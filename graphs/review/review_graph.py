"""Review graph builder."""

from langgraph.graph import END, START, StateGraph

from nodes.review.generate_chosung_quiz import generate_chosung_quiz
from nodes.review.generate_flashcards import generate_flashcards
from nodes.review.select_week_logs import select_week_logs
from states.review_state import ReviewState


def build_review_graph():
    """Create graph for weekly weak-session review workflow."""

    graph = StateGraph(ReviewState)
    graph.add_node("select_week_logs", select_week_logs)
    graph.add_node("generate_chosung_quiz", generate_chosung_quiz)
    graph.add_node("generate_flashcards", generate_flashcards)

    graph.add_edge(START, "select_week_logs")
    graph.add_edge("select_week_logs", "generate_chosung_quiz")
    graph.add_edge("generate_chosung_quiz", "generate_flashcards")
    graph.add_edge("generate_flashcards", END)

    return graph.compile()
