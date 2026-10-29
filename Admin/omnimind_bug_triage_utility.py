#!/usr/bin/env python3
"""
============================================================================
THE OMNIVERSE - OMNIMIND BUG TRIAGE UTILITY  (daemon v8.9.0+)

Reads the bug reports testers send to the hub (POST :5000/api/bugs/report, stored by
omni_live_daemon_server.py as chain events with action "bug_report" in continuity_events.db,
table `events`), and for every report really checks:

  - hash:      event_id == "0x" + sha256(canonical event bytes)   (same as the daemon)
  - signature: Ed25519 signature by author_pubkey over those bytes (omni_signing.verify_event)
  - link:      previous_hash is the event_id of the row stored right before it ("OK"),
               otherwise an event this node holds / the zero hash ("KNOWN"), otherwise "BROKEN"

Duplicates are grouped by normalized what_happened + device.

Usage (run from the folder that holds continuity_events.db, or pass --db):
  python3 omnimind_bug_triage_utility.py list [--limit N]
  python3 omnimind_bug_triage_utility.py show <event_id>
  python3 omnimind_bug_triage_utility.py summary
  add --json for machine-readable output
See Admin/docs/BUG_REPORTS.md.
============================================================================
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omni_signing import canonical_event_bytes, verify_event  # noqa: E402  same helpers as the daemon

BUG_REPORT_ACTION = "bug_report"
DEFAULT_DB = "continuity_events.db"
ZERO_HASH = "0x" + "0" * 64
_COLS = "id, event_id, action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms"


def _connect(db_path) -> sqlite3.Connection:
    p = Path(db_path)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found (run from the daemon's folder or pass --db)")
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _event_struct(row) -> dict:
    """The event exactly as it was signed: int-ms "ts" when ts_ms is set, legacy float "timestamp"
    otherwise (mirrors the daemon's _row_to_feed_event)."""
    payload = json.loads(row["payload_json"] or "{}")
    if not isinstance(payload, dict):
        raise ValueError("payload is not a JSON object")
    ev = {"action": row["action"], "author_pubkey": row["author_pubkey"], "payload": payload,
          "previous_hash": row["previous_hash"]}
    if row["ts_ms"] is not None:
        ev["ts"] = int(row["ts_ms"])
    else:
        ev["timestamp"] = row["timestamp"]
    return ev


def compute_event_id(event: dict) -> str:
    """Same as omni_live_daemon_server.compute_canonical_event_id."""
    return "0x" + hashlib.sha256(canonical_event_bytes(event)).hexdigest()


def verify_row(conn, row) -> dict:
    out = {"hash_ok": False, "signature_ok": False, "link": "BROKEN", "valid": False, "payload": {}}
    try:
        ev = _event_struct(row)
    except (ValueError, TypeError) as e:
        out["error"] = f"unreadable payload: {e}"
        return out
    out["payload"] = ev["payload"]
    try:
        out["hash_ok"] = compute_event_id(ev) == row["event_id"]
        out["signature_ok"] = bool(row["signature"]) and verify_event(dict(ev, signature=row["signature"]))
    except (ValueError, TypeError) as e:
        out["error"] = str(e)
    prev = conn.execute("SELECT event_id FROM events WHERE id < ? ORDER BY id DESC LIMIT 1",
                        (row["id"],)).fetchone()
    if prev is not None and prev[0] == row["previous_hash"]:
        out["link"] = "OK"
    elif row["previous_hash"] == ZERO_HASH or conn.execute(
            "SELECT 1 FROM events WHERE event_id = ? AND id < ?", (row["previous_hash"], row["id"])).fetchone():
        out["link"] = "KNOWN"
    out["valid"] = out["hash_ok"] and out["signature_ok"] and out["link"] != "BROKEN"
    return out


def _report(conn, row) -> dict:
    v = verify_row(conn, row)
    ts_ms = int(row["ts_ms"]) if row["ts_ms"] is not None else int(round(float(row["timestamp"]) * 1000))
    return {"id": row["id"], "event_id": row["event_id"], "ts_ms": ts_ms,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_ms / 1000)),
            "author_pubkey": row["author_pubkey"], "previous_hash": row["previous_hash"],
            "report": v.pop("payload"), **v}


def list_reports(db_path=DEFAULT_DB, limit: int = 50) -> list:
    conn = _connect(db_path)
    try:
        rows = conn.execute(f"SELECT {_COLS} FROM events WHERE action = ? ORDER BY id DESC LIMIT ?",
                            (BUG_REPORT_ACTION, max(1, int(limit)))).fetchall()
        return [_report(conn, r) for r in rows]
    finally:
        conn.close()


def show_report(event_id: str, db_path=DEFAULT_DB):
    conn = _connect(db_path)
    try:
        row = conn.execute(f"SELECT {_COLS} FROM events WHERE event_id = ? AND action = ?",
                           (event_id, BUG_REPORT_ACTION)).fetchone()
        return _report(conn, row) if row else None
    finally:
        conn.close()


def normalize_text(s) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def group_key(report: dict) -> tuple:
    r = report.get("report") or {}
    return normalize_text(r.get("what_happened")), normalize_text(r.get("device"))


def summarize(db_path=DEFAULT_DB) -> dict:
    conn = _connect(db_path)
    try:
        rows = conn.execute(f"SELECT {_COLS} FROM events WHERE action = ? ORDER BY id ASC",
                            (BUG_REPORT_ACTION,)).fetchall()
        reports = [_report(conn, r) for r in rows]
    finally:
        conn.close()
    groups = {}
    for rep in reports:
        g = groups.setdefault(group_key(rep), {"count": 0, "event_ids": [], "apps": set(),
                                               "first_ms": rep["ts_ms"], "last_ms": rep["ts_ms"]})
        g["count"] += 1
        g["event_ids"].append(rep["event_id"])
        if rep["report"].get("app"):
            g["apps"].add(rep["report"]["app"])
        g["last_ms"] = max(g["last_ms"], rep["ts_ms"])
        g["first_ms"] = min(g["first_ms"], rep["ts_ms"])
        g.setdefault("sample", rep["report"].get("what_happened", ""))
        g.setdefault("device", rep["report"].get("device", ""))
    out_groups = sorted(({"what_happened": g["sample"], "device": g["device"], "count": g["count"],
                          "apps": sorted(g["apps"]), "event_ids": g["event_ids"],
                          "first_ms": g["first_ms"], "last_ms": g["last_ms"]} for g in groups.values()),
                        key=lambda g: (-g["count"], -g["last_ms"]))
    invalid = [r["event_id"] for r in reports if not r["valid"]]
    return {"total": len(reports), "valid": len(reports) - len(invalid), "invalid": invalid,
            "groups": out_groups}


def _status(rep) -> str:
    if rep["valid"]:
        return "VERIFIED"
    bad = [k for k, ok in (("hash", rep["hash_ok"]), ("signature", rep["signature_ok"]),
                           ("link", rep["link"] != "BROKEN")) if not ok]
    return "INVALID(" + ",".join(bad) + ")"


def _short(s, n=70) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OmniMind bug triage for continuity_events.db")
    ap.add_argument("--db", default=DEFAULT_DB, help="path to continuity_events.db")
    ap.add_argument("--json", action="store_true", help="print JSON")
    sub = ap.add_subparsers(dest="cmd")
    p_list = sub.add_parser("list", help="newest bug reports first")
    p_list.add_argument("--limit", type=int, default=20)
    p_show = sub.add_parser("show", help="one report with its verification")
    p_show.add_argument("event_id")
    sub.add_parser("summary", help="counts, invalid reports and duplicate groups")
    args = ap.parse_args(argv)
    cmd = args.cmd or "summary"
    try:
        if cmd == "list":
            reps = list_reports(args.db, args.limit)
            if args.json:
                print(json.dumps(reps, indent=2))
            elif not reps:
                print("No bug reports yet.")
            for r in ([] if args.json else reps):
                rr = r["report"]
                print(f"{r['time']}  {_status(r):<20} {r['event_id'][:18]}…  "
                      f"[{rr.get('app', '?')} {rr.get('app_version', '')}] {rr.get('device', '')}: "
                      f"{_short(rr.get('what_happened'))}")
            return 0
        if cmd == "show":
            rep = show_report(args.event_id, args.db)
            if rep is None:
                print(f"No bug report with event_id {args.event_id}", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(rep, indent=2))
            else:
                print(f"event_id:  {rep['event_id']}\ntime:      {rep['time']}\nauthor:    {rep['author_pubkey']}")
                print(f"hash:      {'OK' if rep['hash_ok'] else 'MISMATCH'}\n"
                      f"signature: {'OK' if rep['signature_ok'] else 'INVALID'}\nlink:      {rep['link']}")
                for k, v in rep["report"].items():
                    print(f"{k + ':':<17}{v}")
            return 0 if rep["valid"] else 2
        s = summarize(args.db)
        if args.json:
            print(json.dumps(s, indent=2))
            return 0
        print(f"Bug reports: {s['total']}  verified: {s['valid']}  invalid: {len(s['invalid'])}")
        for eid in s["invalid"]:
            print(f"  ! INVALID {eid}")
        print(f"Distinct issues (by what_happened + device): {len(s['groups'])}")
        for g in s["groups"]:
            print(f"  x{g['count']:<3} {_short(g['what_happened'], 60)}  — {g['device'] or 'unknown device'}"
                  f"  apps={','.join(g['apps']) or '?'}  latest={g['event_ids'][-1][:18]}…")
        return 0
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
