"""늘봄허브 '프로그램 운영 계획서'(운영 목표·주요 교육 내용·주요 강의 방법·운영 방법)를 선택한 프로그램에 맞춰 AI로 작성"""
import json
import time

import requests

from .doc_extract import (
    CALL_TIMEOUT, MIN_REMAINING, TOTAL_BUDGET, ExtractError,
    _active_keys, _post_with_model_fallback, _record, _status_message,
)

MAX_PROGRAMS = 8
MAX_NAME_LEN = 30


def _s():
    return {"type": "STRING"}


def _arr():
    return {"type": "ARRAY", "items": {"type": "STRING"}}


def _obj(props):
    return {"type": "OBJECT", "properties": props, "required": list(props.keys())}


SCHEMA = _obj({
    "goal": _obj({"knowledge": _arr(), "skill": _arr(), "attitude": _arr()}),
    "stages": {
        "type": "ARRAY",
        "items": _obj({"name": _s(), "grade": _s(), "goal": _s(), "content": _s(), "outcome": _s()}),
    },
    "methods": _obj({
        "practice": _s(), "project": _s(), "media": _s(), "custom": _s(),
        "process_eval": _s(), "result_eval": _s(),
    }),
    "operation": _obj({
        "time": _s(), "space": _s(), "participation": _s(), "safety": _s(), "communication": _s(),
    }),
})


def clean_programs(programs):
    out = []
    for p in programs or []:
        name = " ".join(str(p).split())[:MAX_NAME_LEN]
        if name and name not in out:
            out.append(name)
    return out[:MAX_PROGRAMS]


def _prompt(programs):
    names = ", ".join(programs)
    return f"""당신은 초등학교 방과후학교(늘봄학교) 프로그램 운영 계획서를 작성하는 강사 지원 도우미입니다.
아래 프로그램에 대한 '프로그램 운영 계획서'의 일부를 작성해 JSON으로 답하세요.

[프로그램] {names}
{"(여러 프로그램이면 하나의 통합 프로그램으로 운영한다고 보고, 각 프로그램의 특징이 골고루 드러나게 작성)" if len(programs) > 1 else ""}

[작성 조건 - 늘봄허브 강사 제출 서류 양식의 안내사항]
1) 운영 목표: 프로그램을 통하여 학생들에게 길러질 수 있는 역량을 기술하고, 학생의 심리와 발달 정도를 고려한 프로그램 목표를 기술한다.
   - 지식(knowledge) / 기능(skill) / 태도(attitude) 영역별로 각 2~3줄(각 줄 60자 이내).
2) 주요 교육 내용: 학생의 수준에 따른 교육 내용을 기술한다.
   - 수준별 3단계(초급 1~2학년, 중급 3~4학년, 고급 5~6학년)로 stages 3개. 각 단계마다
     name(단계 이름, 12자 이내, 프로그램 특성에 맞게. 예: '원리 배움 단계'), grade(예: '1~2학년'),
     goal(목표 1줄), content(교육 내용 2~3줄, 줄바꿈은 \\n), outcome(기대 성과 1줄).
3) 주요 강의 방법: 학생 수준에 따른 강의 방법, 다른 강사(또는 유사 강의)와의 차별점, 학생 대상 평가 및 환류 방법을 기술한다.
   - practice(실습 중심), project(프로젝트 기반 학습), media(시청각 자료 및 실제 사례), custom(맞춤형 지도)에는 수준별 강의 방법과 차별점이 드러나게 각 1~2문장.
   - process_eval(과정 평가: 출석·참여도·수행 과정), result_eval(결과물 평가·피드백·환류 방법) 각 1~2문장.
4) 운영 방법: 프로그램 운영 시간(총 차시, 1일 차시), 운영 공간, 학생 참여 방법 및 안전 지도계획, 학교·학부모 소통을 기술한다.
   - time(주 횟수, 1일 차시와 시간, 연간 총 차시), space(운영 공간), participation(학생 참여 방법 2줄),
     safety(안전 지도계획 2줄), communication(학교·학부모 소통 2줄).

[주의]
- 선택한 프로그램의 특성에 맞는 구체적인 내용으로 쓰고, 다른 프로그램에도 그대로 쓸 수 있는 뻔한 문구는 피한다.
- 특정 업체·상품·교재명을 단정하지 말고, 과장하거나 확인되지 않은 실적·수상 경력을 쓰지 않는다.
- 문체는 '~한다/~할 수 있다' 형태의 간결한 문장으로 통일한다. 여러 줄은 줄바꿈(\\n)으로 구분하고 줄 앞에 기호(-, ▷ 등)는 붙이지 않는다.
- 숫자(차시·시간)는 초등 방과후학교에서 일반적인 값으로 쓴다."""


def _text(v, limit=700):
    if isinstance(v, list):
        v = "\n".join(str(x).strip() for x in v if str(x).strip())
    return str(v or "").strip()[:limit]


def _lines(v, limit=300):
    if isinstance(v, str):
        v = v.split("\n")
    out = [str(x).strip().lstrip("-▷· ").strip() for x in (v or []) if str(x).strip()]
    return [x[:limit] for x in out][:4]


def normalize(raw):
    """AI 응답을 화면에서 쓰는 모양으로 정리 (없는 항목은 빈 값)"""
    goal = raw.get("goal") or {}
    stages = []
    for st in (raw.get("stages") or [])[:3]:
        stages.append({
            "name": _text(st.get("name"), 30), "grade": _text(st.get("grade"), 20),
            "goal": _text(st.get("goal"), 200), "content": _text(st.get("content"), 500),
            "outcome": _text(st.get("outcome"), 200),
        })
    while len(stages) < 3:
        stages.append({"name": "", "grade": "", "goal": "", "content": "", "outcome": ""})
    m, o = raw.get("methods") or {}, raw.get("operation") or {}
    return {
        "goal": {k: _lines(goal.get(k)) for k in ("knowledge", "skill", "attitude")},
        "stages": stages,
        "methods": {k: _text(m.get(k), 400) for k in ("practice", "project", "media", "custom", "process_eval", "result_eval")},
        "operation": {k: _text(o.get(k), 400) for k in ("time", "space", "participation", "safety", "communication")},
    }


def generate_plan(programs):
    programs = clean_programs(programs)
    if not programs:
        raise ExtractError("프로그램을 선택해주세요.")
    keys = _active_keys()
    if not keys:
        raise ExtractError("AI 설정(API 키)이 아직 되어 있지 않습니다. 관리자에게 문의해주세요.")

    body = {
        "contents": [{"parts": [{"text": _prompt(programs)}]}],
        "generationConfig": {
            "temperature": 0.6,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    deadline = time.monotonic() + TOTAL_BUDGET
    last_error = None
    for key_obj, key in keys:
        if deadline - time.monotonic() < MIN_REMAINING:
            break
        try:
            resp = _post_with_model_fallback(key, body, deadline=deadline)
        except requests.Timeout:
            _record(key_obj, "응답 지연(시간 초과)")
            last_error = ExtractError("AI 서비스가 지금 혼잡해서 응답이 늦습니다. 잠시 후 다시 시도해주세요.")
            continue
        except requests.RequestException:
            _record(key_obj, "연결 실패")
            last_error = ExtractError("AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.")
            continue
        if resp.status_code == 200:
            try:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(text)
            except (KeyError, IndexError, ValueError, TypeError) as e:
                _record(key_obj, "응답 해석 실패")
                raise ExtractError("AI 응답을 해석하지 못했습니다. 다시 시도해주세요.") from e
            _record(key_obj, None)
            return normalize(data)
        _record(key_obj, _status_message(resp.status_code))
        if resp.status_code == 429:
            last_error = ExtractError("오늘 무료 사용량을 모두 사용했거나 요청이 몰렸습니다. 잠시 후 다시 시도해주세요.")
        elif resp.status_code in (400, 401, 403):
            last_error = ExtractError("AI 서비스 설정(API 키)에 문제가 있습니다. 관리자에게 문의해주세요.")
        else:
            last_error = ExtractError("내용을 작성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    raise last_error or ExtractError("AI 서비스가 지금 혼잡해서 응답이 늦습니다. 잠시 후 다시 시도해주세요.")
