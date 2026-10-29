"""NVIDIA NIM(build.nvidia.com) 호출 - Gemini가 사용량 초과·오류일 때 글 작성(텍스트)용 예비 경로

OpenAI 호환 chat/completions 를 쓰고, 문서 쪽에서 만든 Gemini 형식 요청(body)을 그대로 받아 변환한다.
PDF 같은 파일이 들어 있는 요청은 처리하지 않는다(호출하는 쪽에서 걸러냄).
"""
import json
import re
import time

import requests
from django.conf import settings

NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# 앞에서부터 시도. 모델이 없거나(404) 사용량 초과(429)이면 다음 모델로 넘어감. settings.NIM_MODELS 로 바꿀 수 있음
# (카탈로그에 보여도 계정에서 못 쓰거나(404) 서비스가 끝난(410) 모델이 많아, 실제로 응답한 모델만 둠 - 2026-10 확인)
PER_MODEL = 12   # 모델 하나를 기다리는 최대 시간(초). 큰 모델은 무료 구간에서 멈추는 일이 잦아 짧게 끊고 다음으로
DEFAULT_MODELS = [
    "nvidia/nemotron-3.5-bolt-e4b",             # 작지만 빠름(5~7초)
    "nvidia/nemotron-3.5-super-vl-120b-a12b",   # 품질은 더 좋지만 느리고 불안정
]


class NimError(Exception):
    pass


def models():
    m = getattr(settings, "NIM_MODELS", None)
    return list(m) if m else list(DEFAULT_MODELS)


def active_keys():
    """사용 중으로 등록된 NVIDIA NIM 키 (키 관리 화면에서 등록)"""
    from main.models import AIApiKey
    return [(k, k.api_key) for k in AIApiKey.objects.filter(is_active=True, provider="nvidia").exclude(api_key="")]


def can_handle(body):
    """파일(PDF 등)이 들어 있지 않은 글 요청인가"""
    try:
        parts = body["contents"][0]["parts"]
    except (KeyError, IndexError, TypeError):
        return False
    return bool(parts) and all("text" in p for p in parts)


def _plain_schema(s):
    """Gemini 형식 스키마(OBJECT/ARRAY/STRING)를 일반 JSON 스키마로"""
    if not isinstance(s, dict):
        return s
    out = {}
    for k, v in s.items():
        if k == "type" and isinstance(v, str):
            out[k] = v.lower()
        elif k == "properties" and isinstance(v, dict):
            out[k] = {pk: _plain_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _plain_schema(v)
        else:
            out[k] = v
    return out


def _messages(body):
    prompt = body["contents"][0]["parts"][0]["text"]
    schema = (body.get("generationConfig") or {}).get("responseSchema")
    if schema:
        prompt += ("\n\n[출력 형식] 아래 JSON 스키마에 맞는 JSON 객체 하나만 출력하세요. "
                   "설명, 인사말, 코드블록(```)은 쓰지 마세요. 모든 글은 한국어로 씁니다.\n"
                   + json.dumps(_plain_schema(schema), ensure_ascii=False))
    return [{"role": "user", "content": prompt}]


def _parse_json(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            return json.loads(text[a:b + 1])      # 실패하면 ValueError
        raise


def chat_json(key, body, deadline, timeout=PER_MODEL, url=NIM_URL, model_list=None, extra_headers=None):
    """OpenAI 호환 서비스(기본: NIM)로 JSON 응답을 받음. 성공하면 (데이터, None), 실패하면 (None, 오류 설명)
    모델 하나가 timeout 초 안에 답하지 않으면 다음 모델로 넘어간다."""
    gc = body.get("generationConfig") or {}
    last = "응답 없음"
    for model in (model_list or models()):
        left = deadline - time.monotonic()
        if left < 3:
            return None, last
        payload = {
            "model": model, "messages": _messages(body), "stream": False,
            "temperature": gc.get("temperature", 0.6), "max_tokens": min(int(gc.get("maxOutputTokens", 4096)), 4096),
        }
        try:
            resp = requests.post(url, json=payload, timeout=min(timeout, left),
                                 headers=dict({"Authorization": f"Bearer {key}", "Accept": "application/json"}, **(extra_headers or {})))
        except requests.Timeout:
            last = "응답 지연(시간 초과)"
            continue
        except requests.RequestException:
            return None, "연결 실패"
        if resp.status_code == 200:
            try:
                data = _parse_json(resp.json()["choices"][0]["message"]["content"])
            except (KeyError, IndexError, ValueError, TypeError):
                data = None
            want_obj = ((gc.get("responseSchema") or {}).get("type") == "OBJECT")
            if data is None or (want_obj and not isinstance(data, dict)):
                last = "응답 해석 실패"
                continue
            return data, None
        if resp.status_code in (401, 403):
            return None, f"인증 실패({resp.status_code}) - 키를 확인해주세요"
        last = {429: "사용량 초과(429)", 404: "모델을 찾을 수 없음(404)", 410: "서비스 종료된 모델(410)"}.get(resp.status_code, f"서버 오류({resp.status_code})")
    return None, last


def test_key(key_obj, chat=None):
    """등록된 키가 동작하는지 확인 (성공여부, 메시지). chat: 다른 서비스의 chat_json"""
    from .doc_extract import _record
    body = {"contents": [{"parts": [{"text": "다음 JSON 으로만 답하세요: {\"ok\": true}"}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 50}}
    data, err = (chat or chat_json)(key_obj.api_key, body, time.monotonic() + 25)
    if err:
        _record(key_obj, err)
        return False, f"사용할 수 없습니다: {err}"
    _record(key_obj, None)
    return True, "정상적으로 연결되었습니다."
