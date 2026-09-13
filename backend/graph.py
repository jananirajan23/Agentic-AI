r"""
LangGraph orchestration for the Reviewer-Lens review pipeline.

    parse -> literature   \
          \-> architecture -> alignment -> aggregate -> END
    literature ------------------------------^

`literature` and `architecture` run in parallel after `parse`. `alignment`
runs after `architecture` (it needs the diagram components). `aggregate`
waits for both `literature` and `alignment` to finish.

Every node function returns only the keys it adds/changes — never the
full state — so the parallel literature/architecture branches don't both
try to write the same shared keys (e.g. pdf_path) and trip LangGraph's
InvalidUpdateError on the concurrent write.
"""

import functools

from langgraph.graph import StateGraph, END

from state import ReviewState
from agents import (
    document_parser,
    literature_survey_agent,
    architecture_structure_agent,
    alignment_agent,
    report_aggregator,
)


def build_graph(output_path: str):
    graph = StateGraph(ReviewState)

    graph.add_node("parse", document_parser.run)
    graph.add_node("literature", literature_survey_agent.run)
    graph.add_node("architecture", architecture_structure_agent.run)
    graph.add_node("alignment", alignment_agent.run)
    graph.add_node("aggregate", functools.partial(report_aggregator.run, output_path=output_path))

    graph.set_entry_point("parse")

    graph.add_edge("parse", "literature")
    graph.add_edge("parse", "architecture")
    graph.add_edge("architecture", "alignment")
    # A join, not two independent edges: passing a list of source nodes is
    # LangGraph's documented fan-in syntax, meaning "wait until every node
    # in this list has completed, then run once". Two separate
    # add_edge("literature", "aggregate") / add_edge("alignment",
    # "aggregate") calls do NOT join — each is an independent trigger, so
    # `aggregate` fired a first time as soon as `literature` finished
    # (before `architecture`/`alignment` were even done) and a second time
    # after `alignment` finished, silently double-running the Groq
    # suggestion-generation call and briefly exposing an incomplete
    # composite score to anything polling job status mid-pipeline.
    graph.add_edge(["literature", "alignment"], "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()
