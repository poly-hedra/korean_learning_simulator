"""대화 노드: 장소 컨텍스트를 생성한다."""

from ..prompts.location_context import build_location_context_prompt
from services.llm_service import llm_service
from ..state import ConversationState


def generate_location_context(state: ConversationState) -> ConversationState:
    """장소에서 경험할 수 있는 활동·명소·트렌드를 LLM으로 자유 생성한다.
    하드코딩 없이 어떤 장소든 풍부한 컨텍스트를 만들어 이후 generate_scenario 노드의 시나리오 품질을 높인다.
    """
    location = state.get("location", "한강")

    context = llm_service.generate_text(
        system_prompt="너는 한국 문화와 장소에 정통한 현지인이다.",
        user_prompt=build_location_context_prompt(location=location),
        temperature=0.7,
    )

    state["location_context"] = context.strip()
    return state
