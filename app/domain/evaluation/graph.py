"""평가 그래프 빌더."""

from langgraph.graph import END, START, StateGraph

from .nodes.calculate_score import calculate_score
from .nodes.evaluate_context import evaluate_context
from .nodes.evaluate_spelling import evaluate_spelling
from .nodes.evaluate_vocab import evaluate_vocab
from .state import EvaluationState


def build_evaluation_graph():
    """어휘/맥락/맞춤법 평가 후 총점을 계산하는 그래프를 생성한다."""

    graph = StateGraph(EvaluationState)
    graph.add_node("evaluate_vocab", evaluate_vocab)
    graph.add_node("evaluate_context", evaluate_context)
    graph.add_node("evaluate_spelling", evaluate_spelling)
    graph.add_node("calculate_score", calculate_score)

    graph.add_edge(START, "evaluate_vocab")
    graph.add_edge(START, "evaluate_context")
    graph.add_edge(START, "evaluate_spelling")
    graph.add_edge(
        ["evaluate_vocab", "evaluate_context", "evaluate_spelling"],
        "calculate_score",
    )
    graph.add_edge("calculate_score", END)

    return graph.compile()
