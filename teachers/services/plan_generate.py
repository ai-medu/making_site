"""늘봄허브 '프로그램 운영 계획서'(운영 목표·주요 교육 내용·주요 강의 방법·운영 방법)를 선택한 프로그램에 맞춰 AI로 작성"""
import json
import time

import requests

from .doc_extract import (
    CALL_TIMEOUT, MIN_REMAINING, TOTAL_BUDGET, ExtractError,
    _active_keys, _post_with_model_fallback, _record, _status_message,
)

MAX_PROGRAMS = 8
GENERATE_BUDGET = 27
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
   - 지식(knowledge) / 기능(skill) / 태도(attitude) 영역별로 각 3줄, 한 줄은 45~65자의 구체적인 한 문장.
2) 주요 교육 내용: 학생의 수준에 따른 교육 내용을 기술한다.
   - 수준별 3단계(초급 1~2학년, 중급 3~4학년, 고급 5~6학년)로 stages 3개. 각 단계마다
     name(단계 이름, 12자 이내, 프로그램 특성에 맞게. 예: '원리 배움 단계'), grade(예: '1~2학년'),
     goal(목표 1문장, 35~55자), content(교육 내용 3줄, 한 줄 35~55자, 줄바꿈은 \\n), outcome(기대 성과 1문장, 35~55자).
3) 주요 강의 방법: 학생 수준에 따른 강의 방법, 다른 강사(또는 유사 강의)와의 차별점, 학생 대상 평가 및 환류 방법을 기술한다.
   - practice(실습 중심), project(프로젝트 기반 학습), media(시청각 자료 및 실제 사례), custom(맞춤형 지도)에는 초급·중급·고급 수준별 강의 방법과 다른 강의와의 차별점이 드러나게 각 2문장(90~140자).
   - process_eval(과정 평가: 출석·참여도·수행 과정), result_eval(결과물 평가·피드백·환류 방법) 각 2문장(90~140자).
4) 운영 방법: 프로그램 운영 시간(총 차시, 1일 차시), 운영 공간, 학생 참여 방법 및 안전 지도계획, 학교·학부모 소통을 기술한다.
   - time(주 횟수, 1일 차시와 시간, 연간 총 차시를 2줄), space(운영 공간 1~2줄),
     participation(학생 참여 방법 3줄), safety(안전 지도계획 3줄), communication(학교·학부모 소통 3줄). 한 줄은 35~55자.

[주의]
- 선택한 프로그램의 특성에 맞는 구체적인 내용으로 쓰고, 다른 프로그램에도 그대로 쓸 수 있는 뻔한 문구는 피한다.
- 특정 업체·상품·교재명을 단정하지 말고, 과장하거나 확인되지 않은 실적·수상 경력을 쓰지 않는다.
- 문체는 '~한다/~할 수 있다' 형태의 간결한 문장으로 통일한다. 여러 줄은 줄바꿈(\\n)으로 구분하고 줄 앞에 기호(-, ▷ 등)는 붙이지 않는다.
- 숫자(차시·시간)는 초등 방과후학교에서 일반적인 값으로 쓴다.
- 내용이 너무 짧거나 추상적이면 안 된다. 서류 심사에서 강사의 전문성과 운영 계획이 구체적으로 보이도록 충실하게 쓰되,
  정해진 분량(위에 적은 줄 수·글자 수)을 넘기지 않는다. 이 내용은 A4 한 쪽 표 안에 들어가야 한다."""


def _text(v, limit=700):
    if isinstance(v, list):
        v = "\n".join(str(x).strip() for x in v if str(x).strip())
    return str(v or "").strip()[:limit]


def _lines(v, limit=400):
    if isinstance(v, str):
        v = v.split("\n")
    out = [str(x).strip().lstrip("-▷· ").strip() for x in (v or []) if str(x).strip()]
    return [x[:limit] for x in out][:5]


def normalize(raw):
    """AI 응답을 화면에서 쓰는 모양으로 정리 (없는 항목은 빈 값)"""
    goal = raw.get("goal") or {}
    stages = []
    for st in (raw.get("stages") or [])[:3]:
        stages.append({
            "name": _text(st.get("name"), 30), "grade": _text(st.get("grade"), 20),
            "goal": _text(st.get("goal"), 260), "content": _text(st.get("content"), 800),
            "outcome": _text(st.get("outcome"), 260),
        })
    while len(stages) < 3:
        stages.append({"name": "", "grade": "", "goal": "", "content": "", "outcome": ""})
    m, o = raw.get("methods") or {}, raw.get("operation") or {}
    return {
        "goal": {k: _lines(goal.get(k)) for k in ("knowledge", "skill", "attitude")},
        "stages": stages,
        "methods": {k: _text(m.get(k), 700) for k in ("practice", "project", "media", "custom", "process_eval", "result_eval")},
        "operation": {k: _text(o.get(k), 700) for k in ("time", "space", "participation", "safety", "communication")},
    }


def _call_json(body, call_timeout=GENERATE_BUDGET):
    """Gemini를 호출해 JSON 응답을 돌려줌 (키 순환·모델 대체·시간 제한 포함)
    call_timeout: 호출 1회 최대 대기 시간. 짧은 글은 짧게 잡아, 응답이 멈춘 호출은 빨리 포기하고 다른 키로 다시 시도한다."""
    keys = _active_keys()
    if not keys:
        raise ExtractError("AI 설정(API 키)이 아직 되어 있지 않습니다. 관리자에게 문의해주세요.")
    # 서버 작업 제한 30초 안에서 끝내야 함
    deadline = time.monotonic() + GENERATE_BUDGET
    last_error = None
    for _round in range(3):
        retryable = False          # 시간 초과·일시 오류가 있었으면 한 바퀴 더 돌아 재시도
        for key_obj, key in keys:
            if deadline - time.monotonic() < MIN_REMAINING:
                break
            try:
                resp = _post_with_model_fallback(key, body, deadline=deadline, timeout=call_timeout)
            except requests.Timeout:
                _record(key_obj, "응답 지연(시간 초과)")
                last_error = ExtractError("AI 서비스가 지금 혼잡해서 응답이 늦습니다. 잠시 후 다시 시도해주세요.")
                retryable = True
                continue
            except requests.RequestException:
                _record(key_obj, "연결 실패")
                last_error = ExtractError("AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.")
                retryable = True
                continue
            if resp.status_code == 200:
                try:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text)
                except (KeyError, IndexError, ValueError, TypeError) as e:
                    _record(key_obj, "응답 해석 실패")
                    raise ExtractError("AI 응답을 해석하지 못했습니다. 다시 시도해주세요.") from e
                _record(key_obj, None)
                return data
            _record(key_obj, _status_message(resp.status_code))
            if resp.status_code == 429:
                last_error = ExtractError("오늘 무료 사용량을 모두 사용했거나 요청이 몰렸습니다. 잠시 후 다시 시도해주세요.")
            elif resp.status_code in (400, 401, 403):
                last_error = ExtractError("AI 서비스 설정(API 키)에 문제가 있습니다. 관리자에게 문의해주세요.")
            else:
                last_error = ExtractError("내용을 작성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                retryable = retryable or resp.status_code >= 500
        if not retryable or deadline - time.monotonic() < MIN_REMAINING:
            break
    raise last_error or ExtractError("AI 서비스가 지금 혼잡해서 응답이 늦습니다. 잠시 후 다시 시도해주세요.")


def _body(prompt, schema, temperature=0.6):
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }


def generate_plan(programs):
    programs = clean_programs(programs)
    if not programs:
        raise ExtractError("프로그램을 선택해주세요.")
    return normalize(_call_json(_body(_prompt(programs), SCHEMA)))


# ---------------------------------------------------------------------------
# 항목별 AI 작성 (운영 목표 / 주요 교육 내용 / 주요 강의 방법 / 운영 방법 / 교구재 선정 이유·내용·활용 방법)
# ---------------------------------------------------------------------------
SECTION_LABELS = {
    "goal": "운영 목표", "content": "주요 교육 내용", "methods": "주요 강의 방법", "operation": "운영 방법",
    "reason": "교구재 선정 이유", "gear_content": "교구재 내용", "gear_use": "교구재 활용 방법",
}
# 항목마다 '글자 수' 설정이 가리키는 단위의 기본값 (화면의 안내와 맞춤)
DEFAULT_CHARS = {"goal": 55, "content": 45, "methods": 120, "operation": 45, "reason": 160, "gear_content": 160, "gear_use": 160}
MODES = ("fill", "improve", "new")

# 칸이 나뉜 모양(detail)일 때의 칸 이름과 설명
DETAIL_SPEC = {
    "goal": ("""운영 목표: 프로그램을 통하여 학생들에게 길러질 수 있는 역량을 기술하고, 학생의 심리와 발달 정도를 고려한 프로그램 목표를 기술한다.
   - 지식(knowledge) / 기능(skill) / 태도(attitude) 영역별로 각 3줄, 한 줄은 약 {n}자의 구체적인 한 문장.""",
             _obj({"knowledge": _arr(), "skill": _arr(), "attitude": _arr()})),
    "content": ("""주요 교육 내용: 학생의 수준에 따른 교육 내용을 기술한다.
   - 수준별 3단계(초급 1~2학년, 중급 3~4학년, 고급 5~6학년)로 stages 3개. 각 단계마다
     name(단계 이름, 12자 이내, 프로그램 특성에 맞게), grade(예: '1~2학년'),
     goal(목표 1문장, 약 {n}자), content(교육 내용 3줄, 한 줄 약 {n}자, 줄바꿈은 \\n), outcome(기대 성과 1문장, 약 {n}자).""",
                {"type": "OBJECT", "required": ["stages"], "properties": {"stages": {
                    "type": "ARRAY",
                    "items": _obj({"name": _s(), "grade": _s(), "goal": _s(), "content": _s(), "outcome": _s()})}}}),
    "methods": ("""주요 강의 방법: 학생 수준에 따른 강의 방법, 다른 강사(또는 유사 강의)와의 차별점, 학생 대상 평가 및 환류 방법을 기술한다.
   - practice(실습 중심), project(프로젝트 기반 학습), media(시청각 자료 및 실제 사례), custom(맞춤형 지도)에는
     초급·중급·고급 수준별 강의 방법과 다른 강의와의 차별점이 드러나게 각 항목 약 {n}자(2문장).
   - process_eval(과정 평가: 출석·참여도·수행 과정), result_eval(결과물 평가·피드백·환류 방법)도 각 항목 약 {n}자(2문장).""",
                _obj({"practice": _s(), "project": _s(), "media": _s(), "custom": _s(),
                      "process_eval": _s(), "result_eval": _s()})),
    "operation": ("""운영 방법: 프로그램 운영 시간(총 차시, 1일 차시), 운영 공간, 학생 참여 방법 및 안전 지도계획, 학교·학부모 소통을 기술한다.
   - time(주 횟수, 1일 차시와 시간, 연간 총 차시를 2줄), space(운영 공간 1~2줄),
     participation(학생 참여 방법 3줄), safety(안전 지도계획 3줄), communication(학교·학부모 소통 3줄). 한 줄은 약 {n}자.""",
                  _obj({"operation_time": _s(), "space": _s(), "participation": _s(), "safety": _s(), "communication": _s()})),
}
# '운영 시간' 키 이름이 다른 항목과 겹치지 않도록 AI 응답에서는 operation_time 으로 받는다 (화면에는 time 으로 돌려줌)

FLAT_SPEC = {
    "goal": "운영 목표: 프로그램을 통하여 학생들에게 길러질 수 있는 역량과, 학생의 심리·발달 정도를 고려한 프로그램 목표를 기술한다. 지식·기능·태도가 고루 드러나게 한 줄은 약 {n}자, 5~8줄.",
    "content": "주요 교육 내용: 학생의 수준(초급 1~2학년, 중급 3~4학년, 고급 5~6학년)에 따른 교육 내용과 목표·기대 성과를 기술한다. 한 줄은 약 {n}자, 6~9줄.",
    "methods": "주요 강의 방법: 학생 수준에 따른 강의 방법, 다른 강사(또는 유사 강의)와의 차별점, 학생 대상 평가 및 환류 방법을 기술한다. 한 줄은 약 {n}자, 5~8줄.",
    "operation": "운영 방법: 프로그램 운영 시간(총 차시, 1일 차시), 운영 공간, 학생 참여 방법, 안전 지도계획, 학교·학부모 소통을 기술한다. 한 줄은 약 {n}자, 6~9줄.",
    "reason": "교구재 선정 이유: 위 교재·교구·재료를 왜 선택했는지(학생 수준·안전성·교육 목표와의 연결·가격 대비 효과)를 기술한다. 전체 약 {n}자, 2~4줄.",
    "gear_content": "교구재 내용: 위 교구재(교구·재료)의 구성과 특징, 학생이 무엇을 만들거나 체험하는지를 기술한다. 전체 약 {n}자, 2~4줄.",
    "gear_use": "교구재 활용 방법: 위 교구재를 수업에서 어떻게 활용하는지(차시별·단계별 활용, 모둠 활동, 보관·안전 관리)를 기술한다. 전체 약 {n}자, 2~4줄.",
}
FLAT_SCHEMA = _obj({"lines": _arr()})

MODE_TEXT = {
    "fill": "[작성 방식] '빈 칸만 채우기'입니다. 아래 [현재 내용] 중 내용이 있는 칸은 강사가 직접 쓴 것이므로 그 취지와 어긋나지 않게 이어지도록 쓰고, 비어 있는 칸(빈 문자열)을 중심으로 충실히 작성하세요. (내용이 있는 칸은 화면에서 그대로 유지됩니다)",
    "improve": "[작성 방식] '현재 내용 다듬기·보강'입니다. 아래 [현재 내용]의 의도와 핵심 표현을 살리면서 문장을 매끄럽게 고치고, 부족한 부분은 구체적으로 보강하세요. 비어 있는 칸은 새로 작성하세요.",
    "new": "[작성 방식] '새로 작성'입니다. 아래 [현재 내용]이 있다면 그것과 다른 방향·표현·예시로 새롭게 추천하세요(같은 문장을 반복하지 않는다).",
}


def _clip(v, n):
    return " ".join(str(v or "").replace("\u200b", " ").split())[:n] if "\n" not in str(v or "") else \
        "\n".join(" ".join(x.split())[:n] for x in str(v).replace("\u200b", "").split("\n") if x.strip())


def _section_prompt(section, programs, mode, chars, note, extra, current, materials, flat, base=""):
    names = ", ".join(programs)
    if flat:
        spec = FLAT_SPEC[section].format(n=chars)
        out_hint = "응답은 {\"lines\": [...]} 형태로, 줄마다 배열 한 칸에 담는다."
    else:
        spec = DETAIL_SPEC[section][0].format(n=chars)
        out_hint = "응답은 요청한 JSON 구조 그대로 채운다."
    cur_lines = []
    for k, v in (current or {}).items():
        cur_lines.append(f"- {str(k)[:40]}: {_clip(v, 500) or '(비어 있음)'}")
    cur = "\n".join(cur_lines) if cur_lines else "(없음)"
    extra_txt = ("현재 내용에 없더라도 이 프로그램에 어울리는 내용을 AI가 판단해 추가·추천해도 된다." if extra
                 else "현재 내용에 없는 새로운 주제를 마음대로 늘리지 말고, 요청한 칸의 범위 안에서만 작성한다.")
    mat = f"\n[교재·교구·재료 목록]\n{_clip(materials, 700)}\n" if materials and section in ("reason", "gear_content", "gear_use") else ""
    return f"""당신은 초등학교 방과후학교(늘봄학교) 프로그램 운영 계획서를 작성하는 강사 지원 도우미입니다.
'{SECTION_LABELS[section]}' 항목만 작성해 JSON으로 답하세요.

[프로그램] {names}
{"(여러 프로그램이면 하나의 통합 프로그램으로 운영한다고 보고, 각 프로그램의 특징이 골고루 드러나게 작성)" if len(programs) > 1 else ""}
{mat}
[작성 조건]
{spec}

{MODE_TEXT[mode]}
{extra_txt}
{("[기본 요청 - 늘봄허브 서류 안내사항, 반드시 반영] " + base) if base else ""}
{("[강사의 추가 요청] " + note) if note else ""}

[현재 내용]
{cur}

[주의]
- 선택한 프로그램의 특성에 맞는 구체적인 내용으로 쓰고, 다른 프로그램에도 그대로 쓸 수 있는 뻔한 문구는 피한다.
- 특정 업체·상품·교재명을 단정하지 말고(단, 위 [교재·교구·재료 목록]에 있는 이름은 사용 가능), 과장하거나 확인되지 않은 실적·수상 경력을 쓰지 않는다.
- 문체는 '~한다/~할 수 있다' 형태의 간결한 문장으로 통일한다. 줄 앞에 기호(-, ▷ 등)는 붙이지 않는다.
- 글자 수 기준(약 {chars}자)을 지킨다. 이 내용은 A4 표 칸 안에 들어가야 하므로 기준을 크게 넘기지 않는다.
- {out_hint}"""


def generate_section(section, programs, options, current, materials="", flat=False):
    if section not in SECTION_LABELS:
        raise ExtractError("알 수 없는 항목입니다.")
    programs = clean_programs(programs)
    if not programs:
        raise ExtractError("프로그램을 입력해주세요.")
    mode = options.get("mode") if options.get("mode") in MODES else "new"
    try:
        chars = int(options.get("chars") or DEFAULT_CHARS[section])
    except (TypeError, ValueError):
        chars = DEFAULT_CHARS[section]
    chars = max(15, min(chars, 400))
    note = " ".join(str(options.get("note") or "").split())[:300]
    base = "\n".join(" ".join(x.split()) for x in str(options.get("base") or "").split("\n") if x.strip())[:600]
    extra = bool(options.get("extra"))
    flat = bool(flat) or section not in DETAIL_SPEC
    if not isinstance(current, dict):
        current = {}
    current = {str(k)[:40]: v for k, v in list(current.items())[:30]}
    schema = FLAT_SCHEMA if flat else DETAIL_SPEC[section][1]
    prompt = _section_prompt(section, programs, mode, chars, note, extra, current, materials, flat, base)
    # '새로 작성'은 매번 다른 결과가 나오도록 온도를 조금 높임
    # 항목 하나는 보통 3~8초면 끝나므로 호출당 10초만 기다리고, 멈춘 호출은 다른 키로 다시 시도
    data = _call_json(_body(prompt, schema, temperature=0.85 if mode == "new" else 0.6), call_timeout=10)

    if flat:
        return {"lines": _lines(data.get("lines"), 600)[:12] if isinstance(data, dict) else []}
    if section == "goal":
        return {"goal": normalize({"goal": data})["goal"]}
    if section == "content":
        return {"stages": normalize({"stages": data.get("stages")})["stages"]}
    if section == "methods":
        return {"methods": normalize({"methods": data})["methods"]}
    o = dict(data)
    o["time"] = o.pop("operation_time", "")
    return {"operation": normalize({"operation": o})["operation"]}


# ---------------------------------------------------------------------------
# 연간 활동 지도 계획안: 등록된 연간계획서(PDF)를 읽어 주(週)별 '주제 / 내용'으로 정리
# ---------------------------------------------------------------------------
import base64

PLAN_ROWS_SCHEMA = _obj({"rows": {"type": "ARRAY", "items": _obj({"topic": _s(), "lines": _arr()})}})
MAX_PLAN_PDF = 8 * 1024 * 1024


def _plan_rows_prompt(title, start, end, total, topic_max, line_max):
    return f"""첨부한 PDF는 '{title}' 연간(운영) 계획서입니다. 차시(수업 회차)별 학습 주제와 학습 내용이 들어 있습니다.
이 계획서를 바탕으로 강사 제출 서류의 '연간 활동 지도 계획안' 표를 작성합니다.
표는 1주에 1차시씩, 총 {total}주(행)입니다. 이번에는 {start}번째 주부터 {end}번째 주까지({end - start + 1}개 행)만 작성하세요.

[대응 규칙]
- 계획서에 적힌 학습 주제(활동)를 처음부터 순서대로 한 주에 하나씩 대응합니다. (n번째 주 = 계획서의 n번째 주제) 차시 번호 칸이 여러 번호를 한꺼번에 묶어 보여도, 계획서의 주제 수가 전체 차시 수와 같다면 주제 하나가 한 차시(한 주)입니다. 주제를 건너뛰거나 합치지 마세요.
- 계획서의 주제 수가 표의 주 수보다 적을 때만, 한 주제를 학습·제작 등 단계로 나누어 여러 주에 배분합니다.
- 계획서에서 한 주제가 여러 차시에 걸쳐 있으면, 그 학습 내용을 차시별 단계(개념 학습 → 제작 → 동작·실험 등)로 나누어 각 주에 배분합니다. 같은 주제가 이어지면 주제 끝에 (1), (2)처럼 순서를 붙여도 됩니다. 계획서에 없는 활동을 새로 지어내지 마세요.
- 계획서의 전체 차시 수가 {total}보다 많으면 인접한 차시를 묶어 {total}주 안에 들어가게 하고, 적으면 남는 주는 topic과 lines를 빈 값으로 둡니다.
- 차시 번호가 건너뛰어 있거나 표가 여러 쪽에 나뉘어 있어도 계획서 전체를 순서대로 읽습니다.

[분량 - 표 칸이 좁으므로 반드시 지킴]
- topic(주제): 한 줄, 공백 포함 {topic_max}자 이내. 질문형 제목은 의미를 유지하며 짧게 줄입니다.
- lines(내용): 정확히 2줄(배열 2개). 각 줄은 공백 포함 {line_max}자 이내의 한 문장이며 '~합니다 / ~해 봅니다' 문체로 씁니다. 줄 앞에 기호(*, -, ▷)는 붙이지 않습니다.
- 응답은 rows 배열에 {start}번째 주부터 순서대로 정확히 {end - start + 1}개 항목을 담습니다."""


def generate_plan_rows(pdf_bytes, title, start, count, total, topic_max, line_max):
    if len(pdf_bytes) > MAX_PLAN_PDF:
        raise ExtractError("계획서 파일이 너무 커서 읽을 수 없습니다.")
    try:
        start, count, total = int(start), int(count), int(total)
        topic_max, line_max = int(topic_max), int(line_max)
    except (TypeError, ValueError):
        raise ExtractError("요청을 읽지 못했습니다.")
    if not (1 <= count <= 24 and 1 <= start <= total <= 60):
        raise ExtractError("요청 범위가 올바르지 않습니다.")
    topic_max = max(8, min(topic_max, 60))
    line_max = max(10, min(line_max, 80))
    end = min(total, start + count - 1)
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(pdf_bytes).decode()}},
            {"text": _plan_rows_prompt(str(title)[:80], start, end, total, topic_max, line_max)},
        ]}],
        "generationConfig": {
            "temperature": 0.3, "maxOutputTokens": 8192,
            "responseMimeType": "application/json", "responseSchema": PLAN_ROWS_SCHEMA,
        },
    }
    data = _call_json(body, call_timeout=15)   # 멈춘 호출은 15초에 포기하고 다른 키로 한 번 더
    rows = []
    for r in (data.get("rows") if isinstance(data, dict) else None) or []:
        topic = " ".join(str(r.get("topic") or "").split())[:topic_max + 6]
        lines = [" ".join(str(x).split()).lstrip("*-▷· ").strip() for x in (r.get("lines") or []) if str(x).strip()]
        rows.append({"topic": topic, "lines": [x[:line_max + 8] for x in lines[:2]]})
    want = end - start + 1
    rows = rows[:want] + [{"topic": "", "lines": []}] * max(0, want - len(rows))
    return rows
