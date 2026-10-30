from .models import MenuItem


def _can_access_menu(user, menu):
    if user.is_staff:
        return True

    if menu.access_level == 'all':
        return True

    if not user.is_authenticated:
        return False

    user_type = getattr(getattr(user, 'profile', None), 'user_type', None)
    if menu.access_level == 'teacher' and user_type in ('teacher', 'center_teacher'):
        return True
    if menu.access_level == 'institution' and user_type == 'institution':
        return True

    return False


def _admin_new_counts(user):
    out = {'approve': 0, 'suspended': 0}
    try:
        from django.db.models import Q
        from django.contrib.auth.models import User
        from accounts.models import AdminSeen
        seen = {x.key: x.seen_at for x in AdminSeen.objects.filter(user=user)}
        pending = User.objects.filter(is_active=False).filter(
            Q(profile__isnull=True) | Q(profile__suspended_at__isnull=True))
        if 'approve' in seen:
            pending = pending.filter(date_joined__gt=seen['approve'])
        out['approve'] = pending.count()
        susp = User.objects.filter(profile__suspended_at__isnull=False)
        if 'suspended' in seen:
            susp = susp.filter(profile__suspended_at__gt=seen['suspended'])
        out['suspended'] = susp.count()
    except Exception:
        pass
    return out


def _open_counts():
    """모집 메뉴 옆에 보여줄 '모집중' 개수 (공고 수집 쪽은 계산이 무거워 5분간 보관)"""
    from django.core.cache import cache
    from django.utils import timezone
    out = {}
    try:
        from recruit.models import InstructorRecruit, DispatchRecruit
        out['instructor'] = InstructorRecruit.objects.filter(status="open", recruit_end__gte=timezone.now()).count()
        out['dispatch'] = DispatchRecruit.objects.filter(status="open").exclude(deadline__lt=timezone.localdate()).count()
    except Exception:
        pass

    def linkhub_counts():
        res = {'gwangju': 0, 'jeonnam': 0}
        try:
            from linkhub.models import CollectedPost
            for p in CollectedPost.objects.only("region", "post_date"):
                if p.get_auto_status() not in ("모집중", "마감임박"):
                    continue
                if (p.region or "").startswith("광주"):
                    res['gwangju'] += 1
                if "전라남도" in (p.region or ""):
                    res['jeonnam'] += 1
        except Exception:
            pass
        return res

    out.update(cache.get_or_set('menu_linkhub_open_counts', linkhub_counts, 300))
    return out


def menu_items(request):
    user = request.user

    # 기본적으로 활성화 상태인 것만 가져오고 sub_menus를 prefetch하여 쿼리 효율 최적화
    all_menus = list(MenuItem.objects.filter(is_active=True).prefetch_related('sub_menus'))
    allowed_ids = {menu.id for menu in all_menus if _can_access_menu(user, menu)}

    top_menus = []
    for menu in all_menus:
        if menu.parent_id is not None or menu.id not in allowed_ids:
            continue

        visible_sub_menus = [sub for sub in menu.sub_menus.all() if sub.is_active and sub.id in allowed_ids]
        menu.visible_sub_menus = visible_sub_menus

        # 하위 메뉴형 그룹은 실제로 보여줄 항목이 있을 때만 노출
        if visible_sub_menus or menu.url != '#':
            top_menus.append(menu)

    # 새 linkhub 공고 수 (영역별) - 오늘 수집된 것 기준
    try:
        from linkhub.models import CollectedPost
        from django.utils import timezone
        today = timezone.localdate()
        new_qs = CollectedPost.objects.filter(
            collected_at__date=today
        ).values_list('source__area', flat=True)
        areas = list(new_qs)
        linkhub_new_gwangju = areas.count('GWANGJU')
        linkhub_new_jeonnam = areas.count('JEONNAM')
    except Exception:
        linkhub_new_gwangju = 0
        linkhub_new_jeonnam = 0

    # 메뉴/서브메뉴에 linkhub new 플래그 직접 설정
    for menu in top_menus:
        parent_has_new = False
        for sub in menu.visible_sub_menus:
            sub_new = (
                ('area=gwangju' in sub.url and linkhub_new_gwangju) or
                ('area=jeonnam' in sub.url and linkhub_new_jeonnam)
            )
            sub.linkhub_new = bool(sub_new)
            if sub.linkhub_new:
                parent_has_new = True
        menu.linkhub_new = parent_has_new
        if not menu.visible_sub_menus:
            menu.linkhub_new = bool(
                ('area=gwangju' in menu.url and linkhub_new_gwangju) or
                ('area=jeonnam' in menu.url and linkhub_new_jeonnam)
            )

    # 모집 메뉴: 이름 옆에 모집중인 공고 수
    open_counts = _open_counts()
    for menu in top_menus:
        for sub in menu.visible_sub_menus:
            if sub.url.startswith('/recruit/instructor'):
                sub.open_count = open_counts.get('instructor', 0)
            elif sub.url.startswith('/recruit/dispatch'):
                sub.open_count = open_counts.get('dispatch', 0)
            elif 'area=gwangju' in sub.url:
                sub.open_count = open_counts.get('gwangju', 0)
            elif 'area=jeonnam' in sub.url:
                sub.open_count = open_counts.get('jeonnam', 0)

    # 관리 메뉴: 회원승인·회원정지 옆에 '새로 추가된 수'(관리자가 마지막으로 그 화면을 본 이후 늘어난 수)
    if user.is_staff:
        counts = _admin_new_counts(user)
        for menu in top_menus:
            for sub in menu.visible_sub_menus:
                if sub.url.rstrip('/') == '/accounts/approve_users':
                    sub.new_count = counts['approve']
                elif sub.url.rstrip('/') == '/accounts/suspended_users':
                    sub.new_count = counts['suspended']
            menu.new_count = sum(getattr(sub, 'new_count', 0) for sub in menu.visible_sub_menus)

    return {
        'global_menu': top_menus,
        'linkhub_new_gwangju': linkhub_new_gwangju,
        'linkhub_new_jeonnam': linkhub_new_jeonnam,
    }
