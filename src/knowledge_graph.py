"""
MODULE 4: KNOWLEDGE GRAPH
----------------------------
Builds a graph from outputs_store/entities.json linking:
    Equipment --experienced--> Failure --caused_by--> Root Cause
    Equipment --mentioned_in--> Document

Uses NetworkX instead of Neo4j for hackathon speed and portability.
The graph model is still node/edge based, so it can be upgraded to Neo4j
later without changing the rest of the product experience.
"""

import os
import sys
import json
from collections import defaultdict

import networkx as nx

ENTITIES_PATH = "outputs_store/entities.json"
METADATA_PATH = "outputs_store/metadata.json"
GRAPH_PATH = "outputs_store/knowledge_graph.gpickle"
GRAPH_HTML_PATH = "outputs_store/knowledge_graph.html"

NODE_TYPE_ORDER = ["Equipment", "Failure", "RootCause", "Document", "Regulation"]
NODE_TYPE_COLORS = {
    "Equipment": "#028090",
    "Failure": "#d64545",
    "RootCause": "#f39c12",
    "Document": "#6c5ce7",
    "Regulation": "#16a085",
}


def build_graph(export_html=False):
    if not os.path.exists(ENTITIES_PATH):
        print("No entities found. Run 'python src/extract_entities.py' first.")
        return None

    with open(ENTITIES_PATH, "r") as f:
        all_entities = json.load(f)

    G = nx.DiGraph()

    for chunk_entities in all_entities:
        source_doc = chunk_entities.get("_source")
        chunk_id = chunk_entities.get("_chunk_id")
        page_no = chunk_entities.get("_page")
        # date_hint = chunk_entities.get("dates", [None])[0] if chunk_entities.get("dates") else None
        date_hint = chunk_entities.get("dates", [])

        if not source_doc:
            continue

        G.add_node(source_doc, node_type="Document", label=source_doc)

        equipment_tags_in_chunk = []
        for eq in chunk_entities.get("equipment", []):
            if not isinstance(eq, dict) or not eq.get("tag"):
                continue
            tag = eq["tag"]
            equipment_tags_in_chunk.append(tag)
            G.add_node(
                tag,
                node_type="Equipment",
                label=tag,
                equipment_type=eq.get("type", "unknown"),
            )
            G.add_edge(tag, source_doc, relation="mentioned_in", chunk_id=chunk_id, page=page_no)

        for fail in chunk_entities.get("failures", []):
            if not isinstance(fail, dict) or not fail.get("description"):
                continue
            failure_label = fail["description"]
            failure_node = f"FAILURE::{failure_label}::{source_doc}::{page_no}::{chunk_id}"
            G.add_node(
                failure_node,
                node_type="Failure",
                label=failure_label,
                date=date_hint,
                source=source_doc,
                page=page_no,
            )

            linked_eq = fail.get("equipment_tag")
            if linked_eq:
                G.add_node(linked_eq, node_type="Equipment", label=linked_eq)
                G.add_edge(linked_eq, failure_node, relation="experienced", date=date_hint)
            else:
                for tag in equipment_tags_in_chunk:
                    G.add_edge(tag, failure_node, relation="experienced_possible", date=date_hint)

            G.add_edge(failure_node, source_doc, relation="documented_in", chunk_id=chunk_id, page=page_no)

        for cause in chunk_entities.get("root_causes", []):
            if not isinstance(cause, dict) or not cause.get("description"):
                continue
            cause_label = cause["description"]
            cause_node = f"CAUSE::{cause_label}"
            G.add_node(cause_node, node_type="RootCause", label=cause_label)

            linked_failure = cause.get("linked_failure")
            if linked_failure:
                for node, data in G.nodes(data=True):
                    if data.get("node_type") == "Failure" and data.get("label") == linked_failure:
                        G.add_edge(node, cause_node, relation="caused_by")
            else:
                for node, data in G.nodes(data=True):
                    if data.get("node_type") == "Failure" and data.get("source") == source_doc and data.get("page") == page_no:
                        G.add_edge(node, cause_node, relation="caused_by_possible")

        for reg in chunk_entities.get("regulatory_references", []):
            if not isinstance(reg, dict) or not reg.get("code"):
                continue
            reg_node = f"REG::{reg['code']}::{reg.get('clause') or 'general'}"
            G.add_node(
                reg_node,
                node_type="Regulation",
                label=reg["code"],
                clause=reg.get("clause"),
            )
            G.add_edge(source_doc, reg_node, relation="references")

    os.makedirs("outputs_store", exist_ok=True)
    nx.write_gpickle(G, GRAPH_PATH) if hasattr(nx, "write_gpickle") else _save_pickle(G)

    if export_html:
        export_graph_html(G)

    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    _print_node_type_counts(G)
    return G


def _save_pickle(G):
    import pickle
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)


def _load_graph():
    if not os.path.exists(GRAPH_PATH):
        return None
    if hasattr(nx, "read_gpickle"):
        return nx.read_gpickle(GRAPH_PATH)
    import pickle
    with open(GRAPH_PATH, "rb") as f:
        return pickle.load(f)


def _print_node_type_counts(G):
    counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("node_type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    print("Nodes by type:")
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")


def export_graph_html(G=None):
    if G is None:
        G = _load_graph()
    if G is None:
        return None

    try:
        from pyvis.network import Network
    except Exception:
        return None

    net = Network(height="750px", width="100%", directed=True, bgcolor="#ffffff", font_color="#111111")
    net.barnes_hut()

    for node, data in G.nodes(data=True):
        label = data.get("label", node)
        node_type = data.get("node_type", "unknown")
        net.add_node(
            node,
            label=label[:48],
            title=f"{node_type}: {label}",
            color=NODE_TYPE_COLORS.get(node_type, "#95a5a6"),
            shape="dot",
            size=18 if node_type == "Equipment" else 13,
        )

    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, label=data.get("relation", ""), arrows="to")

    net.save_graph(GRAPH_HTML_PATH)
    return GRAPH_HTML_PATH


def query_equipment_history(G, equipment_tag):
    if equipment_tag not in G:
        return {"equipment": equipment_tag, "found": False}

    failures = []
    for _, target, data in G.out_edges(equipment_tag, data=True):
        if data.get("relation") not in ("experienced", "experienced_possible"):
            continue

        cause_desc = []
        evidence_docs = []
        failure_meta = G.nodes[target]

        for _, cause_node, cause_data in G.out_edges(target, data=True):
            if cause_data.get("relation") in ("caused_by", "caused_by_possible"):
                cause_desc.append(G.nodes[cause_node].get("label"))
            if cause_data.get("relation") == "documented_in":
                evidence_docs.append(cause_node)

        for _, doc_node, doc_edge in G.out_edges(target, data=True):
            if doc_edge.get("relation") == "documented_in":
                evidence_docs.append(doc_node)

        failures.append({
            "failure": failure_meta.get("label"),
            "date": failure_meta.get("date"),
            "source": failure_meta.get("source"),
            "page": failure_meta.get("page"),
            "root_cause": sorted(set(cause_desc)) if cause_desc else [],
            "evidence_docs": sorted(set(evidence_docs)),
            "inferred_link": data.get("relation") == "experienced_possible",
        })

    return {"equipment": equipment_tag, "found": True, "failure_history": failures}


def query_equipment_by_root_cause(G, root_cause_keyword):
    matches = []
    keyword = root_cause_keyword.lower()

    for node, data in G.nodes(data=True):
        if data.get("node_type") == "RootCause" and keyword in data.get("label", "").lower():
            for failure_node in G.predecessors(node):
                for equipment_node in G.predecessors(failure_node):
                    if G.nodes[equipment_node].get("node_type") == "Equipment":
                        matches.append({
                            "equipment": equipment_node,
                            "failure": G.nodes[failure_node].get("label"),
                            "root_cause": data.get("label"),
                        })

    unique = []
    seen = set()
    for item in matches:
        key = (item["equipment"], item["failure"], item["root_cause"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


# def query_recurring_failures(G, min_occurrences=2):
#     failure_labels = {}
#     for node, data in G.nodes(data=True):
#         if data.get("node_type") == "Failure":
#             label = data.get("label")
#             failure_labels.setdefault(label, []).append(node)
#     return {label: nodes for label, nodes in failure_labels.items() if len(nodes) >= min_occurrences}
# def query_recurring_failures(G, min_occurrences=2):
#     """
#     Detect recurring failures.

#     Supports:
#     - Multiple failure nodes
#     - Multiple dates stored inside maintenance records

#     Existing RCA and graph functions remain unchanged.
#     """

#     failure_labels = {}

#     for node, data in G.nodes(data=True):

#         if data.get("node_type") != "Failure":
#             continue

#         label = data.get("label")

#         if label not in failure_labels:
#             failure_labels[label] = {
#                 "nodes": [],
#                 "dates": set()
#             }

#         failure_labels[label]["nodes"].append(node)

#         if data.get("date"):
#             failure_labels[label]["dates"].add(data["date"])

#     recurring = {}

#     for label, info in failure_labels.items():

#         occurrences = max(
#             len(info["nodes"]),
#             len(info["dates"])
#         )

#         if occurrences >= min_occurrences:
#             recurring[label] = info["nodes"]

#     return recurring

# def query_recurring_failures(G, min_occurrences=2):
#     """
#     Detect recurring failures using:
#     1. Multiple failure nodes
#     2. Multiple dates from same maintenance record
#     """

#     failure_labels = {}

#     for node, data in G.nodes(data=True):

#         if data.get("node_type") != "Failure":
#             continue

#         label = data.get("label")

#         if label not in failure_labels:
#             failure_labels[label] = {
#                 "nodes": [],
#                 "dates": set()
#             }

#         failure_labels[label]["nodes"].append(node)

#         date_value = data.get("date")

#         if date_value:
#             failure_labels[label]["dates"].add(date_value)


#     recurring = {}

#     for label, info in failure_labels.items():

#         # count multiple maintenance cycles
#         occurrence_count = len(info["dates"])

#         # fallback
#         if occurrence_count == 0:
#             occurrence_count = len(info["nodes"])


#         if occurrence_count >= min_occurrences:
#             recurring[label] = info["nodes"]


#     return recurring

def query_recurring_failures(G, min_occurrences=2):
    """
    Detect recurring failures using multiple maintenance dates.
    """

    failure_labels = {}

    for node, data in G.nodes(data=True):

        if data.get("node_type") != "Failure":
            continue

        label = data.get("label")

        if label not in failure_labels:
            failure_labels[label] = {
                "nodes": [],
                "dates": set()
            }

        failure_labels[label]["nodes"].append(node)

        date_value = data.get("date")

        # Handle list of dates
        if isinstance(date_value, list):
            for d in date_value:
                if d:
                    failure_labels[label]["dates"].add(d)

        # Handle single date
        elif date_value:
            failure_labels[label]["dates"].add(date_value)


    recurring = {}

    for label, info in failure_labels.items():

        occurrence_count = max(
            len(info["nodes"]),
            len(info["dates"])
        )

        if occurrence_count >= min_occurrences:
            recurring[label] = info["nodes"]

    return recurring

def get_document_inventory(metadata_path=METADATA_PATH):
    if not os.path.exists(metadata_path):
        return []

    with open(metadata_path, "r") as f:
        data = json.load(f)

    inventory = {}
    for meta in data.get("metadata", []):
        source = meta.get("source")
        if not source:
            continue
        inventory.setdefault(source, {
            "source": source,
            "file_type": meta.get("file_type", "unknown"),
            "categories": set(),
            "pages": set(),
            "chunk_count": 0,
        })
        inventory[source]["categories"].add(meta.get("category", "General"))
        inventory[source]["pages"].add(meta.get("page"))
        inventory[source]["chunk_count"] += 1

    result = []
    for item in inventory.values():
        result.append({
            "source": item["source"],
            "file_type": item["file_type"],
            "categories": sorted(c for c in item["categories"] if c),
            "page_count": len([p for p in item["pages"] if p is not None]),
            "chunk_count": item["chunk_count"],
        })

    result.sort(key=lambda x: (x["categories"][0] if x["categories"] else "", x["source"]))
    return result


def generate_lessons_learned(G, min_occurrences=2):
    if G is None:
        return []

    recurring = query_recurring_failures(G, min_occurrences=min_occurrences)
    lessons = []

    for failure_label, nodes in recurring.items():
        equipment_involved = set()
        root_causes = set()
        evidence_docs = set()

        for failure_node in nodes:
            for pred in G.predecessors(failure_node):
                if G.nodes[pred].get("node_type") == "Equipment":
                    equipment_involved.add(pred)
            for succ in G.successors(failure_node):
                succ_data = G.nodes[succ]
                if succ_data.get("node_type") == "RootCause":
                    root_causes.add(succ_data.get("label"))
                if succ_data.get("node_type") == "Document":
                    evidence_docs.add(succ)

        root_causes_clean = sorted(c for c in root_causes if c)
        recommendation = recommend_action(failure_label, root_causes_clean)

        # lessons.append({
        #     "failure": failure_label,
        #     "occurrences": len(nodes),
        #     "equipment_involved": sorted(equipment_involved),
        #     "root_causes": root_causes_clean,
        #     "evidence_docs": sorted(evidence_docs),
        #     "recommendation": recommendation,
        # })
                # Calculate occurrences using both graph nodes and maintenance dates
        # dates = set()

        # for failure_node in nodes:
        #     failure_date = G.nodes[failure_node].get("date")
        #     if failure_date:
        #         dates.add(failure_date)

        # occurrence_count = max(
        #     len(nodes),
        #     len(dates)
        # )
        dates = set()

        for failure_node in nodes:
            failure_date = G.nodes[failure_node].get("date")

            # If multiple dates exist
            if isinstance(failure_date, list):
                for d in failure_date:
                    if d:
                        dates.add(d)

            # If single date exists
            elif failure_date:
                dates.add(failure_date)


        occurrence_count = max(
            len(nodes),
            len(dates)
        )

        lessons.append({
            "failure": failure_label,
            "occurrences": occurrence_count,
            "equipment_involved": sorted(equipment_involved),
            "root_causes": root_causes_clean,
            "evidence_docs": sorted(evidence_docs),
            "recommendation": recommendation,
        })

    lessons.sort(key=lambda x: (-x["occurrences"], x["failure"]))
    return lessons


def recommend_action(failure_label, root_causes):
    text = f"{failure_label} {' '.join(root_causes)}".lower()
    if "lubric" in text:
        return "Tighten lubrication intervals, validate lubricant grade, and add vibration trending."
    if "seal" in text or "leak" in text:
        return "Inspect seal material compatibility, stock replacement kits, and increase leakage inspection frequency."
    if "overheat" in text or "temperature" in text:
        return "Review cooling conditions, alarm thresholds, and preventive inspection intervals."
    if "pressure" in text:
        return "Audit pressure control loops, recalibrate instruments, and review relief/protection settings."
    return "Review repeat-failure evidence, standardize the corrective action, and convert it into a preventive maintenance task."


def graph_to_visual_payload(G, max_nodes=60, max_edges=100):
    if G is None:
        return {"nodes": [], "edges": [], "width": 980, "height": 560}

    selected_nodes = []
    for node_type in NODE_TYPE_ORDER:
        nodes_of_type = [
            (node, data) for node, data in G.nodes(data=True)
            if data.get("node_type") == node_type
        ]
        nodes_of_type.sort(key=lambda x: x[1].get("label", x[0]))
        selected_nodes.extend(nodes_of_type[: max(8, max_nodes // len(NODE_TYPE_ORDER))])

    seen = set()
    deduped = []
    for node, data in selected_nodes:
        if node in seen:
            continue
        seen.add(node)
        deduped.append((node, data))
        if len(deduped) >= max_nodes:
            break

    type_groups = defaultdict(list)
    for node, data in deduped:
        type_groups[data.get("node_type", "unknown")].append((node, data))

    width = 980
    height = 560
    left_margin = 90
    top_margin = 70
    column_gap = 190

    nodes_payload = []
    node_lookup = set()
    for col, node_type in enumerate(NODE_TYPE_ORDER):
        group = type_groups.get(node_type, [])
        if not group:
            continue
        vertical_gap = max(70, min(110, (height - 140) // max(1, len(group))))
        for row, (node, data) in enumerate(group):
            x = left_margin + col * column_gap
            y = top_margin + row * vertical_gap
            nodes_payload.append({
                "id": node,
                "label": str(data.get("label", node))[:34],
                "full_label": data.get("label", node),
                "node_type": data.get("node_type", "unknown"),
                "x": x,
                "y": y,
                "color": NODE_TYPE_COLORS.get(data.get("node_type"), "#95a5a6"),
            })
            node_lookup.add(node)

    edges_payload = []
    for source, target, data in G.edges(data=True):
        if source in node_lookup and target in node_lookup:
            edges_payload.append({
                "source": source,
                "target": target,
                "relation": data.get("relation", ""),
            })
            if len(edges_payload) >= max_edges:
                break

    return {
        "nodes": nodes_payload,
        "edges": edges_payload,
        "width": width,
        "height": height,
        "legend": [{"type": t, "color": NODE_TYPE_COLORS[t]} for t in NODE_TYPE_ORDER],
    }


if __name__ == "__main__":
    G = build_graph(export_html=True)
    if G is None:
        sys.exit(1)

    if len(sys.argv) > 1:
        equipment = sys.argv[1]
        result = query_equipment_history(G, equipment)
        print(f"\n--- History for {equipment} ---")
        print(json.dumps(result, indent=2))
    else:
        lessons = generate_lessons_learned(G)
        print("\n--- Recurring failure patterns ---")
        print(json.dumps(lessons[:5], indent=2))
