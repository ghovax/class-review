"""LangGraph Studio entrypoint for Teacher's compiled graph."""

from teacher.graph import define_graph

graph = define_graph().compile()

__all__ = ["graph"]
