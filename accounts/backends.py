from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class CaseInsensitiveModelBackend(ModelBackend):
    """아이디(이메일)는 대소문자를 구분하지 않고 로그인 (휴대폰 키보드가 첫 글자를 대문자로 바꿔도 로그인되게)"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        username = username.strip()
        users = list(User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": username})[:5])
        users.sort(key=lambda u: u.username != username)     # 철자가 정확히 같은 계정을 먼저 확인
        for user in users:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        if not users:
            User().set_password(password)      # 없는 아이디도 같은 시간이 걸리게 (아이디 존재 여부 노출 방지)
        return None
