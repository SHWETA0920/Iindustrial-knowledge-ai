"""
MODULE 2: INDUSTRIAL ENTITY EXTRACTION
MODULE 3: METADATA MANAGEMENT
-----------------------------------------
Runs after ingest.py. For every chunk, extracts industrial entities
(equipment, failures, root causes, operational parameters, regulatory
references) using Groq, with a self-verification pass so low-confidence
entities are flagged rather than silently trusted.

Saves results into outputs_store/entities.json — this file is what the
Knowledge Graph module (Module 4) and the RCA agent (Module 6) both read.

Usage:
    python src/extract_entities.py
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

METADATA_PATH = "outputs_store/metadata.json"
ENTITIES_PATH = "outputs_store/entities.json"

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

EXTRACTION_PROMPT = """Extract structured industrial entities from this document chunk.
Return ONLY valid JSON, no preamble, no markdown fences.

Chunk:
\"\"\"
{chunk_text}
\"\"\"

Schema:
{{
  "equipment": [{{"tag": string, "type": string}}],
  "failures": [{{"description": string, "equipment_tag": string_or_null}}],
  "root_causes": [{{"description": string, "linked_failure": string_or_null}}],
  "operational_parameters": [{{"name": string, "value": string, "unit": string}}],
  "regulatory_references": [{{"code": string, "clause": string_or_null}}],
  "dates": [string]
}}

If a category has no entities, return an empty array for it. Only extract
entities that are explicitly present in the text — do not infer or guess.
"""

VERIFICATION_PROMPT = """You are a QA reviewer. Check whether each extracted entity
actually appears in the original text below, or is a reasonable paraphrase of it.

Original text:
\"\"\"
{chunk_text}
\"\"\"

Extracted entities:
{extracted_json}

Return ONLY valid JSON in this format:
{{
  "confirmed_indices": {{"equipment": [0, 1], "failures": [0], "root_causes": [], "operational_parameters": [0], "regulatory_references": [], "dates": [0]}},
  "flagged_indices": {{"equipment": [], "failures": [], "root_causes": [], "operational_parameters": [], "regulatory_references": [], "dates": []}}
}}
Indices refer to the position of each entity within its category's array in the extracted entities.
"""


def call_llm_json(prompt):
    """Call Groq and parse the response as JSON, tolerating minor formatting issues."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    text = response.choices[0].message.content.strip()
    # strip markdown fences if the model adds them anyway
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("    Warning: could not parse LLM JSON output, skipping this chunk.")
        return None


def extract_with_confidence(chunk_text):
    """Two-pass extraction: draft, then verify. Returns entities tagged with confidence."""
    draft = call_llm_json(EXTRACTION_PROMPT.format(chunk_text=chunk_text))
    if draft is None:
        return None

    verification = call_llm_json(VERIFICATION_PROMPT.format(
        chunk_text=chunk_text,
        extracted_json=json.dumps(draft)
    ))

    if verification is None:
        # If verification fails, keep everything but mark it unverified rather
        # than losing the extraction entirely.
        for category in draft:
            for entity in draft[category]:
                if isinstance(entity, dict):
                    entity["confidence"] = "unverified"
        return draft

    confirmed = verification.get("confirmed_indices", {})
    flagged = verification.get("flagged_indices", {})

    for category in draft:
        for idx, entity in enumerate(draft[category]):
            if not isinstance(entity, dict):
                continue
            if idx in flagged.get(category, []):
                entity["confidence"] = "needs_review"
            elif idx in confirmed.get(category, []):
                entity["confidence"] = "high"
            else:
                entity["confidence"] = "medium"

    return draft


def run_extraction():
    if not os.path.exists(METADATA_PATH):
        print("No metadata found. Run 'python src/ingest.py' first.")
        return

    with open(METADATA_PATH, "r") as f:
        data = json.load(f)

    chunks = data["chunks"]
    metadata = data["metadata"]

    all_entities = []
    total = len(chunks)

    for i, (chunk, meta) in enumerate(zip(chunks, metadata)):
        print(f"Extracting entities [{i + 1}/{total}] from {meta['source']} (page {meta['page']})...")
        entities = extract_with_confidence(chunk)
        if entities is None:
            continue

        entities["_chunk_id"] = meta["chunk_id"]
        entities["_source"] = meta["source"]
        entities["_page"] = meta["page"]
        entities["_category"] = meta["category"]
        all_entities.append(entities)

    os.makedirs("outputs_store", exist_ok=True)
    with open(ENTITIES_PATH, "w") as f:
        json.dump(all_entities, f, indent=2)

    # Summary stats
    needs_review_count = 0
    equipment_count = 0
    for e in all_entities:
        for category in ["equipment", "failures", "root_causes", "operational_parameters", "regulatory_references"]:
            for item in e.get(category, []):
                if isinstance(item, dict):
                    if item.get("confidence") == "needs_review":
                        needs_review_count += 1
                    if category == "equipment":
                        equipment_count += 1

    print(f"\nDone. Extracted entities from {len(all_entities)} chunks.")
    print(f"Equipment entities found: {equipment_count}")
    print(f"Entities flagged for human review: {needs_review_count}")
    print(f"Saved to {ENTITIES_PATH}")


if __name__ == "__main__":
    run_extraction()
