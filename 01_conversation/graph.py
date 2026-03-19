"""Conversation graph builder."""

from langgraph.graph import END, START, StateGraph

from .nodes.generate_scenario import generate_scenario
from .state import ConversationState


def build_conversation_graph():
    """Create graph for scenario generation.

    역할 선택은 이 그래프 이후(터미널/API 단계)에서 받도록 분리한다.
    """

    graph = StateGraph(ConversationState)

    graph.add_node("generate_scenario", generate_scenario)
    graph.add_edge(START, "generate_scenario")
    graph.add_edge("generate_scenario", END)

    return graph.compile()
