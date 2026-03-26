import random
import re

SCENARIO_SYSTEM_PROMPT = """
## Role
너는 학습자의 한국어 수준에 맞춘 대화 시나리오 설계자다.
장소와 관계 유형을 입력받아 아래 제약을 지키며 JSON을 생성한다.

## Output Schema

{{
  "scenario_title": "",
  "scenario_description": "",
  "location": "",
  "dialogue_function": [],
  "relationship_type": "",
  "personas": {{
    "A": {{ "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" }},
    "B": {{ "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" }}
  }}
}}
Output only the above schema without explanations, comments, or ```.

Field descriptions:
  scenario_title      — 시나리오를 한 문장으로 요약한 제목
  scenario_description — 학습자가 대화 맥락을 이해할 수 있는 1~2문장 상황 안내 (## Constraints ④)
  location            — 입력받은 장소값 그대로
  dialogue_function   — 선택한 대화 기능 목록 (문자열 배열, ## Constraints ⑥)
  relationship_type   — 입력받은 관계 유형값 그대로
  personas.A/B
    name    — 인물 이름
    age     — 나이 (문자열)
    gender  — "남" 또는 "여"
    role    — 관계 유형별 허용 역할 (## Constraints ①)
    mission — 이 대화에서 달성하고 싶은 목표 (## Constraints ③)

## Constraints

### ① role·age per relationship_type
  - 친구        → role: 친구 / 친구                         | age: 동갑
  - 선배-후배   → role: 선배 / 후배 (직업명 금지)            | age: 차이 1~5살
  - 선생님-학생 → role: 선생님 / 학생                       | age: 차이 10살 이상
  - 연인        → role: 남자 친구 / 여자 친구 (A/B 교차 가능) | age: 차이 0~3살
  - 낯선 사람   → role: 대학생(고정) / 직업·신분             | age: 제한 없음

### ② personas
  - A 또는 B 중 1명은 반드시 20대 대학생
  - A 또는 B 중 1명은 반드시 외국인 이름 사용

### ③ mission
  - A·B 각 persona가 이 대화를 통해 달성하고 싶은 목표 (30자 이내)
  - mission 구조는 {{dialogue_functions}}의 [] 태그를 따른다.
    카테고리는 [요청자-조력자] / [각자 목표] / [자유 선택] 세 가지다.
    [요청자-조력자] → A는 요청자, B는 조력자
      Example) A mission: "화장실이 어디에 있는지 알고 싶어요." / B mission: "화장실 위치를 알려 주고 싶어요."
    [각자 목표] → A·B 각자 궁금한 것을 mission으로
      단, mission은 반드시 "상대방에 대해 알고 싶은 것"으로 작성할 것
      Example) A mission: "상대방이 좋아하는 음식을 알고 싶어요." / B mission: "상대방의 주말 일과가 궁금해요."
    [자유 선택] → 상황에 맞게 선택
  - [예외] 낯선 사람 관계 → dialogue_function에 관계없이 항상 요청자-조력자 구조

  - Counter-example) "친구와 만나기로 했어요." (완료된 상황 금지)
                     "오늘 저녁에 한강에서 함께 달리기 할래요?" (대화에 활용할 첫 문장 금지)

### ④ scenario_description
  - 학습자가 대화 맥락을 이해할 수 있도록 1~2문장으로 작성
  - Format: [A.name]은/는 ~하고 싶고, [B.name]은/는 ~합니다.
    ~하고 싶고/~합니다 부분은 각 persona의 mission을 바탕으로 작성
    relationship_type은 첫 문장에 자연스러운 한국어로 녹여 표현할 것
    Example)
        친구 / 연인        → "{{location}}에서 만난 [relationship_type]인 두 사람의 대화입니다."
        선배-후배 / 선생님-학생 → "{{location}}에서 함께하는 [A.role]과 [B.role]의 대화입니다."
        낯선 사람          → "{{location}}에서 처음 만난 두 사람의 대화입니다."
      - Constraint: 첫 문장에 {{location}}이 자연스럽게 포함될 것
  - Constraint: 학습자 수준({korean_level})에 맞는 어휘 사용

### ⑤ expression
  - 어휘와 문법은 한국어 {korean_level} 학습자 수준을 유지한다
  - 단, 장소명·브랜드명·음식명·인물 이름 등 고유명사는 자유롭게 사용한다
  - 장소의 실제 명소, 시설, 문화적 맥락을 반영해 생동감 있는 시나리오를 만든다
  - 지하철 노선의 경우 실제 환승 정보를 정확히 반영하라

### ⑥ dialogue_function
  - 배열 각 항목은 기능명만 포함할 것
  - 카테고리 태그([요청자-조력자] 등)나 카테고리명 자체를 항목 값으로 쓰는 것은 금지
  - Example) ["장소 묻기", "취향 묻기"]
  - Counter-example) ["[각자 목표] 취향 묻기"], ["각자 목표"]
"""

SCENARIO_USER_PROMPT_TEMPLATE = """
학습자의 한국어 수준: {korean_level}
장소: {location}
관계 유형: {relationship_type}

## 실행 순서
0. [입력 확인] {relationship_type} — 주어진 값 그대로 사용

1. [활동 선택] {location}에서 할 수 있는 활동들을 다양하게 떠올린 뒤, {relationship_type}과 가장 자연스러운 것 선택
   낯선 사람 → 반드시 1개만 선택 | 나머지 → 1~2개 선택

   참고) {location_context}
   위 맥락은 대화 소재 참고용이다. 대화는 반드시 {location} 안에서 일어나야 한다.
   위 맥락에서 장소 탐색(장소 묻기) 외의 소재를 적극 활용할 것.
   실제 사실을 왜곡하지 말고, 불확실한 정보는 사용하지 말라.

2. [dialogue_function 확정] 선택한 활동에 맞는 dialogue_function을 확정

   {dialogue_functions}

3. [personas 설정] (## Constraints ① role 규칙 준수)

4. [mission 생성] (## Constraints ③ 준수)

5. [scenario_description 생성] (## Constraints ④ Format 준수, 각 persona의 mission 참고)

6. JSON 출력 — 시스템 프롬프트의 출력 스키마를 따를 것

## 예시
예시 1 - 입력: 장소=백화점, 관계 유형=낯선 사람 → [요청자-조력자] + 외국인 이름 A
{{ "scenario_title": "백화점에서 팝업 스토어를 찾는 대학생",
  "scenario_description": "백화점에서 처음 만난 두 사람의 대화입니다. 리사는 나이키 팝업 스토어가 몇 층에 있는지 알고 싶고, 영은은 위치를 안내해 주고 싶어합니다.",
  "location": "백화점",
  "dialogue_function": ["장소 묻기"], "relationship_type": "낯선 사람",
  "personas": {{
    "A": {{ "name": "리사", "age": "21", "gender": "여", "role": "대학생", "mission": "나이키 팝업 스토어가 몇 층에 있는지 알고 싶어요." }},
    "B": {{ "name": "영은", "age": "35", "gender": "여", "role": "백화점 직원", "mission": "팝업 스토어 위치를 알려 주고 싶어요." }}
  }}
}}

예시 2 - 입력: 장소=카페, 관계 유형=연인 → [각자 목표] + 외국인 이름 B
{{ "scenario_title": "카페에서 디저트 이야기를 나누는 연인",
  "scenario_description": "카페에서 만난 연인 관계인 두 사람의 대화입니다. 현아는 제이크가 두쫀쿠를 먹어 본 적이 있는지 알고 싶고, 제이크는 현아가 좋아하는 다른 카페 디저트가 궁금합니다.",
  "location": "카페",
  "dialogue_function": ["취향 묻기", "경험 묻기"], "relationship_type": "연인",
  "personas": {{
    "A": {{ "name": "현아", "age": "23", "gender": "여", "role": "여자 친구", "mission": "남자 친구가 두쫀쿠를 먹어 본 적이 있는지 알고 싶어요." }},
    "B": {{ "name": "제이크", "age": "24", "gender": "남", "role": "남자 친구", "mission": "여자 친구가 두쫀쿠 말고 또 좋아하는 카페 디저트가 있는지 알고 싶어요." }}
  }}
}}

"""

# LEVEL_MAP: 서비스 레벨(3단계) → 한국어 급수 진입점 매핑
#
# 서비스는 Beginner / Intermediate / Advanced 3단계로 구성되며,
# 각 단계 안에서 사용자 진행도에 따라 세부 티어(급수)가 올라간다.
#
#   Beginner    → 1급(진입) ~ 2급(숙달)
#   Intermediate → 3급(진입) ~ 4급(숙달)
#   Advanced    → 5급(진입) ~ 6급(숙달)
#
# 이 맵은 각 서비스 레벨의 진입 급수를 가리킨다.
# 세부 티어 로직은 추후 사용자 진행도 시스템과 연동 예정.
LEVEL_MAP: dict[str, str] = {
    "Beginner": "1급",
    "Intermediate": "3급",
    "Advanced": "5급",
}

# 한국어 표준 교육과정에 기반한 교재들의 급수별 말하기 목표를 종합한 것으로,
# 페르소나 mission을 교육적 근거 위에서 생성하기 위한 비계(scaffolding) 역할을 한다.
# 카테고리(요청자-조력자 / 각자 목표 / 자유 선택)는 A·B 간 mission을 자연스럽게
# 분배하기 위한 분류 기준이다.
# build_user_message() 호출 시 급수를 키로 카테고리별 목록을 포맷팅해 주입한다.
# → {dialogue_functions} 자리에 "[카테고리] 기능1 | 기능2 | ..." 형태로 렌더링된다.
DIALOGUE_FUNCTIONS: dict[str, dict[str, list[str]]] = {
    "1급": {
        "요청자-조력자": ["장소 묻기", "물건 사기", "음식 주문하기", "시간 묻기"],
        "각자 목표": [
            "일상 묻기",
            "취향 묻기",
            "경험 묻기",
            "기분 묻기",
            "날씨/풍경 묻기",
            "어제/주말에 한 일 묻기",
        ],
        "자유 선택": ["자기소개", "약속 정하기"],
    },
    "2급": {
        "요청자-조력자": [
            "음식 주문하기",
            "물건 비교하기",
            "교환/환불 요청하기",
            "교통/길 찾기",
            "전화 통화하기",
            "허락 구하기",
            "도움 요청하기",
            "거절하기",
        ],
        "각자 목표": [
            "안부/근황 묻기",
            "외모/성격 묘사하기",
            "가족/고향 소개하기",
            "여행 계획 말하기",
        ],
        "자유 선택": [
            "감정 표현하기",
            "건강 상태 설명하기",
            "모임 제안하기",
            "미래 계획 말하기",
        ],
    },
}

# 지원하는 관계 유형 목록. build_user_message 호출 시 랜덤으로 하나 선택된다.
# MVP 대표 페르소나(20대 유학생)가 친밀도·위계에 따른 적절한 한국어 표현을 학습할 수 있도록
# 동등(친구·연인) / 수직(선배-후배·선생님-학생) / 초면(낯선 사람)의 스펙트럼을 커버한다.
RELATIONSHIP_TYPES = ["친구", "선배-후배", "연인", "선생님-학생", "낯선 사람"]


# ----------------------------------------------------------------
# [왜 이 함수가 필요한가?]
#
# build_user_message()는 LLM에게 대화 기능 목록을 다음 형태로 주입한다:
#   "[요청자-조력자] 장소 묻기 | 물건 사기 | ..."
#   "[각자 목표] 취향 묻기 | 경험 묻기 | ..."
#
# [] 태그는 LLM이 mission 구조(요청자-조력자인지, 각자 목표인지)를 판단하기 위한
# '힌트'로 설계된 것이고, 최종 JSON 출력의 dialogue_function 배열에는
# 기능명만("취향 묻기") 담겨야 한다.
#
# 그런데 LLM이 이 태그를 그대로 출력에 포함시키는 오류가 발생한다:
#   실패 유형 1: ["[각자 목표] 취향 묻기"]  ← 태그가 값 앞에 붙어 나옴
#   실패 유형 2: ["각자 목표"]              ← 기능명 대신 카테고리명 자체가 들어옴
#
# 시스템 프롬프트에 ⑥ 제약을 추가해 1차 방어를 하지만,
# LLM은 확률적으로 제약을 어기는 경우가 있으므로
# 이 함수로 2차(후처리) 방어를 한다.
#
# [정규식 설명]
#   r"^\[.*?\]\s*"
#   ^        → 문자열 맨 앞에서만 매칭 (값 중간의 [] 는 건드리지 않음)
#   \[.*?\]  → "[" 로 시작해 "]" 로 끝나는 최소 매칭 (예: "[각자 목표]")
#   \s*      → 태그 뒤 공백 제거
#
# [호출부 주의사항]
#   실패 유형 2("각자 목표")는 태그 제거 후 빈 문자열("")이 된다.
#   호출부에서 반드시 `if f` 로 빈 문자열을 필터해야 한다.
#   예) cleaned = [f for f in clean_dialogue_functions(items) if f]
# ----------------------------------------------------------------
def clean_dialogue_functions(items: list[str]) -> list[str]:
    """LLM 출력의 dialogue_function 배열에서 카테고리 태그를 제거한다.

    예) "[각자 목표] 취향 묻기" → "취향 묻기"
        "각자 목표"             → "" (빈 문자열 → 호출부에서 if f 필터 필요)
    """
    return [re.sub(r"^\[.*?\]\s*", "", item).strip() for item in items]


def build_system_prompt(korean_level: str = "Beginner") -> str:
    """시스템 프롬프트를 반환한다.

    korean_level을 LEVEL_MAP으로 급수로 변환해 프롬프트에 주입한다.
    """
    return SCENARIO_SYSTEM_PROMPT.format(
        korean_level=LEVEL_MAP.get(korean_level, "1급")
    )


def build_user_message(
    location: str, korean_level: str = "Beginner", location_context: str = ""
) -> str:
    """유저 프롬프트를 반환한다.

    관계 유형은 RELATIONSHIP_TYPES에서 랜덤으로 선택되므로
    호출할 때마다 다른 시나리오가 생성된다.
    location_context는 generate_location_context 노드가 사전에 생성한 장소 정보다.
    """
    level_str = LEVEL_MAP.get(korean_level, "1급")
    relationship_type = random.choice(RELATIONSHIP_TYPES)
    funcs = DIALOGUE_FUNCTIONS.get(level_str, DIALOGUE_FUNCTIONS["1급"])
    # DIALOGUE_FUNCTIONS[level_str]의 카테고리별 항목을
    # "[카테고리] 기능1 | 기능2 | ..." 형태로 조합해 {dialogue_functions}에 주입
    dialogue_functions = "\n   ".join(
        f"[{category}] {' | '.join(items)}" for category, items in funcs.items()
    )
    return SCENARIO_USER_PROMPT_TEMPLATE.format(
        korean_level=level_str,
        location=location,
        relationship_type=relationship_type,
        dialogue_functions=dialogue_functions,
        location_context=location_context,
    )


# 투두
# - 잘 돌아가는지 테스트 확인
# - 다른 프롬프트 만들기(ai 응답/대화 관련 프롬프트) <- 쪼개기
