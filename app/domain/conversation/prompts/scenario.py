"""scenario.py

시나리오 프롬프트.
노드 방식(location_context 동적 생성) 폐기 후, 하드코딩된 어휘·활동 목록 기반으로 재설계.
"""

import json
import random
from pathlib import Path

VERSION = "education_based 3.0"

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

DIALOGUE_FUNCTIONS: dict[str, list[str]] = {
    "1급": [
        "장소 묻기",
        "물건 사기",
        "음식 주문하기",
        "시간 묻기",
        "일상 묻기",
        "취향 묻기",
        "경험 묻기",
        "기분 묻기",
        "날씨/풍경 묻기",
        "어제/주말에 한 일 묻기",
        "자기소개",
        "약속 정하기",
    ],
    "2급": [
        "음식 주문하기",
        "물건 비교하기",
        "교환/환불 요청하기",
        "교통/길 찾기",
        "전화 통화하기",
        "허락 구하기",
        "도움 요청하기",
        "거절하기",
        "안부/근황 묻기",
        "외모/성격 묘사하기",
        "가족/고향 소개하기",
        "여행 계획 말하기",
        "감정 표현하기",
        "건강 상태 설명하기",
        "모임 제안하기",
        "미래 계획 말하기",
    ],
}
# 한국어 표준 교육과정에 기반한 교재들의 급수별 말하기 목표를 종합한 것으로,
# 페르소나 mission을 교육적 근거 위에서 생성하기 위한 비계(scaffolding) 역할을 한다.
# A·B mission 구조는 카테고리 태그 없이 프롬프트 원칙("같은 화제에서 각자 능동적 목표")으로 제어한다.
#
# build_user_message() 호출 시 급수를 키로 목록을 " | " 구분으로 포맷팅해 {dialogue_functions}에 주입한다.
# LLM은 활동 1개 → 이 목록에서 dialogue_function 1개를 선택한다.
#
# TODO: "3급"(Intermediate), "5급"(Advanced) 데이터 추가 필요.
#       현재 미정의 급수는 "1급" 데이터로 폴백됨 — build_user_message() 참고.

_RELATIONSHIP_TYPES = ["친구", "선배-후배", "연인", "선생님-학생", "낯선 사람"]
# MVP 대표 페르소나(20대 유학생)가 친밀도·위계에 따른
# 적절한 한국어 표현을 학습할 수 있도록 대화 참여자 간 관계를 다섯 가지로 설정했다.
# 동등(친구·연인) / 수직(선배-후배·선생님-학생) / 초면(낯선 사람)의 스펙트럼을 커버한다.

# build_user_message() 호출 시 random.choice로 하나를 무작위 선택해 {relationship_type}에 주입
# → 매 호출마다 다른 관계 유형이 선택되어 시나리오 다양성을 확보한다.
# build_user_message() 내부에서만 소비되므로 _ 접두사(모듈 내부 전용)를 사용.

PERSONA_VOCAB: dict[str, list[str]] = {
    "1급": [
        "회사원",
        "의사",
        "가수",
        "영화배우",
        "아주머니",
        "아저씨",
        "할머니",
        "할아버지",
        "가게 주인",
        "식당 주인",
        "카페 주인",
        "서점 주인",
        "편의점 주인",
        "편의점 직원",
        "백화점 직원",
        "은행 직원",
        "호텔 직원",
        "병원 직원",
        "배달 기사",
    ],
}
# 관계 유형이 "낯선 사람"일 때 B 페르소나의 직업·신분 어휘로 사용.
# 낯선 사람 외 관계에는 주입하지 않는다.
# vocabulary.json에 직업명이 미포함되어 있으므로 별도 관리.
# 2급 어휘는 추후 추가 예정.
#
# [설계 방향] 장소 한정 역할( 한강 관리소 직원 등)은
# 이 목록에 추가하지 않고 location_vocab 단에서 다룬다.
# → 일반 직업(배달 기사, 회사원 등)만 여기서 관리.

_ACTIVITIES: dict[str, dict[str, list[str]]] = {
    "한강": {
        "구매/주문": [
            "편의점에서 간식 사기",
            "카페에서 주문하기",
            "배달 음식 주문하기",
            "피크닉 용품(텐트·테이블·돗자리) 빌리기",
            "푸드트럭에서 음식 고르기",
        ],
        "시설 이용/위치": [
            "가까운 화장실 찾기",
            "지하철역 가는 길 묻기",
            "편의점 찾기",
            "카페 찾기",
            "쓰레기통 찾기",
            "한강 공원 안내소 찾기",
            "음식 배달 존 찾기",
            "오리배 타는 곳 묻기",
            "따릉이 빌리는 곳 찾기",
            "자전거 도로 묻기",
            "인라인 스케이트 타는 곳 묻기",
            "한강에서 보이는 건물이 뭔지 묻기",
        ],
        "시간/계획": [
            "무지개 분수가 켜지는 시간 확인하기",
            "친구와 만날 장소 정하기",
            "수영장 운영 시간 묻기",
            "음식 메뉴 고르기",
            "버스·지하철 막차 시간 확인하기",
            "불꽃축제 일정 물어보기",
            "한강 유람선 타는 시간 묻기",
        ],
        "경험/일상": [
            "오늘 기분이 어떤지 이야기하기",
            "좋아하는 노래 같이 듣기",
            "러닝 크루에서 자기소개하기",
            "한강에 자주 오는지 묻기",
            "어떤 운동을 즐기는지 묻기",
            "처음 한강에 온 경험 이야기하기",
            "한국 생활 이야기하기",
            "한강에서 라면 먹어 본 경험 묻기",
            "어학당 소풍에서 자기소개하기",
        ],
        "감상/휴식": [
            "벚꽃 구경하기",
            "노을 사진 찍기",
            "돗자리 펴고 쉬기",
            "야경 감상하기",
            "산책하기",
            "한강 불꽃놀이 이야기하기",
            "버스킹 공연 구경하기",
            "새 관찰하기",
        ],
        "제안/약속": [
            "한강에서 같이 라면 먹자고 약속하기",
            "다음에 치킨 배달시키자고 제안하기",
            "푸드트럭에서 음식 사자고 말하기",
            "다음에 같이 따릉이 타자고 약속하기",
            "저녁에 한강 산책하자고 제안하기",
            "다음에 같이 배드민턴 치자고 약속하기",
            "반포 무지개 분수 보러 가자고 약속하기",
            "다음에 야경 보러 오자고 제안하기",
            "벚꽃 피면 다시 오자고 약속하기",
            "망원 시장 가 보자고 약속하기",
        ],
    },
}
# 장소별 활동 풀(_ACTIVITIES) — LLM이 자연스러운 활동을 고르도록 돕는 가드레일.
#
# [설계 의도]
#   일반 활동과 장소 특화 활동을 카테고리로 구분해 의도적으로 섞어 놓은 구조다.
#   LLM에게 풀 전체를 주면 task 중심 활동(구매·시설 이용)에 편중되므로,
#   카테고리별 샘플링으로 매 호출마다 두 종류가 균형 있게 뽑히도록 강제한다.
#   → 카테고리 구조 자체가 가드레일 역할을 한다.
#
#   - [구매/주문], [시설 이용/위치], [스포츠/활동]: 장소 특화 활동
#       → 방치하면 LLM이 task 중심으로 쏠림
#   - [경험/일상], [감상/휴식]: 일반 활동 (어느 장소에서든 가능)
#       → 소프트한 대화 기능(기분·취향 묻기 등)이 선택되도록 균형추 역할
#
# [활동명 수준]
#   행위 수준으로 작성 ("편의점에서 간식 사기") — 구체적 물품은 포함하지 않는다.
#   어휘 다양성은 프롬프트 하단 ## 참고 어휘 섹션이 담당한다.
#
# [주입 방식]
#   build_user_message() 호출 시 카테고리별 n개씩 샘플링해 {activities}에 주입.
#   → 6개 카테고리 × 2개 = 매 호출마다 12개의 균형 잡힌 서브셋 제공.
#   편중 제어는 카테고리별 샘플링(_get_activities)으로 대응한다.


_LOCATION_VOCAB: dict[str, dict[str, list[str]]] = {
    "한강": {
        "시설명": [
            "반포 무지개 분수",
            "자전거 대여소",
            "오리배 대여소한강 유람선",
            "한강 수영장",
            "바비큐 구역",
            "피크닉 용품 대여소",
            "서울 달",
            "푸드트럭 거리",
            "자전거 도로",
            "산책로",
            "63빌딩",
            "국회의사당",
            "여의도 공원",
        ],
        "역할": [
            "한강 관리소 직원",
            "오리배 대여소 직원",
            "유람선 안내원",
            "피크닉 용품 대여소 직원",
            "한강공원 안내소 직원",
            "수영장 안내원",
            "푸드트럭 사장",
        ],
    },
}
# 장소별 시설명·역할 어휘.
#
# [구조]
#   dict[장소명, dict[카테고리, list[어휘]]]
#   카테고리는 현재 두 가지:
#     "시설명" — 장소 고유 시설·건물명 (LLM이 스스로 떠올리기 어려운 고유명사)
#               "한강에서 보이는 건물 묻기" 등 선택 시 mission에 활용됨
#     "역할"   — 낯선 사람 관계에서 B 페르소나로 쓸 수 있는 장소 한정 직함
#               PERSONA_VOCAB의 일반 직업(회사원, 의사 등)과 달리
#               해당 장소에서만 자연스럽게 등장하는 역할만 포함
#
# [주입 방식]
#   build_user_message()에서 카테고리별로 레이블을 붙여 참고 어휘 섹션에 주입.
#   예) "장소 시설명: 반포 무지개 분수,  ..."
#       "장소 한정 역할:  오리배 대여소 직원, ..."
#
# [역할 분리 기준]
#   _ACTIVITIES               → 일반 + 장소 특화 활동을 섞은 가드레일 (행위 수준, 샘플링 주입)
#   _LOCATION_VOCAB["시설명"]  → 장소 고유명사 (어휘 수준, 전체 주입 — 활동·mission 작성 힌트)
#   _LOCATION_VOCAB["역할"]   → 장소 한정 직함 (어휘 수준, 전체 주입 — 낯선 사람 B 페르소나 후보)
#   PERSONA_VOCAB             → 장소 무관 일반 직업 (어휘 수준, 전체 주입 — 낯선 사람 B 페르소나 후보)
#
# [추후 확장(to-be)]
#   설명이 필요한 시설은 ("이름", "설명(topic-description)") tuple로 확장 예정.
#   장소 추가 시 동일 구조로 키만 늘리면 됨.

_VOCAB_PATH = (
    Path(__file__).resolve().parents[3]
    / "infra"
    / "persistence"
    / "data"
    / "vocabulary.json"
)
# __file__ = tests/based_prompts/education_based.py
# .parent       → tests/based_prompts/
# .parent.parent → tests/
# .parent.parent.parent → 프로젝트 루트 (korean_learning_simulator/)
# / "database" / "vocabulary.json" → database/vocabulary.json

_VOCAB_CACHE: list[dict] | None = None
# 모듈 로드 시점에 None으로 초기화.
# _load_vocab() 최초 호출 시 JSON을 읽어 채운 뒤, 이후 호출에서는 재사용한다.
# → 같은 프로세스 안에서 build_user_message()를 여러 번 호출해도 파일 I/O는 1회.


def _load_vocab() -> list[dict]:
    """vocabulary.json을 읽어 반환한다. 두 번째 호출부터는 캐시를 반환한다.

    vocabulary.json 구조 (10,635개 항목):
      [
        { "index": "1_1", "word": "가게", "kind": "명사", "example": "가게에 가다" },
        { "index": "2_5", "word": "간호사", "kind": "명사", "example": "..." },
        ...
      ]
      - index 앞자리 숫자 = 급수 ("1_" → 1급, "2_" → 2급, …)
      - kind 필드 = 품사 (단, 공백 오염 있음 → 사용 시 .strip() 필요)
    """
    global _VOCAB_CACHE
    if _VOCAB_CACHE is None:
        with open(_VOCAB_PATH, encoding="utf-8") as f:
            _VOCAB_CACHE = json.load(f)
    return _VOCAB_CACHE


def _get_general_vocab(korean_grade: str, kinds: list[str] | None = None) -> str:
    """vocabulary.json에서 급수·품사 필터 후 프롬프트용 문자열 반환.

    Args:
        korean_grade: LEVEL_MAP으로 변환된 급수 문자열. 예) "1급", "3급", "5급"
        kinds:     포함할 품사 목록. 기본값 ["동사", "형용사"].
                   명사까지 추가하려면 ["명사", "동사", "형용사"] 전달.

    Returns:
        품사별로 그룹화된 어휘 문자열.
        예)
          동사: 가다, 오다, 알다, ...
          형용사: 좋다, 가깝다, 멀다, ...

        kind에 해당하는 단어가 하나도 없으면 해당 줄은 생략된다.

    동작 흐름:
        1. prefix 생성: "1급" → "1_"  (index 앞자리와 매칭하기 위한 변환)
        2. _load_vocab()으로 전체 어휘 목록 로드 (캐시 활용)
        3. grouped dict 초기화: {"동사": [], "형용사": []}
        4. 전체 어휘 순회
           - index가 prefix로 시작하지 않으면 skip (급수 필터)
           - kind.strip()이 grouped 키에 없으면 skip (품사 필터)
           - 통과하면 해당 품사 리스트에 word 추가
        5. 품사별로 "동사: word1, word2, ..." 형태로 join 후 반환

    주의:
        vocabulary.json의 kind 필드에 공백이 섞인 경우가 있어 .strip()으로 정규화한다.
        예) "동사 " → "동사"
    """
    if kinds is None:
        kinds = ["동사", "형용사"]
    prefix = korean_grade.replace("급", "_")  # "1급" → "1_", "3급" → "3_"
    vocab = _load_vocab()
    grouped: dict[str, list[str]] = {k: [] for k in kinds}
    for entry in vocab:
        if not entry["index"].startswith(prefix):
            continue  # 급수 불일치 → 건너뜀
        kind = entry["kind"].strip()  # 공백 오염 정규화
        if kind in grouped:
            grouped[kind].append(entry["word"])
    # words가 빈 리스트인 품사는 출력에서 제외 (if words)
    header = "일반 어휘 (mission·scenario_description 작성 시 어울리는 단어를 골라 사용할 것)"
    lines = [f"{k}: {', '.join(words)}" for k, words in grouped.items() if words]
    return header + "\n" + "\n".join(lines)


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
너는 한국 일상 대화 시나리오 설계자다.
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
  - 음식·물건이 포함되는 경우 구체적인 이름을 쓸 것 (예: 간식 → 떡볶이, 음료 → 아메리카노)
  - A와 B는 같은 화제에서 각자 능동적인 목표를 가진다.
    "왜 지금 이 장소/활동에서 이 목표가 생겼는가"가 설명 가능해야 한다.
    Example) A mission: "상대방이 제주도 여행이 처음인지 알고 싶어요."
             B mission: "상대방이 제주도에서 말을 타 보았는지 궁금해요."
  - 단, 낯선 사람 → A는 정보 요청자, B는 조력자
    Example) A mission: "화장실이 어디에 있는지 알고 싶어요."
             B mission: "화장실 위치를 알려 주고 싶어요."

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
  - Constraint: 학습자 수준({korean_level})에 맞는 어휘 사용

### ⑤ expression
  - 어휘와 문법은 유저 프롬프트에서 주어진 학습자 수준에 맞게 작성
  - 단, 장소명·시설명·고유명사는 수준과 무관하게 자유롭게 사용 가능
  - 유저 프롬프트의 ## 참고 어휘를 mission·scenario_description 작성 시 적극 반영

### ⑥ dialogue_function
  - 1개만 포함할 것
  - 배열 항목은 기능명만 포함할 것
  - Example) ["취향 묻기"]
  - Counter-example) ["취향 묻기", "기분 묻기"]

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
학습자 수준: 한국어 표준 교육과정 {level}
장소: {location}
관계 유형: {relationship_type}

## 실행 순서
0. [입력 확인] 아래 값은 코드가 주입한 것으로 그대로 사용한다.
   - relationship_type: {relationship_type}
   - 활동 풀: {activities}
   - dialogue_function 풀: {dialogue_functions}

1. [활동 선택] {relationship_type}과 가장 자연스러운 활동 1개 선택
   Note) 활동 풀 전체를 고르게 참고할 것.

2. [dialogue_function 확정] 선택한 활동에 가장 자연스럽게 연결되는 dialogue_function 1개를 dialogue_function 풀에서 확정
   낯선 사람 → 정보 요청 성격의 기능(장소 묻기, 시간 묻기 등) 우선 선택

3. [personas 설정] (## Constraints ① role 규칙 준수)

4. [mission 생성] (## Constraints ③ 준수, 참고 어휘 활용)

5. [scenario_description 생성] (## Constraints ④ Format 준수, 각 persona의 mission 참고)

6. JSON 출력 — 시스템 프롬프트의 출력 스키마를 따를 것

## 예시
예시 1 - 입력: 장소=백화점, 관계 유형=낯선 사람 + 외국인 이름 A
{{ "scenario_title": "백화점에서 화장실을 찾는 대학생",
  "scenario_description": "백화점에서 처음 만난 두 사람의 대화입니다. 리사는 화장실이 어디에 있는지 알고 싶고, 영은은 위치를 알려 주고 싶어합니다.",
  "location": "백화점",
  "dialogue_function": ["장소 묻기"], "relationship_type": "낯선 사람",
  "personas": {{
    "A": {{ "name": "리사", "age": "21", "gender": "여", "role": "대학생", "mission": "화장실이 어디에 있는지 알고 싶어요." }},
    "B": {{ "name": "영은", "age": "35", "gender": "여", "role": "백화점 직원", "mission": "화장실 위치를 알려 주고 싶어요." }}
  }}
}}

예시 2 - 입력: 장소=카페, 관계 유형=연인 + 외국인 이름 B
{{ "scenario_title": "카페에서 음료 취향을 나누는 연인",
  "scenario_description": "카페에서 만난 연인 관계인 두 사람의 대화입니다. 현아는 제이크가 아메리카노를 좋아하는지 알고 싶고, 제이크는 현아가 어떤 음료를 즐기는지 궁금합니다.",
  "location": "카페",
  "dialogue_function": ["취향 묻기"], "relationship_type": "연인",
  "personas": {{
    "A": {{ "name": "현아", "age": "23", "gender": "여", "role": "여자 친구", "mission": "남자 친구가 아메리카노를 좋아하는지 알고 싶어요." }},
    "B": {{ "name": "제이크", "age": "24", "gender": "남", "role": "남자 친구", "mission": "여자 친구가 어떤 음료를 즐기는지 궁금해요." }}
  }}
}}

## 참고 어휘
{persona_vocab}
{location_vocab}
{general_vocab}
"""

def _get_activities(location: str, n_per_category: int = 2) -> str:
    """_ACTIVITIES에서 location에 해당하는 카테고리별 활동을 샘플링해 반환한다.

    Returns:
        activities_str — 프롬프트용 활동 목록 문자열 ({activities} 자리에 주입)

    카테고리별로 n_per_category개씩 무작위 샘플링해 균형 잡힌 서브셋을 제공한다.
    location이 _ACTIVITIES에 없으면 빈 문자열을 반환한다.
    """
    categories = _ACTIVITIES.get(location)
    if not categories:
        return "(활동 목록 없음 — 장소에 맞게 자유롭게 선택하세요.)"
    sampled = []
    for items in categories.values():
        sampled.extend(random.sample(items, min(n_per_category, len(items))))
    activities_str = ", ".join(sampled)
    return activities_str


def _get_persona_vocab(korean_grade: str, location: str) -> list[str]:
    """낯선 사람 B 페르소나 후보 어휘를 일반 + 장소 한정 역할 합산해 반환한다.

    Args:
        korean_grade: "1급" / "3급" / "5급" — PERSONA_VOCAB 키로 사용
        location:  장소명 — _LOCATION_VOCAB["역할"] 조회에 사용

    Returns:
        일반 직업(PERSONA_VOCAB) + 장소 한정 직함(_LOCATION_VOCAB["역할"])이
        합산된 단일 리스트.
        예) ["회사원", "의사", ...,  "오리배 대여소 직원"..]

    [왜 이 함수가 필요한가?]
        기존에는 build_user_message()가 PERSONA_VOCAB만 직접 참조했다.
        _LOCATION_VOCAB["역할"]은 location_vocab(참고 어휘)에만 들어가 있어서
        낯선 사람 B 페르소나 후보가 두 군데로 분산되어 있었다.
        이 함수가 두 소스를 합산해 "인물 (낯선 사람 B 전용)" 레이블 아래
        단일 항목으로 제공하므로 LLM이 한 곳만 보면 된다.

    build_user_message()에서 relationship_type == "낯선 사람"일 때만 호출된다.
    location_vocab은 "시설명"만 담당하므로 역할 어휘의 이중 주입은 발생하지 않는다.
    """
    # ① 급수별 일반 직업 목록. 해당 급수 미정의 시 "1급"으로 폴백.
    #    (현재 PERSONA_VOCAB은 "1급"만 정의됨 — 2급 이상은 To-do [4])
    general = PERSONA_VOCAB.get(korean_grade, PERSONA_VOCAB["1급"])

    # ② 장소 한정 직함. location이 없거나 "역할" 키가 없으면 빈 리스트
    #    → 빈 리스트면 general만 반환하게 됨 (한강 외 장소는 현재 이 케이스)
    location_roles = _LOCATION_VOCAB.get(location, {}).get("역할", [])
    return general + location_roles


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_message(
    level: str = "Beginner",
    location: str = "한강",
    relationship_type: str | None = None,
) -> str:
    korean_grade = LEVEL_MAP.get(level, "1급")
    relationship_type = (
        relationship_type
        if relationship_type in _RELATIONSHIP_TYPES
        else random.choice(_RELATIONSHIP_TYPES)
    )
    funcs = DIALOGUE_FUNCTIONS.get(korean_grade, DIALOGUE_FUNCTIONS["1급"])
    # TODO: "3급"·"5급" 데이터 추가 후 폴백 제거 — DIALOGUE_FUNCTIONS 주석 참고.
    # DIALOGUE_FUNCTIONS[korean_grade] 목록을 " | " 구분으로 포맷팅해 {dialogue_functions}에 주입
    dialogue_functions = " | ".join(funcs)
    activities = _get_activities(location)
    if relationship_type == "낯선 사람":
        vocab_list = _get_persona_vocab(korean_grade, location)
        persona_vocab = (
            "인물 (낯선 사람 B 전용 — B의 role 선택 시 이 목록에서 고를 것): "
            + ", ".join(vocab_list)
            + "\n"
        )
    else:
        persona_vocab = ""
    loc_vocab = _LOCATION_VOCAB.get(location, {})
    facilities = loc_vocab.get("시설명", [])
    # "역할"은 _get_persona_vocab()을 통해 persona_vocab으로만 주입.
    # → 낯선 사람 아닌 관계에서는 역할 어휘가 노출되지 않음.
    # → 낯선 사람일 때도 location_vocab·persona_vocab 이중 주입 없음.
    location_vocab = (
        (
            "장소 시설명 (mission·scenario_description 작성 시 활용): "
            + ", ".join(facilities)
            + "\n"
        )
        if facilities
        else ""
    )
    general_vocab = _get_general_vocab(korean_grade)
    # _USER_PROMPT_TEMPLATE 안의 {level}, {location}, {relationship_type} 등
    # 모든 {} 자리에 .format()으로 한꺼번에 값을 주입해 완성된 유저 프롬프트를 반환한다.
    return _USER_PROMPT_TEMPLATE.format(
        level=korean_grade,
        location=location,
        relationship_type=relationship_type,
        dialogue_functions=dialogue_functions,
        activities=activities,
        persona_vocab=persona_vocab,
        location_vocab=location_vocab,
        general_vocab=general_vocab,
    )


# ================================================================
# 전체 로직 흐름
# ================================================================
#
# ┌─────────────────────────────────────────────────────────────┐
# │  build_user_message(location, level) 호출                   │
# └──────────────────────────┬──────────────────────────────────┘
#                            │
#     ┌──────────┬───────────┼───────────┬──────────────┐
#     ▼          ▼           ▼           ▼              ▼
# [관계 유형]  [활동]    [대화 기능]  [장소 어휘]   [일반 어휘]
# _RELATIONSHIP  _ACTIVITIES  DIALOGUE_   _LOCATION_    _get_general_
# _TYPES에서     [location]   FUNCTIONS   VOCAB         vocab(level)
# random.choice  [category]   [level]     [location]    vocabulary.json
# → relationship 카테고리당   " | " 구분  ["시설명"]    에서 급수·품사(동사, 형용사)
#   _type        2개 샘플링   포맷팅      만 전체 주입  필터 후 전체 주입
#                → activities → dialogue  → location    → general_vocab
#                              _functions   _vocab
#     │          │           │            │              │
#     └──────────┴───────────┼────────────┴──────────────┘
#                            │
#          ┌─────────────────┼────────────────────┐
#          ▼                 ▼                    ▼
#   [인물 어휘 결정]   _USER_PROMPT_TEMPLATE 에 변수 주입
#   relationship_type  {level} {location} {relationship_type}
#   == "낯선 사람"     {activities} {dialogue_functions}
#   → _get_persona_  {persona_vocab} {location_vocab} {general_vocab}
#     vocab(level,
#     location) 주입
#   else → ""
#                            │
#                            ▼
#                   [LLM 실행 순서 (step 0~6)]
#                   0. 입력 확인 — relationship_type·활동 풀·
#                      dialogue_function 풀 전체를 확정
#                   1. 활동 선택 (활동 풀에서)
#                      → 1개 선택
#                   2. 활동 → dialogue_function 매핑
#                      (dialogue_function 풀에서 선택)
#                   3. personas 설정 (role·age 제약 준수)
#                   4. mission 생성
#                      (같은 화제, A·B 각자 능동적 목표
#                       낯선 사람은 요청자-조력자 비대칭
#                       음식·물건은 구체적 이름 사용)
#                   5. scenario_description 생성
#                   6. JSON 출력
#
# ================================================================
# 현재 파일 상황 (as-is)
# ================================================================
#
# [코드가 처리]
# - 관계 유형: random.choice → {relationship_type} 주입
# - 학습자 수준: LEVEL_MAP으로 변환 → "한국어 표준 교육과정 {level}" 형태로 주입
# - 대화 기능 목록: DIALOGUE_FUNCTIONS[급수] flat list " | " 구분 포맷팅 → {dialogue_functions} 주입
# - 장소 활동 목록: _ACTIVITIES[location] 카테고리별 2개 샘플링 → {activities} 주입
# - 인물 어휘: _get_persona_vocab(level, location) — 일반 직업 + 장소 역할 합산
#              → "낯선 사람"일 때만 {persona_vocab} 주입
# - 장소 어휘: _LOCATION_VOCAB[location]["시설명"] 전체 → {location_vocab} 주입
#              ("역할"은 persona_vocab으로 분리, location_vocab에는 포함 안 됨)
# - 일반 어휘: vocabulary.json에서 급수·품사(동사·형용사) 필터 → {general_vocab} 주입

# [LLM이 처리]
# 0. 입력 확인 — relationship_type / 활동 풀 / dialogue_function 풀 전체 확정 (주어진 값 그대로)
# 1. 활동 풀에서 relationship_type과 자연스러운 활동 선택
# 2. 선택한 활동에 맞는 dialogue_function을 dialogue_function 풀에서 확정
# 3. personas 설정 (## 제약 ① 준수)
# 4. mission 생성 (## 제약 ③ 준수, 참고 어휘 활용)
# 5. scenario_description 생성 (## 제약 ④ 준수, mission 참고)
# 6. JSON 출력


# To-do
# ================================================================
# [PHASE 1] 데이터 구조화 및 외부화
# ================================================================
# 1.1 JSON 스키마 설계 및 파일 분리 (기존 하드코딩 탈출)
#     - assets/data/locations.json: 장소명, roles, activities 포함
        # {
        #   "한강": {
        #     "location_description": "서울의 큰 강, 자전거를 타거나 음식을 먹는 곳",
        #     "activities_categories": {
        #       "장소/정보 묻기": ["오리배 타는 곳 찾기", "화장실 위치", "따릉이 대여소"],
        #       "경험/취향 공유": ["한강 방문 횟수", "좋아하는 배달 음식", "자전거 타기 선호"],
        #       "제안/약속하기": ["라면 먹으러 가기", "다음주에 또 오기", "사진 찍어주기"],
        #       "자기소개/관계": ["처음 만난 사람과 인사", "선후배 간의 안부"]
        #     }
        #   }
        # }
#     - assets/data/personas.json: 급수별(1~6급) 직업/신분 리스트
#     - assets/data/dialogue_functions.json: 급수별 수행 가능한 대화 목표(부탁하기, 경험 묻기 등)
# 
# [주의사항] JSON 내 '대화 카테고리' 강제화 필수 (편향 방지)
#
# 1.2 장소 및 급수 데이터 확장
#     - '한강' 외 지하철, 편의점, 학교 등 신규 장소 3개 이상 추가
#     - 1급에 한정된 페르소나/대화 기능을 2~3급까지 큐레이션하여 추가
#
# ================================================================
# [PHASE 2] 시나리오 생성 파이프라인 개편
# ================================================================
# 2.1 카테고리 기반 샘플러(Sampler) 구현
#     - 생성 시 한 가지 카테고리에 쏠리지 않도록 '서로 다른 카테고리에서 2개 추출' 등의 룰 적용
#
# 2.2 자유 생성형 'Generator' 프롬프트 설계
#     - JSON에서 뽑은 {장소}, {활동}, {역할}을 주입하되, 어휘 제약 없이 '자연스러운' 시나리오 생성 유도
#
# 2.3 급수 맞춤형 'Refiner' 프롬프트 설계 (핵심)
#     - 생성된 시나리오를 입력받아 한국어 표준 교육과정 급수에 맞게 어휘/문법 교정
#     - [Rule 1] 장소 관련 고유명사/역할은 유지 (ex: 따릉이, 점원)
#     - [Rule 2] 서술어와 조사를 해당 급수 수준으로 하향 조정 (ex: 설명하다 -> 알려주다)
#     - [Rule 3] 미션 문장을 초급자가 즉각 발화 가능한 '행동형'으로 변경

# ================================================================
# [PHASE 3] 시스템 지능화 및 사용자 최적화
# ================================================================
# 3.1 사용자 학습 데이터 연동 (Personalization)
#     - 사용자의 이전 세션 평가 결과(취약한 문법/어휘)를 Refiner에 피드백으로 주입
#
# 3.2 시나리오 메타데이터 강화
#     - 각 시나리오에 '학습 포인트(핵심 어휘/문법)'를 자동으로 추출하여 JSON에 저장
#
# 3.3 저장 로직 개선
#     - results/scenario/ 디렉토리 자동 생성 및 급수별/장소별 파일 네이밍 규칙 적용
# ================================================================