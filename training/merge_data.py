"""
merge_data.py

Reads every JSON file inside data/raw/ and converts each one into the
common knowledge-base format:
    {
        "id": "...",
        "category": "...",
        "question": "...",
        "answer": "...",
        "source_file": "..."
    }

Generic recursive handler: walks any nested JSON structure regardless
of its specific shape, since each of the 34 category files has its own
custom structure. Skips "university", "meta", and "data_type"/"data_types"
keys (internal project documentation, not chatbot-facing content).

Properly recurses into multi-level nested structures (e.g. a faculty
dict containing a nested "courses" list, which itself contains a
nested "specializations" list) instead of flattening them into one
lossy generic entry.

After the main walk, consolidate_course_level_fees() adds one clean,
combined entry per course (e.g. "What is the fee for B.Tech?") so a
plain course-level question isn't diluted across many competing
specialization-level entries.

Run this from inside the `training` folder:
    python merge_data.py
"""

import json
import os
import re
import glob

RAW_DIR = "../data/raw"
OUTPUT_FILE = "../data/knowledge_base.json"

SKIP_KEYS = {"university", "meta", "data_type", "data_types"}
LABEL_KEYS = ("name", "course_name", "faculty_name", "company", "title")

merged = []
counter = 0


def humanize(key):
    return key.replace("_", " ").strip()


def new_id(prefix):
    global counter
    counter += 1
    return f"{prefix}-{counter:05d}"


def add_entry(question, answer, category, source_file):
    question = question.strip()
    answer = answer.strip()
    if not question or not answer:
        return
    merged.append({
        "id": new_id("GEN"),
        "category": category,
        "question": question,
        "answer": answer,
        "source_file": source_file
    })


def _is_leaf_dict(d):
    """A dict with no further nested dict/list values - safe to combine
    into a single answer instead of recursing deeper."""
    for k, v in d.items():
        if k in SKIP_KEYS:
            continue
        if isinstance(v, (dict, list)):
            return False
    return True


def _dict_to_answer_text(d):
    parts = []
    for k, v in d.items():
        if k in SKIP_KEYS:
            continue
        if isinstance(v, str) and v.strip():
            if k.lower() in ("figure", "description", "summary", "overview"):
                parts.append(v.strip())
            else:
                parts.append(f"{humanize(k)}: {v.strip()}")
    return " ".join(parts)


def _extract_label(d):
    for k in LABEL_KEYS:
        if d.get(k):
            return k, d[k]
    return None, None


def walk(node, path, category, source_file):
    if isinstance(node, dict):
        if _is_leaf_dict(node):
            answer = _dict_to_answer_text(node)
            if answer:
                topic = " - ".join(path) if path else category
                question = f"What is known about {topic}?"
                add_entry(question, answer, category, source_file)
            return
        for key, value in node.items():
            if key in SKIP_KEYS:
                continue
            walk(value, path + [humanize(key)], category, source_file)

    elif isinstance(node, list):
        if not node:
            return
        if all(isinstance(x, str) for x in node):
            topic = " - ".join(path)
            question = f"What is known about {topic}?"
            answer = "; ".join(node)
            add_entry(question, answer, category, source_file)

        elif all(isinstance(x, dict) for x in node):
            for item in node:
                label_key, label_val = _extract_label(item)

                if _is_leaf_dict(item):
                    item_for_text = {k: v for k, v in item.items() if k != label_key}
                    sentence = _dict_to_answer_text(item_for_text)
                    if not sentence:
                        continue
                    topic = " - ".join(path)
                    if label_val:
                        question = f"What are the details for {label_val} under {topic}?"
                        sentence = f"{label_val}: {sentence}"
                    else:
                        question = f"What is known about {topic}?"
                    add_entry(question, sentence, category, source_file)
                else:
                    # This item has further nested lists/dicts inside it
                    # (e.g. a faculty dict containing a nested "courses"
                    # list, which itself contains nested "specializations").
                    # Recurse into each of its fields instead of flattening
                    # it into one lossy generic entry.
                    sub_path = path + [label_val] if label_val else path
                    for k, v in item.items():
                        if k in SKIP_KEYS or k == label_key:
                            continue
                        walk(v, sub_path + [humanize(k)], category, source_file)
        else:
            topic = " - ".join(path)
            question = f"What is known about {topic}?"
            answer = "; ".join(str(x) for x in node)
            add_entry(question, answer, category, source_file)

    elif isinstance(node, str):
        if node.strip():
            topic = " - ".join(path) if path else category
            question = f"What is known about {topic}?"
            add_entry(question, node, category, source_file)


def consolidate_course_level_fees():
    """
    The generic walker creates one entry PER specialization under each
    course (e.g. 13 separate entries for B.Tech's 13 specializations).
    This means a simple question like "what is the fee for btech" has
    no single strong matching entry - it's diluted across many
    competing specialization-level entries.

    This scans those fragmented entries after the fact, groups them
    back by (faculty, course), and adds ONE additional clean,
    course-level fee entry per course - e.g. "What is the fee for
    B.Tech at Parul University?" -> states the fee directly when all
    specializations share it, or a range when they differ.
    """
    pattern = re.compile(
        r"^What are the details for (.+?) under (.+?) - courses - (.+?) - specializations\?$"
    )

    groups = {}

    for entry in merged:
        if entry["category"] != "faculties":
            continue
        m = pattern.match(entry["question"])
        if not m:
            continue

        spec_name, faculty_name, course_name = m.groups()

        fee_match = re.search(r"tuition fee:\s*(.+)$", entry["answer"])
        if not fee_match:
            continue
        fee_text = fee_match.group(1).strip()

        key = (faculty_name, course_name)
        groups.setdefault(key, []).append((spec_name, fee_text))

    added = 0
    for (faculty_name, course_name), specs in groups.items():
        if len(specs) < 2:
            continue  # single specialization - already directly findable

        spec_names = [s[0] for s in specs]
        fees = [s[1] for s in specs]
        unique_fees = set(fees)

        if len(unique_fees) == 1:
            fee_statement = f"the annual tuition fee is {fees[0]}"
        else:
            fee_statement = (
                "annual tuition fees vary by specialization, ranging across: "
                + ", ".join(sorted(unique_fees))
            )

        question = f"What is the fee for {course_name} at Parul University?"
        answer = (
            f"{course_name} under {faculty_name} — {fee_statement}. "
            f"Specializations include: {', '.join(spec_names)}."
        )
        add_entry(question, answer, "faculties", "consolidated_course_fees")
        added += 1

    return added


def process_file(filepath):
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  {filename:55s} -> ❌ SKIPPED (invalid JSON: {e})")
        return 0
    except Exception as e:
        print(f"  {filename:55s} -> ❌ SKIPPED (error: {e})")
        return 0

    before = len(merged)
    for top_key, value in data.items():
        if top_key in SKIP_KEYS:
            continue
        category = humanize(top_key)
        walk(value, [], category, filename)

    return len(merged) - before


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"❌ Folder not found: {RAW_DIR}")
        return

    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
    print(f"Found {len(files)} JSON files in {RAW_DIR}\n")

    for filepath in files:
        n = process_file(filepath)
        print(f"  {os.path.basename(filepath):55s} -> {n} entries")

    print(f"\nTotal entries before consolidation: {len(merged)}")

    n_added = consolidate_course_level_fees()
    print(f"Added {n_added} consolidated course-level fee entries")

    seen = set()
    deduped = []
    for e in merged:
        key = e["question"].strip().lower()
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    removed = len(merged) - len(deduped)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Merged {len(deduped)} unique entries (removed {removed} duplicates)")
    print(f"✅ Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()