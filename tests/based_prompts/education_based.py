"""education_based.py

비교 기준 프롬프트 (baseline).
location_context 노드 없이 하드코딩된 어휘·활동 목록만으로 시나리오를 생성한다.
현재 노드 방식(location_context 주입)과의 품질 차이를 데이터로 검증하기 위한 용도.

※ 프로덕션 코드(01_conversation/prompts/scenario.py)를 건드리지 않는다.
"""

import random

VERSION = "education_based"

SYSTEM_PROMPT = """
## Role
너는 학습자의 한국어 수준에 맞춘 대화 시나리오 설계자다.
장소와 관계 유형을 입력받아 아래 제약을 지키며 JSON을 생성한다.

## 제약

### ① role 및 나이 조건 — 관계 유형별 허용값 (반드시 아래 규칙만 사용)
  - 친구        → role: 친구 / 친구           | 나이: 동갑
  - 선배-후배   → role: 선배 / 후배           | 나이: 차이 1~5살
  - 선생님-학생 → role: 선생님 / 학생         | 나이: 차이 10살 이상
  - 연인        → role: 남자 친구 / 여자 친구  | 나이: 차이 0~3살 (성별에 따라 A/B 교차 가능)
  - 낯선 사람   → role: 대학생(고정) / 직업·신분 | 나이: 제한 없음

  - 선배-후배의 role은 반드시 "선배" / "후배" 만 허용. 직업명(회사원 등) 사용 금지.
  - 직업·신분(회사원, 아저씨 등)은 낯선 사람에서만 B에 사용 가능.

### ② 인물 조건
  - A 또는 B 중 1명은 반드시 20대 대학생
  - A 또는 B 중 1명은 반드시 외국인 이름 사용

### ③ 상황 안내(scenario_description) 조건
  - 학습자가 대화 맥락을 이해할 수 있도록 1~2문장으로 작성
  - 형식: "[관계]인 두 사람의 대화입니다. [A이름]은 ~하고 싶고, [B이름]은/는 ~합니다."
  - 한국어 1급 학습자가 이해할 수 있는 어휘 사용

### ④ 대화 목표(mission) 조건
  - 이 대화로 전달하고 싶은 정보나 달성하고픈 행동 (30자 이내)
  - 반드시 1단계에서 결정한 [대화 기능] 참고
  - 비대칭/대칭 패턴은 대화 기능(dialogue_function)을 기준으로 결정한다.

  [비대칭 필수] 대화 기능이 아래 중 하나인 경우 → A는 요청자, B는 조력자
    장소 묻기 | 물건 사기 | 음식 주문하기 | 시간 묻기
    예) A mission: "화장실이 어디에 있는지 알고 싶어요." / B mission: "화장실 위치를 알려 주고 싶어요."

  [대칭 권장] 대화 기능이 아래 중 하나인 경우 → A·B 각자 궁금한 것을 대화 목표로
    일상 묻기 | 취향 묻기 | 기분 묻기 | 날씨/풍경 묻기 | 자기소개 | 경험 묻기 | 어제/주말에 한 일 묻기
    예) A mission: "상대방이 좋아하는 음식을 알고 싶어요." / B mission: "상대방의 주말 일과가 궁금해요."

  [둘 다 허용] 약속 정하기 → 상황에 맞게 선택

  [예외] 낯선 사람 관계 → dialogue_function에 관계없이 항상 비대칭 (요청자 / 조력자)

  - 나쁜 예) "친구와 만나기로 했어요." (완료된 상황 금지)
             "오늘 저녁에 한강에서 함께 달리기 할래요?" (대화에 활용할 첫 문장 금지)

### ⑤ 표현
  - 반드시 한국어 1급 학습자가 이해할 수 있는 단어만 사용
"""

_USER_PROMPT_TEMPLATE = """
학습자 수준: {level}
장소: {location}
관계 유형: {relationship_type}

## 실행 순서
1. 대화 목표 결정 — {location}에서 할 수 있는 활동들을 다양하게 떠올린 뒤 아래 선택지와 잘 어울리는 것을 정할 것.
   낯선 사람 → 반드시 1개만 선택 | 나머지 → 1~2개 선택

   선택지: {dialogue_functions}

   참고) {location}에서 할 수 있는 활동들
     한강 → 데이트, 어학당 소풍, 견학, 산책, 달리기, 사진 찍기, 음악 듣기, 배 타기, 라면 먹기, 꽃 구경, 책 읽기,
            농구, 축구, 따릉이(자전거) 타기, 강아지 산책, 노래 부르기, 여행 이야기하기, 주말 이야기하기, 배달 음식 먹기,
            한강 편의점에서 간식 사기, 자전거 대여소 이용하기, 한강 매점에서 음식 주문하기, 반포 무지개 분수 쇼 보기
     지하철 → 출구 위치 묻기, 환승 노선 묻기, 내리는 역 묻기, 가게에서 간식 먹기, 가게에서 옷 사기,
              비켜 달라고 하기, 음악 소리 줄여 달라고 하기, 모르는 어른의 질문에 답하기
     편의점 → 1+1 행사 확인하기, 간식 추천받기, 나이 확인하기, 계산하기, 야식 고르기, 길 묻기

2. 인물 설정 — 입력받은 관계 유형에 맞게 A, B 확정 (위 role 규칙 및 아래 [참고 어휘] 참고)

3. scenario_description 생성 — 학습자가 대화 맥락을 이해할 수 있도록 1~2문장 작성

4. mission 생성 — 1번 목표 기반, mission 패턴에 따라 비대칭/대칭 적용

5. JSON 출력 — 아래 형식만 출력 (설명·주석·``` 없이)

## 출력
{{
  "scenario_title": "",
  "scenario_description": "",
  "location": "{location}",
  "dialogue_function": [],
  "relationship_type": "{relationship_type}",
  "personas": {{
    "A": {{ "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" }},
    "B": {{ "name": "", "age": "0", "gender": "남/여", "role": "", "mission": "" }}
  }}
}}

## 예시
예시 1 - 입력: 장소=백화점, 관계 유형=낯선 사람 → 비대칭 패턴 + 외국인 이름 A
{{ "scenario_title": "백화점에서 화장실을 찾는 대학생",
  "scenario_description": "낯선 사람끼리의 대화입니다. 리사는 화장실이 어디에 있는지 알고 싶고, 영은은 위치를 알려 주고 싶어합니다.",
  "location": "백화점",
  "dialogue_function": ["장소 묻기"], "relationship_type": "낯선 사람",
  "personas": {{
    "A": {{ "name": "리사", "age": "21", "gender": "여", "role": "대학생", "mission": "화장실이 어디에 있는지 알고 싶어요." }},
    "B": {{ "name": "영은", "age": "35", "gender": "여", "role": "백화점 직원", "mission": "화장실 위치를 알려 주고 싶어요." }}
  }}
}}

예시 2 - 입력: 장소=카페, 관계 유형=연인 → 대칭 패턴 + 외국인 이름 B
{{ "scenario_title": "카페에서 디저트 이야기를 나누는 연인",
  "scenario_description": "연인 관계인 두 사람의 대화입니다. 현아는 제이크가 좋아하는 음료를 알고 싶고, 제이크는 현아의 오늘 기분이 궁금합니다.",
  "location": "카페",
  "dialogue_function": ["취향 묻기", "기분 묻기"], "relationship_type": "연인",
  "personas": {{
    "A": {{ "name": "현아", "age": "23", "gender": "여", "role": "여자 친구", "mission": "남자 친구가 좋아하는 음료를 알고 싶어요." }},
    "B": {{ "name": "제이크", "age": "24", "gender": "남", "role": "남자 친구", "mission": "여자 친구의 오늘 기분을 알고 싶어요." }}
  }}
}}

## 참고 어휘
인물 (낯선 사람 B 전용): 회사원, 의사, 가수, 영화배우, 아주머니, 아저씨, 할머니, 할아버지,
      가게 주인, 식당 주인, 카페 주인, 서점 주인, 편의점 주인, 편의점 직원, 백화점 직원,
      은행 직원, 호텔 직원, 병원 직원
음식: 김밥, 라면, 떡볶이, 치킨, 딸기, 귤, 사과, 바나나, 빵, 아이스크림
동사: 가다, 오다, 알다, 모르다, 찾다, 묻다, 사다, 먹다, 마시다, 만나다, 기다리다, 좋아하다, 싫어하다, 지내다, 다니다
형용사: 좋다, 가깝다, 멀다, 많다, 싸다, 비싸다, 맛있다, 바쁘다, 괜찮다
"""

LEVEL_MAP: dict[str, str] = {
    "Beginner": "1급",
    "Intermediate": "3급",
    "Advanced": "5급",
}

DIALOGUE_FUNCTIONS: dict[str, list[str]] = {
    "1급": [
        "자기소개", "장소 묻기", "일상 묻기", "취향 묻기", "경험 묻기",
        "물건 사기", "음식 주문하기", "시간 묻기", "약속 정하기",
        "기분 묻기", "날씨/풍경 묻기", "어제/주말에 한 일 묻기",
    ],
    "2급": [
        "안부/근황 묻기", "외모/성격 묘사하기", "감정 표현하기",
        "건강 상태 설명하기", "가족/고향 소개하기",
        "음식 주문하기", "물건 비교하기", "교환/환불 요청하기",
        "교통/길 찾기", "전화 통화하기", "여행 계획 말하기",
        "허락 구하기", "도움 요청하기", "거절하기",
        "모임 제안하기", "미래 계획 말하기",
    ],
}

_RELATIONSHIP_TYPES = ["친구", "선배-후배", "연인", "선생님-학생", "낯선 사람"]


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_message(location: str, level: str = "Beginner") -> str:
    level_str = LEVEL_MAP.get(level, "1급")
    relationship_type = random.choice(_RELATIONSHIP_TYPES)
    dialogue_functions = " | ".join(DIALOGUE_FUNCTIONS.get(level_str, DIALOGUE_FUNCTIONS["1급"]))
    return _USER_PROMPT_TEMPLATE.format(
        level=level_str,
        location=location,
        relationship_type=relationship_type,
        dialogue_functions=dialogue_functions,
    )


# 투두 (우선순위 순) — 이 파일을 기반으로 고도화 예정
#
# [1] topic 풀 설계 + CoT 고도화 + node 방식 폐기 (함께 진행)
#     - 현재 하드코딩된 장소별 활동 목록을 topic 단위로 재편
#       (예: "따릉이 타기", "수상 택시 타기")
#     - topic은 SCK 급수별 대화 기능(dialogue_function)을 기준으로 설계되므로
#       topic 풀 자체가 대화 기능을 이미 내포함
#     - 장소 독립적 topic vs 장소 종속적 topic 구조 결정 필요
#     - location_context 동적 생성 노드 제거 및 그래프 구조 단순화
#
# [2] vocabulary.json 동적 주입
#     - 현재 하단 [참고 어휘] 하드코딩 → vocabulary.json 기반 동적 주입으로 전환
#     - 대화 기능별 어휘 매핑 테이블(JSON) 별도 작성 필요 (전처리 1회 작업)
#     - 급수·대화 기능 기준으로 어휘를 동적으로 뽑아 프롬프트에 주입
#
# [3] 어휘 설명 필드 추가
#     - topic에 고유명사(따릉이 등) 포함 시 학습자를 위한 어휘 설명 필드 추가
#     - 구 location_description 필드에 해당
#     - [1] topic 구현 이후 진행
