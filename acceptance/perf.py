"""AC-18 performance check (REQ-17): with 1,000 tickets stored, send 200 mixed requests
one at a time; the 95th percentile latency, measured by this client, must be at most 1 s.

    export CRA_BASE_URL=https://<deployment-base-url>
    export CRA_API_TOKEN=<token>      # never commit it or paste it into a prompt
    python -m acceptance.perf --reset --out perf.json

Run it from the repository root. It is not part of the pytest suite or the deployed
tester: it loads about 2,400 requests' worth of data and takes minutes.

Phases, in order:

1. Warm-up: ``--warmup`` untimed requests (health, clock, list), reported on their own
   as cold-start numbers. Cloud Run and Neon may both be asleep before this.
2. Reset (only with ``--reset``): ``POST /test/reset`` deletes every ticket on the
   deployment, for every client. Without it the deployment must already be empty.
3. Load: valid tickets through the public API only (submit, triage, record
   submission, close), in the fixed ``LOAD_PROFILE`` mix. Not timed. By default it
   loads ``--tickets`` minus the measured POSTs (990), so the store holds exactly
   ``--tickets`` (1,000, the spec's limit) after the last measured request.
4. Measured: ``--requests`` requests sent one after another in the fixed
   ``MEASURED_MIX``, shuffled by ``--seed``. Each request has one expected status; any
   other status, a connection error or a response that breaks the contract schema is a
   failure, however fast it was.

Times are derived from the service's own clock (``GET /test/clock``), read once before
loading, and always lie in the past, so the script never sets the clock. A fixed clock
left by an earlier run is used as it is. With ``--exceed-limit`` the load is the full
``--tickets`` and the measured POSTs take the store past it (1,010), a slightly harder
test than the requirement.

Latency is the wall time of one HTTP request, from sending it to reading the whole
response body. The transport opens a new connection per request (as the acceptance
runner does), so against HTTPS each sample includes a TCP and TLS handshake.

Percentiles use the nearest-rank method: p95 of 200 samples is the 190th fastest.

Exit status: 0 if p95 <= 1 s and nothing failed, 1 if not, 2 if the run could not
start or the load failed. Afterwards the deployment holds the loaded tickets; a final
``POST /test/reset`` is the operator's call.
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote, urlencode

from acceptance.client import ROOT, Contract, HTTPTransport

ACTOR = "perf-ac18"
P95_LIMIT_SECONDS = 1.0
DEFAULT_SEED = 17

# Measured operations and their share of the 200 requests (sum 200). Each name maps
# to one contract operation; the three list variants are reported separately.
MEASURED_MIX = {
    "list": 20,  # GET /tickets
    "list_state": 10,  # GET /tickets?state=...
    "list_status": 10,  # GET /tickets?obligation_status=...
    "get": 50,  # GET /tickets/{id}
    "draft": 30,  # GET /tickets/{id}/reports/{type}
    "audit": 20,  # GET /tickets/{id}/audit
    "patch": 20,  # PATCH /tickets/{id}
    "create": 10,  # POST /tickets
    "triage": 10,  # POST /tickets/{id}/triage
    "submission": 10,  # POST /tickets/{id}/reports/{type}/submission
    "close": 10,  # POST /tickets/{id}/close
}

OPERATIONS = {
    "list": ("GET", "/tickets", 200),
    "list_state": ("GET", "/tickets", 200),
    "list_status": ("GET", "/tickets", 200),
    "get": ("GET", "/tickets/{id}", 200),
    "draft": ("GET", "/tickets/{id}/reports/{type}", 200),
    "audit": ("GET", "/tickets/{id}/audit", 200),
    "patch": ("PATCH", "/tickets/{id}", 200),
    "create": ("POST", "/tickets", 201),
    "triage": ("POST", "/tickets/{id}/triage", 200),
    "submission": ("POST", "/tickets/{id}/reports/{type}/submission", 200),
    "close": ("POST", "/tickets/{id}/close", 200),
}

# What the loaded tickets look like, as shares of --tickets (sum 1).
LOAD_PROFILE = {
    "received_min": Fraction(15, 100),  # required fields only, never triaged
    "received_full": Fraction(15, 100),  # every field, never triaged
    "reportable": Fraction(25, 100),  # triaged actively_exploited, nothing recorded
    "early_warning": Fraction(10, 100),  # + early warning recorded
    "notification": Fraction(10, 100),  # + early warning and notification recorded
    "final_report": Fraction(5, 100),  # all three recorded, still reportable
    "resolved": Fraction(5, 100),  # all three recorded, then closed (resolved)
    "not_reportable": Fraction(15, 100),  # triaged not_actively_exploited or invalid
}
REPORTABLE = ("reportable", "early_warning", "notification", "final_report", "resolved")
RECORDED = {
    "reportable": (),
    "early_warning": ("early_warning",),
    "notification": ("early_warning", "notification"),
    "final_report": ("early_warning", "notification", "final_report"),
    "resolved": ("early_warning", "notification", "final_report"),
}

# Pools the mutating measured operations draw from, without replacement and disjoint,
# so every measured request has a known expected status.
MUTATION_POOLS = {
    "triage": ("received_full",),
    "submission": ("reportable", "early_warning"),
    "close": ("final_report",),
    "patch": ("received_min", "reportable", "early_warning", "notification"),
}
READ_POOLS = {
    "get": tuple(LOAD_PROFILE),
    "audit": tuple(LOAD_PROFILE),
    "draft": REPORTABLE,
}
LIST_STATES = ("received", "reportable", "closed")
LIST_STATUSES = ("pending", "overdue", "submitted", "awaiting_fix", "not_applicable")
DRAFT_TYPES = ("early_warning", "notification", "final_report", "user_advisory")
MEMBER_STATES = ("DE", "NL", "FR", "IE", "AT", "BE", "ES", "IT", "PL", "SE")


class SetupError(Exception):
    """The run cannot start or its load failed; nothing was measured."""


# ---------------------------------------------------------------- pure helpers


def percentile(values, pct) -> float:
    """Nearest-rank percentile: the smallest value with at least pct% of values at or
    below it. percentile(200 samples, 95) is the 190th smallest."""
    if not values:
        raise ValueError("no values")
    if not 0 < pct <= 100:
        raise ValueError("pct must be in (0, 100]")
    ordered = sorted(values)
    rank = math.ceil(Fraction(str(pct)) * len(ordered) / 100)
    return ordered[rank - 1]


def apportion(shares: dict, total: int) -> dict:
    """Split total into integer counts proportional to shares (largest remainder, ties
    to the earlier key), so the counts always sum to total."""
    weight = sum(Fraction(value) for value in shares.values())
    exact = {key: Fraction(value) * total / weight for key, value in shares.items()}
    counts = {key: math.floor(value) for key, value in exact.items()}
    order = sorted(exact, key=lambda key: (-(exact[key] - counts[key]), list(shares).index(key)))
    for key in order[: total - sum(counts.values())]:
        counts[key] += 1
    return counts


def summarize(seconds) -> dict:
    return {
        "n": len(seconds),
        "p50": percentile(seconds, 50),
        "p95": percentile(seconds, 95),
        "p99": percentile(seconds, 99),
        "max": max(seconds),
    }


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _full_fields(rng: random.Random, number: int, base: datetime, aware: datetime | None):
    """Every client field, so every draft is complete. The fix time is in the past and,
    for a reportable ticket, usually after awareness (sometimes before, as in E5)."""
    if aware is None:
        fix_at = base - timedelta(hours=rng.randint(1, 240))
    elif rng.random() < 0.8:
        fix_at = aware + (base - aware) * rng.random()
    else:
        fix_at = aware - timedelta(hours=rng.randint(1, 72))
    return {
        "member_states": rng.sample(MEMBER_STATES, rng.randint(1, 3)),
        "vulnerability": {
            "cve_id": f"CVE-2026-{10000 + number}",
            "description": "Crafted session cookie bypasses authentication. " * 4,
        },
        "exploit": {"description": "Observed against exposed admin interfaces."},
        "mitigations": {
            "taken": "Rotated session keys and blocked the attack pattern.",
            "for_users": "Restrict the admin interface to trusted networks.",
        },
        "impact": "An attacker can take over the device remotely.",
        "malicious_actor": "Unknown",
        "sensitivity": rng.choice(["CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED"]),
        "severity": rng.choice(["low", "medium", "high", "critical"]),
        "fix": {
            "available_at": _iso(fix_at),
            "description": "Session validation fixed.",
            "fixed_versions": [f"4.{number % 7}.{number % 5 + 1}"],
        },
    }


def ticket_body(rng: random.Random, number: int, base: datetime, *, full: bool, aware=None):
    body = {
        "source": rng.choice(["external_researcher", "customer", "internal", "scanner", "csirt"]),
        "title": f"Perf ticket {number}: authentication bypass",
        "description": "Reporter describes a login bypass using a crafted session cookie. "
        * rng.randint(1, 8),
        "product": {
            "manufacturer": "Acme",
            "name": f"Router OS {number % 12}",
            "affected_versions": [f"4.{number % 7}.0", f"4.{number % 7}.1"],
        },
        "reporter": {"name": f"Reporter {number}", "contact": f"r{number}@example.invalid"},
    }
    if full:
        body.update(_full_fields(rng, number, base, aware))
    return body


def load_size(tickets: int, mix: dict, *, exceed_limit: bool = False) -> int:
    """How many tickets to load so the store holds `tickets` after the measured POSTs
    (or before them, with exceed_limit)."""
    count = tickets if exceed_limit else tickets - mix.get("create", 0)
    if count < 1:
        raise ValueError("--tickets must be larger than the measured POSTs")
    return count


def build_load_specs(seed: int, tickets: int, base: datetime) -> list[dict]:
    """The loaded tickets, in creation order: a pure function of seed, count and the
    service time read at the start. Each spec is the request chain for one ticket."""
    rng = random.Random(f"load-{seed}")
    categories = [
        category
        for category, count in apportion(LOAD_PROFILE, tickets).items()
        for _ in range(count)
    ]
    specs = []
    for number, category in enumerate(categories):
        spec = {"category": category, "triage": None, "submissions": [], "close": False}
        aware = None
        if category in REPORTABLE:
            aware = base - timedelta(hours=rng.randint(2, 20 * 24))
            spec["triage"] = {
                "decision": "actively_exploited",
                "aware_at": _iso(aware),
                "reason": "Customer logs show exploitation.",
            }
        elif category == "not_reportable":
            spec["triage"] = {
                "decision": rng.choice(["not_actively_exploited", "invalid"]),
                "reason": "No sign of exploitation.",
            }
        full = category != "received_min"
        spec["body"] = ticket_body(rng, number, base, full=full, aware=aware)
        if category == "reportable" and rng.random() < 0.3:
            spec["body"].pop("fix")  # final report awaiting a fix
        recorded_at = aware
        for report in RECORDED.get(category, ()):
            # Somewhere between the last recorded report (or awareness) and now, so
            # some reports are on time and some late.
            recorded_at = recorded_at + (base - recorded_at) * rng.random() * 0.5
            spec["submissions"].append(
                {"type": report, "body": {"submitted_at": _iso(recorded_at)}}
            )
        spec["close"] = category == "resolved"
        specs.append(spec)
    return specs


def build_plan(seed: int, mix: dict, category_sizes: dict) -> list[dict]:
    """The measured requests, in order: a pure function of seed, mix and the number of
    loaded tickets in each category. Targets are (category, index-within-category);
    server IDs are filled in at run time. Raises ValueError if a pool is too small."""
    rng = random.Random(f"plan-{seed}")
    available = {category: list(range(size)) for category, size in sorted(category_sizes.items())}
    for indexes in available.values():
        rng.shuffle(indexes)
    reserved = set()

    def take(op):
        for category in MUTATION_POOLS[op]:
            if available.get(category):
                target = (category, available[category].pop())
                reserved.add(target)
                return target
        raise ValueError(f"not enough loaded tickets for {mix[op]} '{op}' requests")

    def pick(op):
        categories = [c for c in READ_POOLS[op] if category_sizes.get(c)]
        if not categories:
            raise ValueError(f"no loaded tickets for '{op}' requests")
        weights = [category_sizes[c] for c in categories]
        category = rng.choices(categories, weights)[0]
        return (category, rng.randrange(category_sizes[category]))

    ops = [op for op, count in mix.items() for _ in range(count)]
    rng.shuffle(ops)
    plan = []
    for position, op in enumerate(ops):
        step = {"op": op}
        if op == "list_state":
            step["query"] = {"state": rng.choice(LIST_STATES)}
        elif op == "list_status":
            step["query"] = {"obligation_status": rng.choice(LIST_STATUSES)}
        elif op in READ_POOLS:
            step["target"] = pick(op)
            if op == "draft":
                step["type"] = rng.choice(DRAFT_TYPES)
        elif op in MUTATION_POOLS:
            step["target"] = take(op)
            if op == "submission":
                category = step["target"][0]
                step["type"] = "early_warning" if category == "reportable" else "notification"
            elif op == "triage":
                step["decision"] = rng.choice(
                    ["actively_exploited", "actively_exploited", "not_actively_exploited"]
                )
                step["aware_hours_ago"] = rng.randint(1, 96)
            elif op == "patch":
                step["severity"] = rng.choice(["low", "medium", "high", "critical"])
        elif op == "create":
            step["full"] = rng.random() < 0.5
        step["number"] = position
        plan.append(step)
    return plan


# ---------------------------------------------------------------- HTTP


def _timed(transport, method, path, body=None, actor=ACTOR):
    started = time.perf_counter()
    try:
        response = transport.send(method, path, body=body, actor=actor)
    except Exception as error:  # timeout, refused, reset: a failure, not a crash
        return None, time.perf_counter() - started, f"{type(error).__name__}"
    return response, time.perf_counter() - started, None


def _call(transport, method, path, expected, body=None, actor=ACTOR):
    response, _, error = _timed(transport, method, path, body, actor)
    status = response.status if response else error
    if status != expected:
        raise SetupError(f"{method} {path.split('?')[0]}: expected {expected}, got {status}")
    return json.loads(response.body) if response.body else None


def _ticket_path(ticket_id: str, suffix: str = "") -> str:
    return "/tickets/" + quote(ticket_id, safe="") + suffix


def load_ticket(transport, spec) -> str:
    ticket = _call(transport, "POST", "/tickets", 201, body=spec["body"])
    ticket_id = ticket["id"]
    if spec["triage"]:
        _call(transport, "POST", _ticket_path(ticket_id, "/triage"), 200, body=spec["triage"])
    for submission in spec["submissions"]:
        path = _ticket_path(ticket_id, f"/reports/{submission['type']}/submission")
        _call(transport, "POST", path, 200, body=submission["body"])
    if spec["close"]:
        _call(transport, "POST", _ticket_path(ticket_id, "/close"), 200)
    return ticket_id


def load_all(transport, specs, workers: int) -> list[str]:
    """Loads every spec, a few at a time; stops at the first failure."""
    pool = ThreadPoolExecutor(workers)
    futures = [pool.submit(load_ticket, transport, spec) for spec in specs]
    try:
        return [future.result() for future in futures]
    finally:
        pool.shutdown(cancel_futures=True)


def run_warmup(transport, count: int) -> list[dict]:
    cycle = [("GET", "/health"), ("GET", "/test/clock"), ("GET", "/tickets")]
    results = []
    for index in range(count):
        method, path = cycle[index % len(cycle)]
        response, seconds, error = _timed(transport, method, path, actor=None)
        results.append(
            {
                "method": method,
                "path": path,
                "status": response.status if response else None,
                "error": error,
                "seconds": seconds,
            }
        )
    return results


def _request_for(step, ids, base, created):
    op = step["op"]
    method, template, expected = OPERATIONS[op]
    body = None
    ticket_id = ids[step["target"]] if "target" in step else None
    if op in ("list", "list_state", "list_status"):
        path = "/tickets" + ("?" + urlencode(step["query"]) if "query" in step else "")
    elif op == "get":
        path = _ticket_path(ticket_id)
    elif op == "patch":
        path = _ticket_path(ticket_id)
        body = {"title": f"Perf update {step['number']}", "severity": step["severity"]}
    elif op == "audit":
        path = _ticket_path(ticket_id, "/audit")
    elif op == "draft":
        path = _ticket_path(ticket_id, f"/reports/{step['type']}")
    elif op == "submission":
        path = _ticket_path(ticket_id, f"/reports/{step['type']}/submission")
        body = {"reference": f"PERF-{step['number']}"}
    elif op == "close":
        path = _ticket_path(ticket_id, "/close")
    elif op == "triage":
        path = _ticket_path(ticket_id, "/triage")
        body = {"decision": step["decision"], "reason": "Measured triage."}
        if step["decision"] == "actively_exploited":
            body["aware_at"] = _iso(base - timedelta(hours=step["aware_hours_ago"]))
    else:  # create
        path = "/tickets"
        rng = random.Random(f"create-{step['number']}")
        body = ticket_body(rng, 100000 + created, base, full=step["full"])
    return method, template, path, expected, body


def run_measured(transport, plan, ids, base, stored, contract=None) -> list[dict]:
    results = []
    created = 0
    for step in plan:
        method, template, path, expected, body = _request_for(step, ids, base, created)
        response, seconds, error = _timed(transport, method, path, body)
        status = response.status if response else None
        problem = error
        if status is not None and status != expected:
            problem = f"expected {expected}, got {status}"
        if problem is None and step["op"] == "create":
            created += 1
        if problem is None and contract is not None:
            # Outside the timer: a fast answer that breaks the contract still fails.
            try:
                parsed = contract.validate(method, template, response)
            except (AssertionError, ValueError) as failure:
                problem = f"schema: {str(failure)[:200]}"
            else:
                if step["op"] == "list" and len(parsed) != stored + created:
                    problem = f"list returned {len(parsed)} tickets, expected {stored + created}"
        results.append(
            {
                "op": step["op"],
                "method": method,
                "path": template,
                "expected_status": expected,
                "status": status,
                "seconds": seconds,
                "ok": problem is None,
                "problem": problem,
            }
        )
    return results


def report(results, warmup, limit=P95_LIMIT_SECONDS) -> dict:
    seconds = [result["seconds"] for result in results]
    by_op = {}
    for result in results:
        by_op.setdefault(result["op"], []).append(result["seconds"])
    failures = [result for result in results if not result["ok"]]
    overall = summarize(seconds)
    warm = [entry["seconds"] for entry in warmup]
    return {
        "overall": overall,
        "per_operation": {
            op: {"method": OPERATIONS[op][0], "path": OPERATIONS[op][1], **summarize(values)}
            for op, values in by_op.items()
        },
        "unexpected": len(failures),
        "failures": [
            {key: f[key] for key in ("op", "method", "path", "status", "problem")} for f in failures
        ],
        "warmup": {
            "requests": warmup,
            "first_seconds": warm[0] if warm else None,
            "max_seconds": max(warm) if warm else None,
            "unexpected": sum(entry["status"] != 200 for entry in warmup),
        },
        "p95_limit_seconds": limit,
        "passed": overall["p95"] <= limit and not failures,
    }


# ---------------------------------------------------------------- CLI


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _now_utc() -> str:
    return datetime.fromtimestamp(time.time(), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ms(value) -> str:
    return f"{value * 1000:8.1f} ms"


def _print_summary(result):
    print(
        f"\nAC-18 against {result['base_url']} ({result['ticket_count_at_start']} tickets "
        f"at the start, {result['ticket_count_at_end']} at the end)"
    )
    warm = result["summary"]["warmup"]
    if warm["requests"]:
        print(
            f"Cold start (untimed warm-up, n={len(warm['requests'])}): first "
            f"{_ms(warm['first_seconds'])}, max {_ms(warm['max_seconds'])}, "
            f"unexpected statuses {warm['unexpected']}"
        )
    overall = result["summary"]["overall"]
    print(
        f"Measured n={overall['n']}: p50 {_ms(overall['p50'])}  p95 {_ms(overall['p95'])}  "
        f"p99 {_ms(overall['p99'])}  max {_ms(overall['max'])}"
    )
    print(f"{'operation':<14}{'request':<44}{'n':>4}{'p50':>12}{'p95':>12}{'max':>12}")
    for op, row in result["summary"]["per_operation"].items():
        request = f"{row['method']} {row['path']}"
        print(
            f"{op:<14}{request:<44}{row['n']:>4}"
            f"{_ms(row['p50']):>12}{_ms(row['p95']):>12}{_ms(row['max']):>12}"
        )
    print(f"Unexpected statuses or responses: {result['summary']['unexpected']}")
    for failure in result["summary"]["failures"][:20]:
        print(f"  {failure['method']} {failure['path']}: {failure['problem']}")
    verdict = "PASS" if result["summary"]["passed"] else "FAIL"
    print(f"{verdict}: p95 {_ms(overall['p95']).strip()} (limit {P95_LIMIT_SECONDS:.0f} s)")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m acceptance.perf", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("--base-url", default=os.environ.get("CRA_BASE_URL"))
    parser.add_argument(
        "--reset",
        action="store_true",
        help="POST /test/reset first: deletes ALL data on the deployment, for every client",
    )
    parser.add_argument("--tickets", type=int, default=1000)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument(
        "--exceed-limit",
        action="store_true",
        help="load the full --tickets; the measured POSTs then take the store past it",
    )
    parser.add_argument("--warmup", type=int, default=5, help="untimed cold-start requests")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--load-workers", type=int, default=4, help="concurrent loaders")
    parser.add_argument(
        "--no-validate", action="store_true", help="skip contract schema checks of responses"
    )
    parser.add_argument(
        "--tested-version", default=os.environ.get("CRA_TESTED_VERSION", "unspecified")
    )
    parser.add_argument("--out", help="write the JSON result here")
    args = parser.parse_args(argv)
    if not args.base_url:
        parser.error("provide --base-url or CRA_BASE_URL")
    if not os.environ.get("CRA_API_TOKEN"):
        parser.error("set CRA_API_TOKEN in the environment")
    if args.tickets < 1 or args.requests < 1 or args.warmup < 0 or args.load_workers < 1:
        parser.error("--tickets, --requests and --load-workers must be positive")
    return args


def run(args) -> int:
    transport = HTTPTransport(args.base_url, os.environ["CRA_API_TOKEN"])
    mix = apportion(MEASURED_MIX, args.requests)
    load_count = load_size(args.tickets, mix, exceed_limit=args.exceed_limit)
    result = {
        "criterion": "AC-18 / REQ-17: p95 <= 1 s over sequential mixed requests",
        "base_url": transport.base_url,
        "tested_version_label": args.tested_version,
        "script_commit": _commit(),
        "started_at": _now_utc(),
        "seed": args.seed,
        "tickets": args.tickets,
        "loaded": load_count,
        "exceed_limit": args.exceed_limit,
        "requests": args.requests,
        "mix": mix,
        "percentile_method": "nearest rank",
        "connection": "new TCP (and TLS for https) connection per request",
        "reset": args.reset,
    }
    try:
        plan = build_plan(args.seed, mix, apportion(LOAD_PROFILE, load_count))
        print(f"Target: {transport.base_url}")
        print(f"Warm-up: {args.warmup} untimed requests")
        warmup = run_warmup(transport, args.warmup)
        if args.reset:
            print("Resetting the WHOLE deployment (POST /test/reset): every client's data")
            _call(transport, "POST", "/test/reset", 204, actor=None)
        existing = _call(transport, "GET", "/tickets", 200, actor=None)
        if existing:
            raise SetupError(
                f"the deployment already holds {len(existing)} tickets; use an empty "
                "deployment or pass --reset (deletes everything)"
            )
        clock = _call(transport, "GET", "/test/clock", 200, actor=None)["now"]
        base = datetime.fromisoformat(clock.replace("Z", "+00:00"))
        result["service_clock_at_start"] = clock
        specs = build_load_specs(args.seed, load_count, base)
        print(f"Loading {load_count} tickets ({args.load_workers} at a time, not timed)...")
        load_started = time.perf_counter()
        loaded = load_all(transport, specs, args.load_workers)
        result["load_seconds"] = round(time.perf_counter() - load_started, 1)
        ids, seen = {}, {}
        for spec, ticket_id in zip(specs, loaded, strict=True):
            index = seen.get(spec["category"], 0)
            ids[(spec["category"], index)] = ticket_id
            seen[spec["category"]] = index + 1
        stored = len(_call(transport, "GET", "/tickets", 200, actor=None))
        result["ticket_count_at_start"] = stored
        result["ticket_count_at_end"] = stored + mix.get("create", 0)
        print(f"Loaded in {result['load_seconds']} s; {stored} tickets stored.")
        print(f"Measuring {args.requests} requests, one at a time...")
        contract = None if args.no_validate else Contract()
        measured = run_measured(transport, plan, ids, base, stored, contract)
    except SetupError as error:
        result["error"] = str(error)
        print(f"Not measured: {error}", file=sys.stderr)
        _write(args.out, result)
        return 2
    result["finished_at"] = _now_utc()
    result["summary"] = report(measured, warmup)
    result["results"] = measured
    _write(args.out, result)
    _print_summary(result)
    print(
        "The deployment still holds the loaded tickets. A final POST /test/reset is the "
        "operator's call. The script did not set the test clock."
    )
    return 0 if result["summary"]["passed"] else 1


def _write(destination, result):
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except ValueError as error:  # a bad base URL or a pool too small for the mix
        print(f"Not measured: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
