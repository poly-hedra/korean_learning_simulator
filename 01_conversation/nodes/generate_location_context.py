"""대화 노드: 장소 컨텍스트를 생성한다."""

import time

from ..prompts.location_context import build_location_context_prompt
from services.llm_service import llm_service
from ..state import ConversationState

MAX_CONTEXT_RETRY = 3

# LLM 응답 품질 판별 기준
_HALLUCINATION_KEYWORDS = ['최종 확정', '최종 답변', '재작성', '수정', '(※', '단,', '보충:', '추가 상황']


def _is_valid_context(ctx: str, duration: float) -> bool:
    """생성된 컨텍스트가 유효한지 검사한다.

    - duration > 5초: 루프·재시도 의심
    - 메타텍스트 포함: LLM 자기 수정 의심 (할루시네이션)
    """
    if duration > 5:
        return False
    for kw in _HALLUCINATION_KEYWORDS:
        if kw in ctx:
            return False
    return True


def generate_location_context(state: ConversationState) -> ConversationState:
    """장소에서 경험할 수 있는 활동·명소·트렌드를 LLM으로 자유 생성한다.
    하드코딩 없이 어떤 장소든 풍부한 컨텍스트를 만들어 이후 generate_scenario 노드의 시나리오 품질을 높인다.
    유효하지 않은 응답은 최대 MAX_CONTEXT_RETRY회 재시도하며, 초과 시 컨텍스트 없이 진행한다.
    """
    location = state.get("location", "한강")

    for attempt in range(MAX_CONTEXT_RETRY):
        start = time.time()
        context = llm_service.generate_text(
            system_prompt="너는 한국 문화와 장소에 정통한 현지인이다.",
            user_prompt=build_location_context_prompt(location=location),
            temperature=0.7,
        )
        duration = time.time() - start

        if _is_valid_context(context, duration):
            state["location_context"] = context.strip()
            return state

        print(f"  location_context 재시도 {attempt + 1}/{MAX_CONTEXT_RETRY}...")

    # 재시도 초과 → 컨텍스트 없이 기존 방식으로 fallback
    state["location_context"] = None
    return state
