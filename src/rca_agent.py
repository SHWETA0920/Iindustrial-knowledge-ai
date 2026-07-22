"""
MODULE 6: MAINTENANCE INTELLIGENCE / RCA AGENT
MODULE 9: LESSONS LEARNED INTELLIGENCE ENGINE
-------------------------------------------------
Given an equipment tag, this agent:
1. Pulls that equipment's failure history from the knowledge graph
2. Checks whether the same failure/cause pattern recurs (Lessons Learned)
3. Retrieves any relevant maintenance/OEM manual text via RAG
4. Produces a structured RCA report + recommendation
"""

import os
import sys
import json
from groq import Groq
from dotenv import load_dotenv

from knowledge_graph import _load_graph, query_equipment_history, query_recurring_failures
from query import query_answer

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

RCA_PROMPT = """You are a Root Cause Analysis (RCA) agent for industrial equipment.

Equipment: {equipment_tag}

Failure history from the knowledge graph:
{failure_history_json}

Recurring failure patterns detected across the plant (same failure seen elsewhere too):
{recurring_patterns_json}

Relevant maintenance/manual context retrieved from documents:
{rag_context}

Produce a structured RCA report in this exact format:

PROBLEM:
(one line summarizing the most significant or most recent failure)

IMMEDIATE CAUSE:
(the direct mechanical/operational cause, if determinable from the data — say \"not determinable from available data\" if unclear)

ROOT CAUSE:
(the underlying systemic cause — maintenance schedule, material, procedure, etc.)

PATTERN ASSESSMENT:
(state clearly whether this is a recurring pattern across the plant or an isolated incident, based on the recurring patterns data given)

CORRECTIVE ACTION:
(a specific, actionable fix)

PREVENTIVE ACTION:
(a specific, actionable step to prevent recurrence)

CONFIDENCE: high | medium | low
(base this on how much of the above was grounded in actual retrieved data vs. inferred)

Do not invent failure details not present in the data provided above.
"""


def run_rca(equipment_tag):
    G = _load_graph()
    if G is None:
        print("No knowledge graph found. Run 'python src/knowledge_graph.py' first.")
        return None

    failure_history = query_equipment_history(G, equipment_tag)
    recurring = query_recurring_failures(G, min_occurrences=2)

    relevant_recurring = {}
    if failure_history.get("found"):
        history_labels = {f["failure"] for f in failure_history.get("failure_history", []) if f.get("failure")}
        relevant_recurring = {label: nodes for label, nodes in recurring.items() if label in history_labels}

    rag_result = query_answer(f"maintenance history and manual guidance for {equipment_tag}")
    rag_context = rag_result["answer"]

    prompt = RCA_PROMPT.format(
        equipment_tag=equipment_tag,
        failure_history_json=json.dumps(failure_history, indent=2),
        recurring_patterns_json=json.dumps({k: len(v) for k, v in relevant_recurring.items()}, indent=2),
        rag_context=rag_context,
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return {
        "equipment": equipment_tag,
        "failure_history": failure_history,
        "recurring_patterns": {k: len(v) for k, v in relevant_recurring.items()},
        "rag_sources": rag_result.get("sources", []),
        "rca_report": response.choices[0].message.content,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python src/rca_agent.py "Pump P101"')
        sys.exit(1)

    result = run_rca(sys.argv[1])
    if result:
        print(f"\n--- RCA Report: {result['equipment']} ---\n")
        print(result["rca_report"])
