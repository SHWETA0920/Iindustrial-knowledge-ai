"""
MODULE 8: COMPLIANCE INTELLIGENCE AGENT
-------------------------------------------
Compares a procedure document against regulatory text retrieved from the
corpus (OISD / Factory Act / PESO chunks) and:
1. Detects whether the procedure is compliant
2. If not, auto-drafts a corrected version of the specific non-compliant
   section, plus a one-line change summary for an audit log

Usage:
    python src/compliance_agent.py "path/to/procedure.txt" "hot work permit frequency"
"""

import os
import sys
import json
from groq import Groq
from dotenv import load_dotenv

from query import query_answer

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GAP_PROMPT = """Compare the procedure below against the regulatory context retrieved
from the document corpus. Identify any deviation.

Regulatory context (retrieved from corpus):
\"\"\"
{regulation_text}
\"\"\"

Current procedure:
\"\"\"
{procedure_text}
\"\"\"

Return ONLY valid JSON:
{{
  "compliant": boolean,
  "gap_description": "string, empty if compliant",
  "severity": "critical" | "moderate" | "minor" | "none",
  "clause_reference": "string, best guess at which regulation/clause applies"
}}
"""

DRAFT_PROMPT = """The following procedure has a compliance gap against a regulatory requirement.
Draft a corrected version of ONLY the non-compliant section — keep everything else unchanged
in spirit, just fix the specific gap.

Regulatory requirement (from corpus): {regulation_text}
Gap identified: {gap_description}
Original procedure:
\"\"\"
{procedure_text}
\"\"\"

Return ONLY valid JSON:
{{
  "corrected_section": "rewritten text, ready to paste into the procedure doc",
  "change_summary": "one sentence describing what changed, for the audit log"
}}
"""


def _call_llm_json(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    return json.loads(text)


def check_compliance(procedure_text, regulation_topic):
    """
    regulation_topic: a short phrase describing what regulatory area to check
    against, e.g. "hot work permit frequency" — this is used to retrieve the
    most relevant regulatory chunks from your ingested corpus via RAG.
    """
    rag_result = query_answer(f"regulatory requirement for {regulation_topic}")
    regulation_text = rag_result["answer"]

    gap_result = _call_llm_json(GAP_PROMPT.format(
        regulation_text=regulation_text,
        procedure_text=procedure_text
    ))

    result = {
        "regulation_topic": regulation_topic,
        "regulation_sources": rag_result["sources"],
        **gap_result
    }

    if not gap_result.get("compliant", True):
        draft = _call_llm_json(DRAFT_PROMPT.format(
            regulation_text=regulation_text,
            gap_description=gap_result.get("gap_description", ""),
            procedure_text=procedure_text
        ))
        result["corrective_draft"] = draft

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python src/compliance_agent.py "path/to/procedure.txt" "regulation topic"')
        sys.exit(1)

    procedure_path = sys.argv[1]
    topic = sys.argv[2]

    with open(procedure_path, "r") as f:
        procedure_text = f.read()

    result = check_compliance(procedure_text, topic)
    print(json.dumps(result, indent=2))
