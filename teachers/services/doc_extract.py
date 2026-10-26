"""졸업증명서·학위기·자격증·경력증명서 파일에서 등록 항목을 자동으로 읽어내는 서비스 (Google Gemini)"""
import base64
import json
import mimetypes

import requests
from django.conf import settings

MAX_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PDF_TYPE = "application/pdf"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _str(enum=None):
    d = {"type": "STRING", "nullable": True}
    if enum:
        d["enum"] = list(enum)
    return d


def _schema(properties):
    return {
        "type": "OBJECT",
        "required": ["items", "note"],
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {"type": "OBJECT", "properties": properties, "required": list(properties.keys())},
            },
            "note": {"type": "STRING"},
        },
    }


KINDS = {
    "education": {
        "label": "학력",
        "docs": "졸업증명서, 학위기, 학위증서, 수료증명서, 재학증명서 등",
        "fields": (
            "school_name: 학교명 (예: 호남대학교, 광주교육대학교 교육대학원). 학위기에 '교육대학원'처럼 대학원이 있으면 대학교 이름과 함께 적는다.\n"
            "status: 졸업 / 수료 / 재학 / 휴학 / 중퇴 중 하나. 졸업증명서·학위기면 '졸업'.\n"
            "major: 전공 분야 (학과·전공명)\n"
            "degree: 박사 / 석사 / 학사 / 전문학사 / 해당없음 중 하나. 학위기의 학위명(예: 교육학석사 → 석사, 이학사 → 학사)을 기준으로 한다.\n"
            "start_date: 입학일 (문서에 있을 때만, YYYY-MM-DD)\n"
            "end_date: 졸업일 또는 학위수여일 (YYYY-MM-DD)"
        ),
        "properties": {
            "school_name": _str(),
            "status": _str(["졸업", "수료", "재학", "휴학", "중퇴"]),
            "major": _str(),
            "degree": _str(["박사", "석사", "학사", "전문학사", "해당없음"]),
            "start_date": _str(),
            "end_date": _str(),
        },
    },
    "certificate": {
        "label": "자격증",
        "docs": "자격증, 자격취득사항확인서, 수료증, 합격증, 자격 인증서 등",
        "fields": (
            "name: 자격증명(급수가 있으면 급수 포함. 예: 로봇지도사 1급)\n"
            "issued_by: 발급기관 (예: 한국산업인력공단, 교육부, STEAM교육협회)\n"
            "issued_date: 취득일 또는 발급일 (YYYY-MM-DD)\n"
            "expires_date: 유효기간 만료일 (문서에 있을 때만, YYYY-MM-DD)"
        ),
        "properties": {
            "name": _str(),
            "issued_by": _str(),
            "issued_date": _str(),
            "expires_date": _str(),
        },
    },
    "career": {
        "label": "경력",
        "docs": "경력증명서, 재직증명서, 위촉증명서, 강사 위촉장, 근무확인서 등",
        "fields": (
            "organization: 기관명 (학교·회사·센터 이름)\n"
            "position: 직책 또는 담당 프로그램명 (예: 로봇과학 강사)\n"
            "start_date: 근무 시작일 (YYYY-MM-DD)\n"
            "end_date: 근무 종료일 (YYYY-MM-DD, 현재 재직 중이면 null)\n"
            "description: 담당 업무·세부 내용 (짧게, 문서에 있을 때만)\n"
            "※ 한 문서에 여러 기관/기간이 있으면 각각 별도 항목으로 만든다."
        ),
        "properties": {
            "organization": _str(),
            "position": _str(),
            "start_date": _str(),
            "end_date": _str(),
            "description": _str(),
        },
    },
}


class ExtractError(Exception):
    pass


def extract(kind, filename, content_type, data):
    if kind not in KINDS:
        raise ExtractError("지원하지 않는 종류입니다.")
    if len(data) > MAX_BYTES:
        raise ExtractError("파일이 너무 큽니다. 10MB 이하 파일을 올려주세요.")
    ctype = (content_type or mimetypes.guess_type(filename)[0] or "").lower()
    if ctype == "image/jpg":
        ctype = "image/jpeg"
    if ctype not in IMAGE_TYPES and ctype != PDF_TYPE:
        raise ExtractError("PDF 또는 이미지(JPG·PNG) 파일만 읽을 수 있습니다.")

    spec = KINDS[kind]
    prompt = (
        f"첨부된 파일은 강사의 '{spec['label']}' 증빙 서류({spec['docs']})입니다.\n"
        "문서에 실제로 적힌 내용만 읽어서 아래 항목을 채워주세요. 보이지 않거나 확실하지 않은 값은 추측하지 말고 null로 두세요.\n"
        "날짜는 반드시 YYYY-MM-DD 형식(예: 2018-08-31)으로 바꿔 적습니다. 연·월만 있으면 해당 월의 1일, 연도만 있으면 null로 둡니다.\n"
        "주민등록번호·주소·연락처 등 항목에 없는 개인정보는 결과에 포함하지 않습니다.\n"
        "이 종류의 서류가 아니거나 읽을 수 없으면 items를 빈 배열로 하고 note에 이유를 한국어 한 문장으로 적습니다.\n\n"
        f"[채울 항목]\n{spec['fields']}\n\n"
        "note에는 확인이 필요한 점(흐릿해서 불확실한 값 등)을 한국어 한 문장으로 적고, 없으면 빈 문자열로 둡니다."
    )
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": ctype, "data": base64.b64encode(data).decode()}},
            {"text": prompt},
        ]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _schema(spec["properties"]),
        },
    }
    model = getattr(settings, "DOC_EXTRACT_MODEL", "gemini-2.5-flash")

    keys = _active_keys()
    if not keys:
        raise ExtractError("서류 자동 읽기 설정(API 키)이 아직 되어 있지 않습니다. 관리자에게 문의해주세요.")

    last_error = None
    for key_obj, key in keys:
        try:
            resp = requests.post(GEMINI_URL.format(model=model), json=body,
                                 headers={"x-goog-api-key": key}, timeout=90)
        except requests.RequestException:
            _record(key_obj, "연결 실패")
            last_error = ExtractError("AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.")
            continue
        if resp.status_code == 200:
            try:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text)
            except (KeyError, IndexError, ValueError, TypeError) as e:
                _record(key_obj, "응답 해석 실패")
                raise ExtractError("서류 내용을 해석하지 못했습니다. 더 선명한 파일로 다시 시도하거나 직접 입력해주세요.") from e
            _record(key_obj, None)
            if not isinstance(result.get("items"), list):
                result["items"] = []
            return result
        # 이 키로는 쓸 수 없는 경우 → 다음 키로 넘어감
        _record(key_obj, _status_message(resp.status_code))
        if resp.status_code == 429:
            last_error = ExtractError("오늘 무료 사용량을 모두 사용했거나 요청이 몰렸습니다. 잠시 후 다시 시도하거나 직접 입력해주세요.")
        elif resp.status_code in (400, 401, 403):
            last_error = ExtractError("AI 서비스 설정(API 키)에 문제가 있습니다. 관리자에게 문의해주세요.")
        else:
            last_error = ExtractError("서류를 읽는 중 오류가 발생했습니다. 잠시 후 다시 시도하거나 직접 입력해주세요.")
    raise last_error


def _status_message(code):
    return {
        429: "사용량 초과(429)",
        400: "요청 오류 또는 잘못된 키(400)",
        401: "인증 실패(401)",
        403: "권한 없음/키 차단(403)",
    }.get(code, f"서버 오류({code})")


def _active_keys():
    """사용 중으로 등록된 키를 순서대로 (DB 키가 하나도 없으면 설정 파일의 키)"""
    from main.models import AIApiKey
    keys = [(k, k.api_key) for k in AIApiKey.objects.filter(is_active=True, provider="gemini").exclude(api_key="")]
    if not keys and getattr(settings, "GEMINI_API_KEY", ""):
        keys = [(None, settings.GEMINI_API_KEY)]
    return keys


def _record(key_obj, error):
    if key_obj is None:
        return
    from django.db.models import F
    from django.utils import timezone
    from main.models import AIApiKey
    now = timezone.now()
    if error is None:
        AIApiKey.objects.filter(pk=key_obj.pk).update(
            success_count=F("success_count") + 1, last_used_at=now, last_error="", last_error_at=None)
    else:
        AIApiKey.objects.filter(pk=key_obj.pk).update(
            fail_count=F("fail_count") + 1, last_used_at=now, last_error=error[:300], last_error_at=now)


def test_key(key_obj):
    """등록된 키가 동작하는지 확인 (짧은 요청 1회). (성공여부, 메시지)"""
    model = getattr(settings, "DOC_EXTRACT_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": "OK 라고만 답해주세요."}]}]}
    try:
        resp = requests.post(GEMINI_URL.format(model=model), json=body,
                             headers={"x-goog-api-key": key_obj.api_key}, timeout=30)
    except requests.RequestException:
        _record(key_obj, "연결 실패")
        return False, "AI 서비스에 연결하지 못했습니다."
    if resp.status_code == 200:
        _record(key_obj, None)
        return True, "정상적으로 연결되었습니다."
    msg = _status_message(resp.status_code)
    _record(key_obj, msg)
    return False, f"사용할 수 없습니다: {msg}"
