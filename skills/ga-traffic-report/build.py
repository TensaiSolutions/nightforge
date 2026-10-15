"""Build report.html from report.json + template.html for the ga-traffic-report skill.

Usage: python build.py <data folder>

The data folder (the card's **Data folder**) holds report.json, which the run writes, plus
history.json and report.html, which this script writes. template.html ships next to this script.

Also tracks triage actions across runs (history.json) so the page can mark each
action NEW or "open since <date>", and list actions cleared since the last run.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "template.html"
PLACEHOLDER = "/*__REPORT_DATA__*/null"
PRIORITIES = {"now", "soon", "fyi"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def fail(msg):
    print(f"build failed: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: python build.py <data folder>")
    data_dir = Path(sys.argv[1]).resolve()
    if not data_dir.is_dir():
        fail(f"data folder {data_dir} not found")
    report = data_dir / "report.json"
    history_path = data_dir / "history.json"
    out = data_dir / "report.html"

    if not report.exists():
        fail(f"{report} not found")
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"report.json is not valid JSON: {e}")

    for key in ("window", "sites", "actions"):
        if key not in data:
            fail(f"report.json missing '{key}'")

    today = date.today().isoformat()
    history = {}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = {}
    prev_open = history.get("open", {})

    seen_ids = set()
    for a in data["actions"]:
        if a.get("priority") not in PRIORITIES:
            a["priority"] = "fyi"
        # Normalise the site part of the id so "open since" survives wording drift between runs.
        raw = a.get("id") or f"x:{a.get('kind', '')}:{a.get('title', '')}"
        rest = raw.split(":", 1)[1] if ":" in raw else raw
        aid = f"{slug(a.get('site', ''))}:{rest.lower()}"
        a["id"] = aid
        seen_ids.add(aid)
        if aid in prev_open:
            a["isNew"] = False
            a["firstSeen"] = prev_open[aid]["firstSeen"]
        else:
            a["isNew"] = bool(prev_open) or bool(history.get("runs"))
            a["firstSeen"] = today

    data["resolved"] = [
        {"site": v.get("site", ""), "title": v.get("title", "")}
        for k, v in prev_open.items()
        if k not in seen_ids
    ]

    history = {
        "runs": history.get("runs", 0) + 1,
        "lastRun": today,
        "open": {
            a["id"]: {"firstSeen": a["firstSeen"], "site": a.get("site", ""), "title": a.get("title", "")}
            for a in data["actions"]
        },
    }

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        fail("template.html has no data placeholder")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(template.replace(PLACEHOLDER, blob), encoding="utf-8")
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    counts = {p: sum(1 for a in data["actions"] if a["priority"] == p) for p in ("now", "soon", "fyi")}
    new = sum(1 for a in data["actions"] if a["isNew"])
    errors = data.get("errors") or []
    print(
        f"built {out}: {len(data['sites'])} sites, actions now={counts['now']} "
        f"soon={counts['soon']} fyi={counts['fyi']} (new {new}, cleared {len(data['resolved'])})"
    )
    if errors:
        print("failed calls: " + "; ".join(f"{e.get('site')}/{e.get('call')}" for e in errors))


if __name__ == "__main__":
    main()
