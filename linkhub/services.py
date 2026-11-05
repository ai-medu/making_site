import requests
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime, date
from urllib.parse import urljoin

from .models import CollectedPost, LinkhubConfig, post_is_expired



AJAX_URL = "https://neulbomhub.kosac.re.kr/prrg/papr/papr/paprListPgng.do"
BASE_URL = "https://neulbomhub.kosac.re.kr"

# 🔥 수집 기준 날짜 (이 날짜 이후 공고만)
CUTOFF_DATE = date(2025, 11, 1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     


def get_total_pages(soup):
    """
    페이지네이션에서 마지막 페이지 번호 추출
    """
    buttons = soup.select("div.paging button[onclick]")
    pages = []

    for btn in buttons:
        onclick = btn.get("onclick", "")
        match = re.search(r"go_Page\((\d+)\)", onclick)
        if match:
            pages.append(int(match.group(1)))

    return max(pages) if pages else 1


# ==================================================
# ✅ 늘봄허브 상세 페이지 파싱
# ==================================================
def fetch_neulbom_detail(detail_url, headers=None):
    """
    늘봄허브 상세 페이지에서
    - 운영요일 (● 표시 기준)
    - 첨부파일 URL
    """
    try:
        res = requests.get(detail_url, headers=headers, timeout=60)
        res.raise_for_status()
    except Exception:
        return "", []

    soup = BeautifulSoup(res.text, "html.parser")

    # ==================================================
    # 🔹 운영요일 추출 (● 표시 기준)
    # ==================================================
    weekday_list = []

    # "요일/시간대" th를 가진 tr 찾기
    th = soup.find("th", string=lambda x: x and "요일/시간대" in x)
    if th:
        table = th.find_next("table")
        if table:
            # 요일 헤더 (월~금)
            headers = [h.get_text(strip=True) for h in table.select("thead th")[1:]]
            # headers 예: ["월", "화", "수", "목", "금"]

            marked_indexes = set()

            for row in table.select("tbody tr"):
                tds = row.select("td")
                for idx, td in enumerate(tds):
                    if "●" in td.get_text():
                        marked_indexes.add(idx)

            for idx in sorted(marked_indexes):
                if idx < len(headers):
                    weekday_list.append(headers[idx])

    weekday = ", ".join(weekday_list)

    # ==================================================
    # 🔹 첨부파일 추출
    # ==================================================
    attachments = []
    for a in soup.select("a[href*='fileDownLoad.do']"):
        href = a.get("href")
        if not href:
            continue
        attachments.append({
            "name": a.get_text(strip=True) or "첨부파일",
            "url": urljoin("https://neulbomhub.kosac.re.kr", href),
        })

    return weekday, attachments



def collect_posts(site):
    """
    SourceSite.collector 기준으로 수집 방식 분기
    """
    if site.collector == "NEULBOM":
        return collect_neulbom(site)

    if site.collector == "JNE_COMMON":
        return collect_jne_common(site)

    if site.collector == "JNE_REGION":
        return collect_jne_region(site)

    raise ValueError(f"지원하지 않는 collector 타입: {site.collector}")


from .models import NeulbomConfig

def get_cutoff_date():
    config = NeulbomConfig.objects.first()
    return config.cutoff_date if config else None

# ==================================================
# ✅ 늘봄허브 수집 (상세 포함)
# ==================================================
def collect_neulbom(site):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    detail_headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://neulbomhub.kosac.re.kr/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    cutoff_date = get_cutoff_date()

    new_saved = 0
    # ==================================================
    # 🔥 NEW 초기화 (하루 지난 글)
    # ==================================================
    today = date.today()

    CollectedPost.objects.filter(
        source=site,
        is_new=True,
        collected_at__date__lt=today
    ).update(is_new=False)

    # 🔹 1페이지 → 전체 페이지 계산
    first_payload = {
        "list_oper_rgn_lclsf_cd": "R0500",
        "miv_pageNo": 1,
    }

    first_res = requests.post(AJAX_URL, data=first_payload, headers=headers, timeout=60)
    first_res.raise_for_status()

    soup = BeautifulSoup(first_res.text, "html.parser")
    total_pages = get_total_pages(soup)

    for page in range(1, total_pages + 1):
        payload = {
            "list_oper_rgn_lclsf_cd": "R0500",
            "miv_pageNo": page,
        }

        response = requests.post(AJAX_URL, data=payload, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("div.boardlist table tbody tr")

        for row in rows:
            flex_tds = row.select("td.flex")
            if len(flex_tds) < 4:
                continue

            def clean(td):
                label = td.select_one("span.w_hidden")
                if label:
                    label.decompose()
                return td.get_text(strip=True)

            region = clean(flex_tds[0])
            school = clean(flex_tds[1])

            # 🔥 광주만
            if not region.startswith("광주광역시"):
                continue

            title_el = row.select_one("td.title_box .title a")
            if not title_el:
                continue

            onclick = title_el.get("onclick", "")
            match = re.search(r"paprDetail\('E',\s*'([^']+)'\)", onclick)
            if not match:
                continue

            mng_no = match.group(1)
            title = title_el.get_text(strip=True)
            period_text = clean(flex_tds[3]).replace("모집기간", "").strip()
            status = clean(flex_tds[-1]) if flex_tds else ""

            # 🔹 모집기간 파싱 (종료일 기준)
            try:
                start_str, end_str = [x.strip() for x in period_text.split("~")]
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except Exception:
                continue

            # ❌ 모집 종료된 공고 스킵
            if end_date < today:
                continue

            # ❌ 기준일 이전 공고 스킵 (🔥 핵심)
            if cutoff_date and end_date < cutoff_date:
                continue


            link = (
                "https://neulbomhub.kosac.re.kr/prrg/papr/papr/paprDetail.do"
                f"?mode=E&prgrm_pbanc_mng_no={mng_no}"
            )

            # 🔥 상세 페이지 → 요일 + 첨부파일 (항상 최신)
            weekday, attachments = fetch_neulbom_detail(
                link,
                headers=detail_headers
            )

            # ❌ 첨부파일 없는 공고는 수집 제외 (광주 늘봄)
            if not attachments:
                continue

            # 🔥 create or update
            obj, created = CollectedPost.objects.update_or_create(
                source=site,
                mng_no=mng_no,
                defaults={
                    "title": title,
                    "link": link,
                    "region": region,
                    "school_name": school,
                    "post_date": period_text,
                    "status": status,
                    "weekday": weekday,
                    "attachment_urls": attachments,
                }
            )

            # ✅ 신규만 NEW 처리
            if created:
                obj.is_new = True
                obj.save(update_fields=["is_new"])


            time.sleep(0.2)

        time.sleep(0.2)

    return new_saved


# ==================================================
# JNE COMMON (기존 유지)
# ==================================================
def collect_jne_common(site):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Referer": site.url,
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    existing_mng = set(
        CollectedPost.objects
        .filter(source=site)
        .values_list("mng_no", flat=True)
    )

    new_saved = 0
    page = 1
    MAX_PAGES = 50
    lconfig = LinkhubConfig.get()

    while page <= MAX_PAGES:
        params = site.extra_params.copy() if site.extra_params else {}
        params["pageIndex"] = page

        try:
            response = requests.get(site.url, params=params, headers=headers, timeout=60)
            response.raise_for_status()
        except Exception:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select(site.list_selector)
        if not rows:
            break

        expired_in_page = 0
        for row in rows:
            school_el = row.select_one("td:nth-child(2)")
            school_name = school_el.get_text(strip=True) if school_el else ""

            title_el = row.select_one("td.al a.nttInfoBtn")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            mng_no = title_el.get("data-id")
            if not mng_no or mng_no in existing_mng:
                continue

            link = (
                "https://www.jne.go.kr/aftersc/na/ntt/selectNttInfo.do"
                f"?bbsId=367&nttSn={mng_no}&mi=762"
            )

            date_el = row.select_one("td:nth-child(5)")
            post_date = date_el.get_text(strip=True) if date_el else ""
            if post_is_expired(post_date, config=lconfig):    # 이미 기간이 지난 공고는 다시 담지 않음 (지워도 되살아나는 것 방지)
                expired_in_page += 1
                continue

            CollectedPost.objects.create(
                source=site,
                mng_no=mng_no,
                title=title,
                link=link,
                region="전라남도",
                school_name=school_name,
                post_date=post_date,
                status="무관",
                is_new=True,
            )

            existing_mng.add(mng_no)
            new_saved += 1

        if expired_in_page and expired_in_page >= len(rows):    # 한 쪽이 전부 기간 지난 공고면 더 뒤쪽도 볼 필요 없음
            break
        page += 1
        time.sleep(0.5)

    return new_saved


# ==================================================
# JNE REGION (기존 유지)
# ==================================================
def collect_jne_region(site):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Referer": site.url,
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    existing_mng = set(
        CollectedPost.objects
        .filter(source=site)
        .values_list("mng_no", flat=True)
    )

    new_saved = 0
    page = 1
    MAX_PAGES = 10
    lconfig = LinkhubConfig.get()

    while page <= MAX_PAGES:
        params = {
            "bbsId": site.extra_params.get("bbsId"),
            "mi": site.extra_params.get("mi"),
            "pageIndex": page,
        }

        response = requests.get(site.url, params=params, headers=headers, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tbody tr")
        if not rows:
            break

        saved_in_page = 0

        for row in rows:
            title_el = row.select_one("a.nttInfoBtn")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            mng_no = title_el.get("data-id")
            if not mng_no or mng_no in existing_mng:
                continue

            tds = row.select("td")
            if len(tds) < 4:
                continue

            school_name = tds[2].get_text(strip=True)
            post_date = tds[3].get_text(strip=True)
            if post_is_expired(post_date, config=lconfig):    # 이미 기간이 지난 공고는 다시 담지 않음
                continue

            link = urljoin(
                site.url,
                f"/hped/na/ntt/selectNttInfo.do"
                f"?bbsId={site.extra_params.get('bbsId')}"
                f"&nttSn={mng_no}"
                f"&mi={site.extra_params.get('mi')}"
            )

            CollectedPost.objects.create(
                source=site,
                mng_no=mng_no,
                title=title,
                link=link,
                region="전라남도",
                school_name=school_name,
                post_date=post_date,
                status="",
                is_new=True,
            )

            existing_mng.add(mng_no)
            new_saved += 1
            saved_in_page += 1

        if saved_in_page == 0:
            break

        page += 1
        time.sleep(0.1)

    print(f"[DONE][JNE_REGION] 신규 수집 {new_saved}건")
    return new_saved

