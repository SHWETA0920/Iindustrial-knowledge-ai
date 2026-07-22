"""
MODULE 10: LIGHTWEIGHT AGENTIC WORKFLOW / SUPERVISOR ROUTER
-----------------------------------------------------------
A pragmatic hackathon-friendly supervisor that routes user requests to the
best available module without requiring full LangGraph orchestration.
"""

import re

from knowledge_graph import _load_graph, generate_lessons_learned
from query import query_answer
from rca_agent import run_rca

EQUIPMENT_PATTERNS = [
    r"\b(?:Pump|Compressor|Boiler|Valve|Motor|Tank|Fan|Blower)\s*[A-Z]?-?\d{2,4}\b",
    r"\b[A-Z]{1,3}-\d{2,4}\b",
]


def extract_equipment_tag(text):
    for pattern in EQUIPMENT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def format_lessons_answer(lessons):
    if not lessons:
        return "No recurring lessons-learned patterns are available yet. Build the knowledge graph after ingesting incident and maintenance data."

    lines = ["LESSONS LEARNED SUMMARY:"]
    for item in lessons[:5]:
        root_causes = ", ".join(item.get("root_causes", [])) or "not explicitly captured"
        equipment = ", ".join(item.get("equipment_involved", [])) or "unlinked equipment"
        lines.extend([
            f"- Failure pattern: {item['failure']}",
            f"  Occurrences: {item['occurrences']}",
            f"  Equipment involved: {equipment}",
            f"  Suspected root causes: {root_causes}",
            f"  Recommendation: {item['recommendation']}",
        ])
    return "\n".join(lines)


def handle_user_request(question):
    q = question.lower()
    equipment_tag = extract_equipment_tag(question)

    if equipment_tag and any(k in q for k in ["root cause", "rca", "failure analysis", "why did", "why does"]):
        result = run_rca(equipment_tag)
        if result:
            return {
                "mode": "rca",
                "question": question,
                "answer": result["rca_report"],
                "sources": result.get("rag_sources", []),
                "details": result,
            }

    if any(k in q for k in ["lesson learned", "lessons learned", "recurring", "repeat failure", "pattern across"]):
        G = _load_graph()
        lessons = generate_lessons_learned(G) if G is not None else []
        return {
            "mode": "lessons",
            "question": question,
            "answer": format_lessons_answer(lessons),
            "sources": [],
            "details": {"lessons": lessons[:5]},
        }

    result = query_answer(question)
    result["mode"] = "rag"
    return result
