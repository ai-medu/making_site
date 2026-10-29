"""OpenRouter(openrouter.ai) 무료 모델 호출 - Gemini·NVIDIA NIM 이 모두 실패했을 때의 마지막 예비 경로 (글 작성 전용)

NIM 과 같은 OpenAI 호환 방식이라 호출 부분은 nim.chat_json 을 그대로 쓴다.
"""
from django.conf import settings

from . import nim

URL = "https://openrouter.ai/api/v1/chat/completions"
# 무료(:free) 모델만 사용 - 유료 모델이 불려 요금이 나가지 않게 함. settings.OPENROUTER_MODELS 로 바꿀 수 있음 (2026-10 목록 기준)
DEFAULT_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "openrouter/free",
]
HEADERS = {"HTTP-Referer": "https://steam-making.com", "X-Title": "MeduTeacher"}


def models():
    m = getattr(settings, "OPENROUTER_MODELS", None)
    return [x for x in (m or DEFAULT_MODELS) if x.endswith(":free") or x == "openrouter/free"]


def active_keys():
    from main.models import AIApiKey
    return [(k, k.api_key) for k in AIApiKey.objects.filter(is_active=True, provider="openrouter").exclude(api_key="")]


def chat_json(key, body, deadline, timeout=nim.PER_MODEL):
    return nim.chat_json(key, body, deadline, timeout=timeout, url=URL, model_list=models(), extra_headers=HEADERS)


def test_key(key_obj):
    return nim.test_key(key_obj, chat=chat_json)
