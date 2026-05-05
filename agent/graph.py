from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import planner, retriever, calculator, responder, evaluator


def _route_after_planner(state: AgentState) -> str:
    return state["route"]


def _route_after_evaluator(state: AgentState) -> str:
    if state["is_sufficient"] or state["retry_count"] >= 2:
        return "end"
    return "retry"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner)
    graph.add_node("retriever", retriever)
    graph.add_node("calculator", calculator)
    graph.add_node("responder", responder)
    graph.add_node("evaluator", evaluator)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"retrieval": "retriever", "calculator": "calculator"},
    )

    graph.add_edge("retriever", "responder")
    graph.add_edge("calculator", "responder")
    graph.add_edge("responder", "evaluator")

    graph.add_conditional_edges(
        "evaluator",
        _route_after_evaluator,
        {"retry": "retriever", "end": END},
    )

    return graph.compile()


agent = build_graph()
