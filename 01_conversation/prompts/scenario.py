import random

SCENARIO_SYSTEM_PROMPT = """
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
  - 학습자 수준({korean_level})에 맞는 어휘 사용

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
  - 어휘와 문법은 한국어 {korean_level} 학습자 수준을 유지한다
  - 단, 장소명·브랜드명·음식명·인물 이름 등 고유명사는 자유롭게 사용한다
  - 장소의 실제 명소, 시설, 문화적 맥락을 반영해 생동감 있는 시나리오를 만든다
  - 지하철 노선의 경우 실제 환승 정보를 정확히 반영하라
"""
 
SCENARIO_USER_PROMPT_TEMPLATE = """
학습자의 한국어 수준: {korean_level}
장소: {location}
관계 유형: {relationship_type}
 
## 실행 순서
1. 대화 기능 결정 — {location}에서 할 수 있는 활동들을 다양하게 떠올린 뒤 아래 선택지와 잘 어울리는 것을 정할 것.
   낯선 사람 → 반드시 1개만 선택 | 나머지 → 1~2개 선택
 
   선택지: {dialogue_functions}

   참고) {location_context}
   위 맥락은 대화 소재 참고용이다. 대화는 반드시 {location} 안에서 일어나야 한다.
   실제 사실을 왜곡하지 말고, 불확실한 정보는 사용하지 말라.

2. 인물 설정 — 입력받은 관계 유형에 맞게 A, B 확정 (위 role 규칙 참고)
 
3. mission 생성 — 1번 대화 기능 기반, mission 패턴에 따라 비대칭/대칭 적용
 
4. JSON 출력 — 아래 형식만 출력 (설명·주석·``` 없이)
 
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
{{ "scenario_title": "백화점에서 팝업 스토어를 찾는 대학생",
  "scenario_description": "낯선 사람끼리의 대화입니다. 리사는 나이키 팝업 스토어가 몇 층에 있는지 알고 싶고, 영은은 위치를 안내해 주고 싶어합니다.",
  "location": "백화점",
  "dialogue_function": ["장소 묻기"], "relationship_type": "낯선 사람",
  "personas": {{
    "A": {{ "name": "리사", "age": "21", "gender": "여", "role": "대학생", "mission": "나이키 팝업 스토어가 몇 층에 있는지 알고 싶어요." }},
    "B": {{ "name": "영은", "age": "35", "gender": "여", "role": "백화점 직원", "mission": "팝업 스토어 위치를 알려 주고 싶어요." }}
  }}
}}

예시 2 - 입력: 장소=카페, 관계 유형=연인 → 대칭 패턴 + 외국인 이름 B
{{ "scenario_title": "카페에서 디저트 이야기를 나누는 연인",
  "scenario_description": "연인 관계인 두 사람의 대화입니다. 현아는 제이크가 두쫀쿠를 먹어 본 적이 있는지 알고 싶고, 제이크는 현아가 좋아하는 다른 카페 디저트가 궁금합니다.",
  "location": "카페",
  "dialogue_function": ["취향 묻기", "경험 묻기"], "relationship_type": "연인",
  "personas": {{
    "A": {{ "name": "현아", "age": 23, "gender": "여", "role": "여자 친구", "mission": "남자 친구가 두쫀쿠를 먹어 본 적이 있는지 알고 싶어요." }},
    "B": {{ "name": "제이크", "age": 24, "gender": "남", "role": "남자 친구", "mission": "여자 친구가 두쫀쿠 말고 또 좋아하는 카페 디저트가 있는지 알고 싶어요." }}
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

# 급수별 대화 기능 목록. build_user_message 호출 시 해당 급수 목록이 프롬프트에 주입된다.
# 각 서비스 레벨 내 세부 티어(급수)가 올라갈수록 더 높은 급수 목록이 사용된다.
#   Beginner    → 1급, 2급
#   Intermediate → 3급, 4급  (추가 예정)
#   Advanced    → 5급, 6급  (추가 예정)
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

# 지원하는 관계 유형 목록. build_user_message 호출 시 랜덤으로 하나 선택된다.
RELATIONSHIP_TYPES = ["친구", "선배-후배", "연인", "선생님-학생", "낯선 사람"]


def build_system_prompt(korean_level: str = "Beginner") -> str:
    """시스템 프롬프트를 반환한다.

    korean_level을 LEVEL_MAP으로 급수로 변환해 프롬프트에 주입한다.
    """
    return SCENARIO_SYSTEM_PROMPT.format(korean_level=LEVEL_MAP.get(korean_level, "1급"))


def build_user_message(location: str, korean_level: str = "Beginner", location_context: str = "") -> str:
    """유저 프롬프트를 반환한다.

    관계 유형은 RELATIONSHIP_TYPES에서 랜덤으로 선택되므로
    호출할 때마다 다른 시나리오가 생성된다.
    location_context는 generate_location_context 노드가 사전에 생성한 장소 정보다.
    """
    level_str = LEVEL_MAP.get(korean_level, "1급")
    relationship_type = random.choice(RELATIONSHIP_TYPES)
    dialogue_functions = " | ".join(DIALOGUE_FUNCTIONS.get(level_str, DIALOGUE_FUNCTIONS["1급"]))
    return SCENARIO_USER_PROMPT_TEMPLATE.format(
        korean_level=level_str,
        location=location,
        relationship_type=relationship_type,
        dialogue_functions=dialogue_functions,
        location_context=location_context,
    )


# 투두
# - 1급 하드코딩된 내용을 변수로 빼서 프롬프트에 주입
# - 잘 돌아가는지 테스트 확인

# - 다른 프롬프트 만들기(ai 응답/대화 관련 프롬프트) <- 쪼개기