"""Build report.html from report.json + template.html for the ga-traffic-report skill.

Usage:
  python build.py <data folder>            build report.html, stage history.pending.json
  python build.py <data folder> --commit   after a successful publish: pending -> history.json

The data folder (the card's **Data folder**) holds report.json, which the run writes, plus
history.json and report.html, which this script writes. template.html ships next to this script.

Also tracks triage actions across runs (history.json) so the page can mark each
action NEW or "open since <date>", and list actions cleared since the last run. The new
history is only staged by the build; the run commits it once the page is published, so a
failed publish does not advance it.
"""
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "template.html"
PLACEHOLDER = "/*__REPORT_DATA__*/null"
PRIORITIES = {"now", "soon", "fyi"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def fail(msg):
    print(f"build failed: {msg}")
    sys.exit(1)


def commit(data_dir):
    pending = data_dir / "history.pending.json"
    if not pending.exists():
        fail(f"{pending} not found; run the build first")
    os.replace(pending, data_dir / "history.json")
    print(f"committed {data_dir / 'history.json'}")


def main():
    args = sys.argv[1:]
    commit_mode = "--commit" in args
    args = [a for a in args if a != "--commit"]
    if len(args) != 1:
        fail("usage: python build.py <data folder> [--commit]")
    data_dir = Path(args[0]).resolve()
    if not data_dir.is_dir():
        fail(f"data folder {data_dir} not found")
    if commit_mode:
        commit(data_dir)
        return
    report = data_dir / "report.json"
    history_path = data_dir / "history.json"
    pending_path = data_dir / "history.pending.json"
    out = data_dir / "report.html"

    if not report.exists():
        fail(f"{report} not found")
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"report.json is not valid JSON: {e}")

    # Valid JSON is not a valid report: the page calls array methods on these.
    if not isinstance(data, dict):
        fail("report.json must be a JSON object")
    for key in ("window", "sites", "actions"):
        if key not in data:
            fail(f"report.json missing '{key}'")
    if not isinstance(data["window"], dict):
        fail("report.json 'window' must be an object")
    for key in ("sites", "actions"):
        if not isinstance(data[key], list):
            fail(f"report.json '{key}' must be an array")
    for key in ("notConnected", "errors"):
        if data.get(key) is not None:
            if not isinstance(data[key], list):
                fail(f"report.json '{key}' must be an array")
            if any(not isinstance(x, dict) for x in data[key]):
                fail(f"report.json '{key}' must hold objects")
    if any(not isinstance(a, dict) for a in data["actions"]):
        fail("report.json 'actions' must hold objects")
    if any(not isinstance(s, dict) for s in data["sites"]):
        fail("report.json 'sites' must hold objects")

    # The report's own calendar date, in the card's time zone (generatedAt carries its offset),
    # not this machine's date, so firstSeen/lastRun match the report.
    try:
        today = datetime.fromisoformat(str(data.get("generatedAt", ""))).date().isoformat()
    except ValueError:
        today = date.today().isoformat()
    history = {}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            # Never reset it: that would wipe every action's firstSeen date for good.
            fail(f"{history_path} is not valid JSON ({e}); fix or restore it, then rebuild")
        if not isinstance(history, dict):
            fail(f"{history_path} must be a JSON object; fix or restore it, then rebuild")
    prev_open = history.get("open", {})

    # Sites this run could not assess. Their missing actions are unknown, not cleared.
    failed_sites = {slug(s.get("name", "")) for s in data["sites"] if s.get("status") != "ok"}
    failed_sites |= {slug(e.get("site", "")) for e in (data.get("errors") or []) if isinstance(e, dict)}
    failed_sites.discard("")

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

    carried = {}
    resolved = []
    for k, v in prev_open.items():
        if k in seen_ids:
            continue
        if slug(v.get("site", "")) in failed_sites:
            carried[k] = v
        else:
            resolved.append({"site": v.get("site", ""), "title": v.get("title", "")})
    data["resolved"] = resolved

    open_now = {
        a["id"]: {"firstSeen": a["firstSeen"], "site": a.get("site", ""), "title": a.get("title", "")}
        for a in data["actions"]
    }
    open_now.update(carried)
    next_history = {"runs": history.get("runs", 0) + 1, "lastRun": today, "open": open_now}

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        fail("template.html has no data placeholder")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(template.replace(PLACEHOLDER, blob), encoding="utf-8")
    pending_path.write_text(json.dumps(next_history, indent=2), encoding="utf-8")

    counts = {p: sum(1 for a in data["actions"] if a["priority"] == p) for p in ("now", "soon", "fyi")}
    new = sum(1 for a in data["actions"] if a["isNew"])
    errors = data.get("errors") or []
    print(
        f"built {out}: {len(data['sites'])} sites, actions now={counts['now']} "
        f"soon={counts['soon']} fyi={counts['fyi']} (new {new}, cleared {len(resolved)}, "
        f"kept for failed sites {len(carried)})"
    )
    print(f"staged {pending_path.name}; run with --commit after the publish succeeds")
    if errors:
        print("failed calls: " + "; ".join(f"{e.get('site')}/{e.get('call')}" for e in errors))


if __name__ == "__main__":
    main()
