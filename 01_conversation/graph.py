"""대화 그래프 빌더."""

from langgraph.graph import END, START, StateGraph

from .nodes.generate_location_context import generate_location_context
from .nodes.generate_scenario import generate_scenario
from .state import ConversationState


def build_conversation_graph():
    """시나리오 생성을 위한 그래프를 생성한다.

    역할 선택은 이 그래프 이후(터미널/API 단계)에서 받도록 분리한다.
    """

    graph = StateGraph(ConversationState)

    graph.add_node("generate_location_context", generate_location_context)
    graph.add_node("generate_scenario", generate_scenario)

    graph.add_edge(START, "generate_location_context")
    graph.add_edge("generate_location_context", "generate_scenario")
    graph.add_edge("generate_scenario", END)

    return graph.compile()
