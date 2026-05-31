#!/usr/bin/env python3
"""Post-deploy smoke: paper workflow must create a record and clear loop_empty."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _get(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Ops-Admin-Token"] = token
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:500]}
        return exc.code, payload


def main() -> int:
    base = (os.environ.get("BACKEND_PUBLIC_URL") or "").strip().rstrip("/")
    token = (os.environ.get("OPS_ADMIN_TOKEN") or "").strip()
    if not base:
        print("SKIP: BACKEND_PUBLIC_URL not set")
        return 0
    if not token:
        print("FAIL: OPS_ADMIN_TOKEN required for paper workflow smoke")
        return 1

    _, tower_before = _get(f"{base}/api/v1/daytrading/paper-autonomy/control-tower")
    before_codes = {a.get("code") for a in tower_before.get("alerts") or [] if isinstance(a, dict)}

    status, run = _get(
        f"{base}/api/v1/daytrading/workflow/run",
        token=token,
        method="POST",
        body={"run_mode": "paper", "symbols": ["AAPL"], "source": "runtime"},
    )
    if status != 200:
        print(f"FAIL: workflow/run HTTP {status} {run}")
        return 1

    submitted = bool(run.get("submitted_order"))
    blockers = list(run.get("blockers") or [])[:10]
    print(f"workflow status={run.get('status')} submitted_order={submitted}")
    if blockers:
        print(f"blockers={blockers}")

    _, tower_after = _get(f"{base}/api/v1/daytrading/paper-autonomy/control-tower")
    summary = tower_after.get("summary") or {}
    orders = int(summary.get("paper_orders") or 0)
    after_codes = {a.get("code") for a in tower_after.get("alerts") or [] if isinstance(a, dict)}

    print(f"control_tower paper_orders={orders} alerts={sorted(after_codes)}")

    failures: list[str] = []
    if not submitted and orders < 1:
        failures.append("no submitted_order and no paper orders in store")
    if orders < 1:
        failures.append("paper_orders still 0")
    if orders > 0 and "loop_empty" in after_codes:
        failures.append("loop_empty alert still present with orders")

    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    if "loop_empty" in before_codes and "loop_empty" not in after_codes:
        print("PASS: loop_empty cleared after paper run")
    else:
        print("PASS: paper autonomy loop populated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
