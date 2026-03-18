"""Evaluation graph builder."""

from langgraph.graph import END, START, StateGraph

from nodes.evaluation.calculate_score import calculate_score
from nodes.evaluation.evaluate_context import evaluate_context
from nodes.evaluation.evaluate_spelling import evaluate_spelling
from nodes.evaluation.evaluate_vocab import evaluate_vocab
from states.evaluation_state import EvaluationState


def build_evaluation_graph():
    """Create graph for vocab/context/spelling -> total score."""

    graph = StateGraph(EvaluationState)
    graph.add_node("evaluate_vocab", evaluate_vocab)
    graph.add_node("evaluate_context", evaluate_context)
    graph.add_node("evaluate_spelling", evaluate_spelling)
    graph.add_node("calculate_score", calculate_score)

    graph.add_edge(START, "evaluate_vocab")
    graph.add_edge("evaluate_vocab", "evaluate_context")
    graph.add_edge("evaluate_context", "evaluate_spelling")
    graph.add_edge("evaluate_spelling", "calculate_score")
    graph.add_edge("calculate_score", END)

    return graph.compile()
