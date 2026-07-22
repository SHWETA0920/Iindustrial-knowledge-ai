"""
HACKATHON DEMO BACKEND
----------------------
Unified backend for the Industrial Knowledge Intelligence demo.

Exposes:
  - dashboard UI
  - supervisor-routed chat copilot
  - RCA agent
  - compliance checker
  - recurring-failure alerts
  - lessons learned summaries
  - document explorer inventory
  - lightweight knowledge-graph visualization payload
  - dashboard statistics
"""

import os
import json
import sys
from collections import Counter

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from compliance_agent import check_compliance
from knowledge_graph import (
    _load_graph,
    generate_lessons_learned,
    get_document_inventory,
    graph_to_visual_payload,
    query_recurring_failures,
)
from rca_agent import run_rca
from supervisor_agent import handle_user_request

app = Flask(__name__)
CORS(app)

METADATA_PATH = "outputs_store/metadata.json"
ENTITIES_PATH = "outputs_store/entities.json"


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    question = request.json.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    result = handle_user_request(question)
    return jsonify(result)


@app.route("/api/rca", methods=["POST"])
def api_rca():
    equipment_tag = request.json.get("equipment_tag", "").strip()
    if not equipment_tag:
        return jsonify({"error": "equipment_tag is required"}), 400
    result = run_rca(equipment_tag)
    if result is None:
        return jsonify({"error": "Knowledge graph not built yet. Run src/knowledge_graph.py first."}), 400
    return jsonify(result)


@app.route("/api/compliance", methods=["POST"])
def api_compliance():
    procedure_text = request.json.get("procedure_text", "").strip()
    topic = request.json.get("topic", "").strip()
    if not procedure_text or not topic:
        return jsonify({"error": "procedure_text and topic are required"}), 400
    result = check_compliance(procedure_text, topic)
    return jsonify(result)


@app.route("/api/alerts")
def api_alerts():
    G = _load_graph()
    if G is None:
        return jsonify({"alerts": []})

    recurring = query_recurring_failures(G, min_occurrences=2)
    alerts = []
    for failure_label, nodes in recurring.items():
        equipment_involved = set()
        evidence_docs = set()
        for failure_node in nodes:
            for pred in G.predecessors(failure_node):
                if G.nodes[pred].get("node_type") == "Equipment":
                    equipment_involved.add(pred)
            for succ in G.successors(failure_node):
                if G.nodes[succ].get("node_type") == "Document":
                    evidence_docs.add(succ)

        severity = "HIGH" if len(nodes) >= 3 else "MEDIUM"
        alerts.append({
            "severity": severity,
            "failure": failure_label,
            "occurrences": len(nodes),
            "equipment_involved": sorted(equipment_involved),
            "evidence_docs": sorted(evidence_docs),
            "recommendation": (
                f"Investigate recurring '{failure_label}' across {len(equipment_involved) or 1} equipment unit(s) "
                f"and standardize the corrective action into preventive maintenance."
            ),
        })

    alerts.sort(key=lambda a: (-a["occurrences"], a["failure"]))
    return jsonify({"alerts": alerts})


@app.route("/api/lessons")
def api_lessons():
    G = _load_graph()
    lessons = generate_lessons_learned(G) if G is not None else []
    return jsonify({"lessons": lessons})


@app.route("/api/documents")
def api_documents():
    return jsonify({"documents": get_document_inventory()})


@app.route("/api/graph")
def api_graph():
    G = _load_graph()
    return jsonify(graph_to_visual_payload(G))


@app.route("/api/stats")
def api_stats():
    stats = {
        "documents_processed": 0,
        "equipment_identified": 0,
        "failure_patterns": 0,
        "regulatory_docs": 0,
        "chunk_count": 0,
        "entities_extracted": 0,
        "file_types": {},
        "alerts_count": 0,
    }

    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
        metadata = data.get("metadata", [])
        sources = {m["source"] for m in metadata if m.get("source")}
        stats["documents_processed"] = len(sources)
        stats["chunk_count"] = len(data.get("chunks", []))
        stats["regulatory_docs"] = len({
            m["source"] for m in metadata if m.get("category") == "Regulatory"
        })
        stats["file_types"] = dict(Counter(m.get("file_type", "unknown") for m in metadata))

    if os.path.exists(ENTITIES_PATH):
        with open(ENTITIES_PATH, "r") as f:
            entities = json.load(f)
        total_entities = 0
        for item in entities:
            for category in [
                "equipment",
                "failures",
                "root_causes",
                "operational_parameters",
                "regulatory_references",
                "dates",
            ]:
                total_entities += len(item.get(category, []))
        stats["entities_extracted"] = total_entities

    G = _load_graph()
    if G is not None:
        equipment_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "Equipment"]
        stats["equipment_identified"] = len(equipment_nodes)
        stats["failure_patterns"] = len(query_recurring_failures(G, min_occurrences=2))
        stats["alerts_count"] = stats["failure_patterns"]

    return jsonify(stats)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
