"""education_based.py

차기 프로덕션 시나리오 프롬프트.
노드 방식(location_context 동적 생성) 폐기 후, 하드코딩된 어휘·활동 목록 기반으로 재설계.
고도화 완료 시 01_conversation/prompts/scenario.py 를 이 버전으로 교체한다.
"""

import random
import re

VERSION = "education_based"

# ================================================================
# 데이터
# ================================================================

LEVEL_MAP: dict[str, str] = {
    "Beginner": "1급",
    "Intermediate": "3급",
    "Advanced": "5급",
}
# 한국어 표준 과정(1~2급: Beginner / 3~4급: Intermediate / 5~6급: Advanced) 기준으로
# 각 구간의 시작 급수(1·3·5급)를 대표값으로 사용해 가장 쉬운 레벨부터 시작하도록 설계.

# build_user_message() 호출 시 level 인자("Beginner" 등)를 이 딕셔너리로 변환한다.
# 변환된 값(예: "1급")이 _USER_PROMPT_TEMPLATE의 {level} 자리에 주입된다.
# LLM은 항상 "1급 / 3급 / 5급" 형태로 학습자 수준을 받는다.

DIALOGUE_FUNCTIONS: dict[str, dict[str, list[str]]] = {
    "1급": {
        "요청자-조력자": ["장소 묻기", "물건 사기", "음식 주문하기", "시간 묻기"],
        "각자 목표":     ["일상 묻기", "취향 묻기", "경험 묻기",
                         "기분 묻기", "날씨/풍경 묻기", "어제/주말에 한 일 묻기"],
        "자유 선택":    ["자기소개", "약속 정하기"],
    },
    "2급": {
        "요청자-조력자": ["음식 주문하기", "물건 비교하기", "교환/환불 요청하기",
                         "교통/길 찾기", "전화 통화하기", "허락 구하기", 
                         "도움 요청하기", "거절하기"],
        "각자 목표":     ["안부/근황 묻기", "외모/성격 묘사하기", 
                         "가족/고향 소개하기", "여행 계획 말하기"],
        "자유 선택":    ["감정 표현하기", "건강 상태 설명하기", 
                        "모임 제안하기", "미래 계획 말하기"],
    },
}
# 한국어 표준 교육과정에 기반한 교재들의 급수별 말하기 목표를 종합한 것으로,
# 페르소나 mission을 교육적 근거 위에서 생성하기 위한 비계(scaffolding) 역할을 한다.
# 카테고리(요청자-조력자 / 각자 목표 / 자유 선택)는 A·B 간 mission을 자연스럽게
# 분배하기 위한 분류 기준이며, dialogue_function 자체는 최종 JSON에 포함되지만
# mission을 이끌어내기 위한 중간 장치로 설계되었다.

# build_user_message() 호출 시 급수를 키로 카테고리별 목록을 포맷팅해 주입한다.
# → {dialogue_functions} 자리에 "[카테고리] 기능1 | 기능2 | ..." 형태로 렌더링된다.
# → LLM이 [] 태그를 보고 mission 구조를 직접 판단하므로 시스템 프롬프트에서 목록 중복 불필요.

_RELATIONSHIP_TYPES = ["친구", "선배-후배", "연인", "선생님-학생", "낯선 사람"]
# MVP 대표 페르소나(20대 유학생)가 친밀도·위계에 따른 
# 적절한 한국어 표현을 학습할 수 있도록 대화 참여자 간 관계를 다섯 가지로 설정했다.
# 동등(친구·연인) / 수직(선배-후배·선생님-학생) / 초면(낯선 사람)의 스펙트럼을 커버한다.

# build_user_message() 호출 시 random.choice로 하나를 무작위 선택해 {relationship_type}에 주입
# → 매 호출마다 다른 관계 유형이 선택되어 시나리오 다양성을 확보한다.
# build_user_message() 내부에서만 소비되므로 _ 접두사(모듈 내부 전용)를 사용.

PERSONA_VOCAB: dict[str, list[str]] = {
    "1급": [
        "회사원", "의사", "가수", "영화배우",
        "아주머니", "아저씨", "할머니", "할아버지",
        "가게 주인", "식당 주인", "카페 주인", "서점 주인",
        "편의점 주인", "편의점 직원", "백화점 직원",
        "은행 직원", "호텔 직원", "병원 직원",
    ],
}
# 관계 유형이 "낯선 사람"일 때 B 페르소나의 직업·신분 어휘로 사용.
# 낯선 사람 외 관계에는 주입하지 않는다.
# vocabulary.json에 직업명이 미포함되어 있으므로 별도 관리. (To-do [2] 참고)
# 2급 어휘는 추후 추가 예정.
#
# [설계 방향] 장소 한정 역할(따릉이 대여소 직원, 한강 관리소 직원 등)은
# 이 목록에 추가하지 않고 location_vocab 단에서 다룬다.
# → 일반 직업(배달 기사, 회사원 등)만 여기서 관리.

_ACTIVITIES: dict[str, list[str]] = {
    "한강": [
        # [구매/주문] → 음식 주문하기, 물건 사기
        "편의점에서 간식 사기", "카페에서 음료 주문하기", "카페에서 디저트 주문하기",
        "배달 음식 주문하기", "피크닉 용품 빌리기",
        # [시설 이용/위치] → 장소 묻기
        "가까운 화장실 찾기", "지하철역 가는 길 묻기", "편의점 찾기", "카페 찾기", "쓰레기통 찾기",
        # [시간/계획] → 시간 묻기, 약속 정하기
        "분수 쇼 시작 시간 확인하기", "친구와 만날 장소 정하기",
        "수영장 운영 시간 묻기", "음식 메뉴 고르기",
        # [경험/일상] → 경험 묻기, 취향 묻기, 기분 묻기, 일상 묻기, 자기소개
        "오늘 기분이 어떤지 이야기하기", "좋아하는 노래 같이 듣기",
        "러닝 크루에서 자기소개하기", "한강에 자주 오는지 묻기",
        # [감상/휴식] → 날씨/풍경 묻기
        "무지개 분수 구경하기", "노을 사진 찍기",
        "돗자리 펴고 쉬기", "야경 감상하며 산책하기",
    ],
}
# 장소별 활동 풀(_ACTIVITIES) — LLM이 적합한 활동을 고르게 선택하도록 돕는 참고 목록.
#
# [역할]
#   LLM이 장소에서 가능한 활동을 충분히 알지 못하거나 task 중심 활동에 편중될 수 있으므로
#   활동 풀을 명시적으로 제공한다.
#   - [구매/주문], [시설 이용/위치]: 장소 특화 정보 — 없으면 LLM이 스스로 떠올리기 어려움
#   - [경험/일상], [감상/휴식]: 균형추 — 소프트한 대화 기능(기분·취향 묻기 등) 선택 확률 확보
#
# [활동명 수준]
#   행위 수준으로 작성 ("편의점에서 간식 사기") — 구체적 물품은 포함하지 않는다.
#   어휘 다양성은 프롬프트 하단 ## 참고 어휘 섹션이 담당한다.
#
# [주입 방식]
#   build_user_message() 호출 시 전체 목록을 {activities}에 주입.
#   장소별 편중이 확인되면 _ACTIVITY_CAUTIONS에 Caution 문구를 추가해 프롬프트 레벨에서 제어.


_ACTIVITY_CAUTIONS: dict[str, str] = {
    "한강": "자전거 관련 활동에 편중되지 말 것.",
}
# 장소별로 LLM이 특정 활동에 과도하게 편중되는 경우 여기에 추가한다.
# 해당 장소의 주의 문구가 없으면 빈 문자열이 주입된다.


# ================================================================
# 프롬프트
# ================================================================
#
# [시스템 프롬프트 vs 유저 프롬프트 템플릿]
#
# SYSTEM_PROMPT        — 요청마다 변하지 않는 고정 규칙
#                        - LLM의 역할 정의
#                        - 허용값·금지 규칙 (항상 적용)
#                        - 출력 JSON 스키마
#                        → 모든 호출에서 동일하게 전달됨
#
# _USER_PROMPT_TEMPLATE — 요청마다 달라지는 동적 내용
#                        - 변수 입력값 ({level}, {location} 등)
#                        - CoT 실행 순서 (생성 흐름 안내)
#                        - 예시 (현재 1급 고정 → 급수 확장 시 {level}별로 분기 예정)
#                        - 참고 어휘 (현재 하드코딩 → [2] 완료 후 동적 주입 예정)
#                        → build_user_message() 호출 시 변수 주입 후 완성됨
#
# ================================================================

SYSTEM_PROMPT = """
## Role
너는 학습자의 한국어 수준에 맞춘 대화 시나리오 설계자다.
장소와 관계 유형을 입력받아 아래 제약을 지키며 JSON을 생성한다.

## Constraints

### ① role·age per relationship_type
  - 친구        → role: 친구 / 친구                        | age: 동갑
  - 선배-후배   → role: 선배 / 후배 (직업명 금지)           | age: 차이 1~5살
  - 선생님-학생 → role: 선생님 / 학생                      | age: 차이 10살 이상
  - 연인        → role: 남자 친구 / 여자 친구 (A/B 교차 가능) | age: 차이 0~3살
  - 낯선 사람   → role: 대학생(고정) / 직업·신분            | age: 제한 없음

### ② personas
  - A 또는 B 중 1명은 반드시 20대 대학생
  - A 또는 B 중 1명은 반드시 외국인 이름 사용

### ③ mission
  - A·B 각 persona가 이 대화를 통해 달성하고 싶은 목표 (30자 이내)
  - mission 구조는 {dialogue_functions}의 [] 태그를 따른다.
    카테고리는 [요청자-조력자] / [각자 목표] / [자유 선택] 세 가지다.
    [요청자-조력자] → A는 요청자, B는 조력자
      Example) A mission: "화장실이 어디에 있는지 알고 싶어요." / B mission: "화장실 위치를 알려 주고 싶어요."
    [각자 목표] → A·B 각자 궁금한 것을 mission으로
      mission은 "상대방에 대해 알고 싶은 것"으로 작성하되,
      지금 함께하는 활동이나 {location} 상황이 대화의 계기가 될 것
      Example) A mission: "상대방이 한강에서 자전거 타기를 좋아하는지 알고 싶어요."
               B mission: "상대방이 좋아하는 한강 간식이 궁금해요."
      Counter-example) "상대방의 주말 일과가 궁금해요." — {location} 상황과 무관한 일상 질문
    [자유 선택] → 상황에 맞게 선택
    [예외] 낯선 사람 관계 → dialogue_function에 관계없이 항상 요청자-조력자 구조

  - Counter-example) "친구와 만나기로 했어요." (완료된 상황 금지)
                     "오늘 저녁에 한강에서 함께 달리기 할래요?" (대화에 활용할 첫 문장 금지)

### ④ scenario_description
  - 학습자가 대화 맥락을 이해할 수 있도록 1~2문장으로 작성
  - Format: [A.name]은/는 ~하고 싶고, [B.name]은/는 ~합니다.
    ~하고 싶고/~합니다 부분은 각 persona의 mission을 바탕으로 작성
    relationship_type은 첫 문장에 자연스러운 한국어로 녹여 표현할 것
    Example)
      친구 / 연인        → "{location}에서 만난 [relationship_type]인 두 사람의 대화입니다."
      선배-후배 / 선생님-학생 → "{location}에서 함께하는 [A.role]과 [B.role]의 대화입니다."
      낯선 사람          → "{location}에서 처음 만난 두 사람의 대화입니다."
  - Constraint: 첫 문장에 {location}이 자연스럽게 포함될 것

### ⑤ expression
  - 어휘와 문법은 유저 프롬프트에서 주어진 학습자 수준에 맞게 작성
  - 단, 장소명·시설명·고유명사(따릉이, 반포 무지개 분수 등)는 수준과 무관하게 자유롭게 사용 가능
  - 유저 프롬프트의 ## 참고 어휘를 mission·scenario_description 작성 시 적극 반영

### ⑥ dialogue_function
  - 배열 각 항목은 기능명만 포함할 것
  - 카테고리 태그([요청자-조력자] 등)나 카테고리명 자체를 항목 값으로 쓰는 것은 금지
  - Example) ["장소 묻기", "취향 묻기"]
  - Counter-example) ["[각자 목표] 취향 묻기"], ["각자 목표"]

## Output Schema

{
  "scenario_title": "",
  "scenario_description": "",
  "location": "",
  "dialogue_function": [],
  "relationship_type": "",
  "personas": {
    "A": { "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" },
    "B": { "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" }
  }
}
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
"""

_USER_PROMPT_TEMPLATE = """
학습자 수준: {level}
장소: {location}
관계 유형: {relationship_type}

## 실행 순서
0. [입력 확인] {relationship_type} — 주어진 값 그대로 사용

1. [활동 선택] {relationship_type}과 가장 자연스러운 활동 선택
   낯선 사람 → 반드시 1개만 선택 | 나머지 → 1~2개 선택
   {activity_caution}Note) 아래 목록 전체를 고르게 참고할 것.
     {activities}

2. [dialogue_function 확정] 선택한 활동에 가장 자연스럽게 연결되는 dialogue_function을 아래 목록에서 확정

   {dialogue_functions}

3. [personas 설정] (## Constraints ① role 규칙 준수)

4. [mission 생성] (## Constraints ③ 준수, 참고 어휘 활용)

5. [scenario_description 생성] (## Constraints ④ Format 준수, 각 persona의 mission 참고)

6. JSON 출력 — 시스템 프롬프트의 출력 스키마를 따를 것

## 예시
예시 1 - 입력: 장소=백화점, 관계 유형=낯선 사람 → [요청자-조력자] + 외국인 이름 A
{{ "scenario_title": "백화점에서 화장실을 찾는 대학생",
  "scenario_description": "백화점에서 처음 만난 두 사람의 대화입니다. 리사는 화장실이 어디에 있는지 알고 싶고, 영은은 위치를 알려 주고 싶어합니다.",
  "location": "백화점",
  "dialogue_function": ["장소 묻기"], "relationship_type": "낯선 사람",
  "personas": {{
    "A": {{ "name": "리사", "age": "21", "gender": "여", "role": "대학생", "mission": "화장실이 어디에 있는지 알고 싶어요." }},
    "B": {{ "name": "영은", "age": "35", "gender": "여", "role": "백화점 직원", "mission": "화장실 위치를 알려 주고 싶어요." }}
  }}
}}

예시 2 - 입력: 장소=카페, 관계 유형=연인 → [각자 목표] + 외국인 이름 B
{{ "scenario_title": "카페에서 디저트 이야기를 나누는 연인",
  "scenario_description": "카페에서 만난 연인 관계인 두 사람의 대화입니다. 현아는 제이크가 좋아하는 음료를 알고 싶고, 제이크는 현아의 오늘 기분이 궁금합니다.",
  "location": "카페",
  "dialogue_function": ["취향 묻기", "기분 묻기"], "relationship_type": "연인",
  "personas": {{
    "A": {{ "name": "현아", "age": "23", "gender": "여", "role": "여자 친구", "mission": "남자 친구가 좋아하는 음료를 알고 싶어요." }},
    "B": {{ "name": "제이크", "age": "24", "gender": "남", "role": "남자 친구", "mission": "여자 친구의 오늘 기분을 알고 싶어요." }}
  }}
}}

## 참고 어휘
{persona_vocab}음식: 김밥, 라면, 떡볶이, 치킨, 딸기, 귤, 사과, 바나나, 빵, 아이스크림
동사: 가다, 오다, 알다, 모르다, 찾다, 묻다, 사다, 먹다, 마시다, 만나다, 기다리다, 좋아하다, 싫어하다, 지내다, 다니다
형용사: 좋다, 가깝다, 멀다, 많다, 싸다, 비싸다, 맛있다, 바쁘다, 괜찮다
"""

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
# 시스템 프롬프트에 ⑤ 제약을 추가해 1차 방어를 하지만,
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

    예) "[각자 목표] 취향 묻기" → "취향 문기"
        "각자 목표"             → "" (빈 문자열 → 호출부에서 if f 필터 필요)
    """
    return [re.sub(r"^\[.*?\]\s*", "", item).strip() for item in items]

def _get_activities(location: str) -> tuple[str, str]:
    """_ACTIVITIES에서 location에 해당하는 전체 활동 목록을 반환한다.

    Returns:
        activities_str   — 프롬프트용 활동 목록 문자열 ({activities} 자리에 주입)
        activity_caution — 장소별 편중 주의 문구 ({activity_caution} 자리에 주입, 없으면 "")

    location이 _ACTIVITIES에 없으면 빈 문자열을 반환한다.
    """
    pool = _ACTIVITIES.get(location)
    if not pool:
        return "(활동 목록 없음 — 장소에 맞게 자유롭게 선택하세요.)", ""
    activities_str = ", ".join(pool)
    activity_caution = _ACTIVITY_CAUTIONS.get(location, "")
    return activities_str, activity_caution


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_message(location: str, level: str = "Beginner") -> str:
    level_str = LEVEL_MAP.get(level, "1급")
    relationship_type = random.choice(_RELATIONSHIP_TYPES)
    funcs = DIALOGUE_FUNCTIONS.get(level_str, DIALOGUE_FUNCTIONS["1급"])
    # DIALOGUE_FUNCTIONS[level_str]의 카테고리별 항목을
    # "[카테고리] 기능1 | 기능2 | ..." 형태로 조합해 {dialogue_functions}에 주입
    dialogue_functions = "\n   ".join(
        f"[{category}] {' | '.join(items)}"
        for category, items in funcs.items()
    )
    activities, activity_caution = _get_activities(location)
    caution_str = f"Caution) {activity_caution}\n   " if activity_caution else ""
    if relationship_type == "낯선 사람":
        vocab_list = PERSONA_VOCAB.get(level_str, PERSONA_VOCAB["1급"])
        persona_vocab = "인물 (낯선 사람 B 전용): " + ", ".join(vocab_list) + "\n"
    else:
        persona_vocab = ""
    return _USER_PROMPT_TEMPLATE.format(
        level=level_str,
        location=location,
        relationship_type=relationship_type,
        dialogue_functions=dialogue_functions,
        activities=activities,
        activity_caution=caution_str,
        persona_vocab=persona_vocab,
    )


# ================================================================
# 현재 파일 상황 (as-is)
# ================================================================

# [코드가 처리]
# - 관계 유형: random.choice → {relationship_type} 주입
# - 학습자 수준: LEVEL_MAP으로 변환 → {level} 주입
# - 대화 기능 목록: DIALOGUE_FUNCTIONS[급수] 카테고리별 포맷팅 → {dialogue_functions} 주입
# - 장소 활동 목록: 하드코딩 (유저 프롬프트 참고 블록) → [3] 완료 후 동적 주입 예정
# - 인물 어휘: PERSONA_VOCAB[급수] → "낯선 사람"일 때만 {persona_vocab} 주입
# - 참고 어휘(음식·동사·형용사): 하드코딩 → [2] 완료 후 동적 주입 예정

# [LLM이 처리]
# 0. relationship_type 확인 (주어진 값 그대로)
# 1. 장소 활동 중 relationship_type과 자연스러운 것 선택
# 2. 선택한 활동에 맞는 dialogue_function 확정
# 3. personas 설정 (## 제약 ① 준수)
# 4. mission 생성 (## 제약 ③ 준수)
# 5. scenario_description 생성 (## 제약 ④ 준수, mission 참고)
# 6. JSON 출력

# ================================================================
# To-do 및 To-be
# ================================================================
#
# [2] vocabulary 동적 주입 ← [1] 완료 후
#
# as-is: 참고 어휘 프롬프트 하단에 하드코딩 (1급 기준 고정)
#         → 급수 추가·수정 시 프롬프트 직접 수정 필요
#         → 낯선 사람 아닌 관계에도 인물 어휘 불필요하게 주입
#         → 2급 이상으로 확장 시 인물/어휘 모두 수동 교체 필요
#
# 실제 vocabulary.json 구조 (10,635개):
#   [
#     { "index": "1_1", "word": "가게", "kind": "명사", "example": "가게에 가다" },
#     { "index": "2_5", "word": "간호사", "kind": "명사", "example": "..." },
#     ...
#   ]
#   → index 앞자리 = 급수 ("1_" → 1급, "2_" → 2급)
#   → kind 필드로 품사 구분 (단, 공백 포함 오염 있음 → .strip() 필요)
#   → "인물" 카테고리 없음 → 직업명은 vocabulary.json에 미포함
#
# to-be:
#   ① 일반 어휘 — vocabulary.json에서 동적 필터링
#     → index.startswith("{급수}_") 로 급수 필터
#     → kind.strip() in ["명사", "동사", "형용사"] 로 품사 필터
#     → 필터된 단어 목록을 프롬프트에 주입
#     → LLM이 대화 기능({dialogue_function})을 보고 어울리는 단어 선택 (열린 구조)
#
#   ② 인물 어휘 — 급수별 별도 관리 (vocabulary.json에 없음)
#     → 직업명·신분어는 vocabulary.json에 포함 안 되어 있음
#     → 별도 dict 또는 파일로 급수별 큐레이션 필요
#     → 예:
#       PERSONA_VOCAB = {
#         "1급": ["회사원", "의사", "가게 주인", "편의점 직원", "아주머니", "아저씨", ...],
#         "2급": ["간호사", "경찰관", "선생님", "은행원", ...],
#       }
#     → 관계 유형이 "낯선 사람"일 때만 해당 급수 인물 어휘 주입
#
#   검증 후: 어휘 선택이 여전히 느슨하면 대화 기능별 명사 힌트 추가 고려
#            (예: "음식 주문하기" → 음식 명사 우선 주입)

# ----------------------------------------------------------------

# [3] topic DB 설계 ← [2] 검증 후 시나리오 여전히 밋밋하면
#
# as-is (현재 구조):
#   _ACTIVITIES dict — 장소별 활동 목록 (행위 수준 문자열, 전체 주입)
#   → 편중 방지: _ACTIVITY_CAUTIONS로 프롬프트 레벨 제어
#   → location_vocab 미사용 (stub 상태) — To-do [3] 완료 후 복원 예정
#   → Python dict 하드코딩 (한강·지하철·편의점 3개 장소)
#
# to-be (설계 방향 확정):
#   _ACTIVITIES와 location_vocab의 역할 분리
#     - _ACTIVITIES  → 일반 행위 수준 활동 ("화장실 찾기", "음식 주문하기" 등)
#                      LLM이 장소 맥락 없이도 알 수 있는 것들
#     - location_vocab → 장소 특화 고유명사 ("따릉이 대여소", "반포 무지개 분수" 등)
#                        LLM이 스스로 떠올리기 어려운 것, 참고 어휘로 주입
#   → LLM이 일반 활동을 선택한 뒤 location_vocab의 고유명사를 mission에 활용하는 구조
#   → 장소별 고유명사가 _ACTIVITIES 풀을 늘리지 않으므로 쏠림 현상 방지
#
#   location_vocab 자료구조 설계 방향 (확정):
#     - "topic" 아닌 "vocab"으로 명명 — 활동(할 것)이 아니라 알아야 할 고유 용어/시설명
#     - 항목 구조: { "term": "따릉이", "description": "서울시 공공자전거 대여 서비스" }
#     - 프롬프트 주입 레이블은 '장소 고유명사' 또는 '장소 시설명'으로 구분
#       → 참고 어휘(일반 한국어 어휘)와 혼동 방지
#
#   추가 to-be:
#   - 장소 확장: 현재 3개 장소 → 서비스 전체 장소 커버
#   - 외부화: Python dict → JSON/DB 파일로 분리
#   - topic : dialogue_function 힌트 추가 고려

# ----------------------------------------------------------------

# [4] mission 구조 카테고리 확장 ← 3급 이상 작업 시작할 때
#
# as-is: DIALOGUE_FUNCTIONS를 카테고리(요청자-조력자/각자 목표/자유 선택) 딕셔너리로 구조화
#         → 1·2급 수동 분류 완료
#         → 3급 이상 추가 시 동일하게 수동 분류 필요 (자동화 미완)
#
# to-be: 자동화 또는 분류 기준 재정의 (방법 미정)