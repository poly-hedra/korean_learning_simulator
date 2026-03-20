"""복습 그래프 빌더."""

from langgraph.graph import END, START, StateGraph

from .nodes.generate_chosung_quiz import generate_chosung_quiz
from .nodes.generate_flashcards import generate_flashcards
from .nodes.select_weak_logs import select_weak_logs
from .state import ReviewState


def build_review_graph():
    """주간 취약 세션 복습 워크플로용 그래프를 생성한다."""

    graph = StateGraph(ReviewState)
    graph.add_node("select_weak_logs", select_weak_logs)
    graph.add_node("generate_chosung_quiz", generate_chosung_quiz)
    graph.add_node("generate_flashcards", generate_flashcards)

    graph.add_edge(START, "select_weak_logs")
    graph.add_edge("select_weak_logs", "generate_chosung_quiz")
    graph.add_edge("select_weak_logs", "generate_flashcards")
    graph.add_edge(["generate_chosung_quiz", "generate_flashcards"], END)

    return graph.compile()
