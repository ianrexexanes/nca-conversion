"""Make one Microsoft Clarity Data Export call, inside a local daily budget, with the token kept out of every output.

    clarity_export.py --project NAME --days 1|2|3 [--dimension D]... [--out FILE] [--data-dir DIR] [--token-file PATH]

The token is read by cro_runtime.clarity_token() and travels only in the Authorization header of the one request.
No exception text, response body, URL or token is printed or written: a failure becomes a fixed reason string.
No redirect is followed. Exit 0 with data, or with a reason when no token is found; 2 on bad input;
3 when the call fails; 4 when the local budget refuses it.
"""
import argparse
import hashlib
import http.client
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cro_runtime  # noqa: E402

ENDPOINT = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
DIMENSIONS = ("Browser", "Device", "Country/Region", "OS", "Source", "Medium", "Campaign", "Channel", "URL")
DAILY_LIMIT = 10
ROW_LIMIT = 1000
LOOPBACK = ("127.0.0.1", "::1", "localhost")
HTTP_REASONS = {
    400: "bad parameters",
    401: "the token is missing, invalid or expired",
    403: "the token is not authorised for this project",
    429: "the Clarity daily limit is spent (ten requests per project per day)",
}


class Refused(Exception):
    """Carries only a fixed reason string."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def loopback_endpoint(url):
    try:
        parts = urllib.parse.urlsplit(url)
        return (parts.scheme in ("http", "https") and parts.hostname in LOOPBACK
                and "@" not in parts.netloc and "\\" not in parts.netloc)
    except ValueError:
        return False


def usable(token):
    return all(0x21 <= ord(c) <= 0x7E for c in token)


def budget_key(label, token_file, project):
    if label == "token-file":
        where = str(Path(token_file).expanduser().resolve())
    elif label == "env":
        where = cro_runtime.CLARITY_ENV
    else:
        where = str(cro_runtime.CLARITY_FILE)
    return hashlib.sha256(f"{label}:{where}:{project}".encode()).hexdigest()[:16]


def read_budget(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def take_one(path, key):
    """Count this request for today (UTC) and save before it is sent; Refused when the budget is spent."""
    today = datetime.now(timezone.utc).date().isoformat()
    budget = read_budget(path)
    entry = budget.get(key)
    count = entry.get("count") if isinstance(entry, dict) and entry.get("day") == today else 0
    if not isinstance(count, int) or isinstance(count, bool):
        count = 0
    if count >= DAILY_LIMIT:
        raise Refused("the local budget for this token and project is spent for the UTC day; the API allows ten requests per project per day")
    budget[key] = {"day": today, "count": count + 1}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".clarity-budget-")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(budget, handle)
        os.replace(temp, path)
    except OSError:
        raise Refused("the local budget file cannot be written, so nothing was sent") from None


def fetch(url, token, loopback):
    handlers = [NoRedirect()]
    if loopback:
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with opener.open(request, timeout=60) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        code = error.code
        if 300 <= code < 400:
            raise Refused(f"HTTP {code}: the export address answered with a redirect, which is not followed") from None
        raise Refused(f"HTTP {code}: " + HTTP_REASONS.get(code, "refused")) from None
    except (OSError, http.client.HTTPException):
        raise Refused("the export address could not be reached") from None
    except ValueError:
        raise Refused("the token was not sent because it cannot be used in a header") from None
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    if not isinstance(data, list) or not all(
            isinstance(item, dict) and isinstance(item.get("metricName"), str) and isinstance(item.get("information"), list)
            for item in data):
        raise Refused("the answer was not a list of metrics with rows")
    metrics = {}
    for item in data:
        metrics.setdefault(item["metricName"], []).extend(item["information"])
    return metrics


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="clarity_export.py", description="One Clarity Data Export call, inside a local daily budget.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--days", type=int, required=True, help="1, 2 or 3 (the last 24, 48 or 72 hours)")
    parser.add_argument("--dimension", action="append", default=[], help="up to three of: " + ", ".join(DIMENSIONS))
    parser.add_argument("--out", metavar="FILE")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument("--endpoint", default=None, help="test override: replaces the export address; loopback hosts only")
    return parser, parser.parse_args(argv)


def invalid(args):
    if not args.project.strip():
        return "--project is blank"
    if args.days not in (1, 2, 3):
        return "--days must be 1, 2 or 3"
    if len(args.dimension) > 3:
        return "at most three --dimension"
    for name in args.dimension:
        if name not in DIMENSIONS:
            return "unknown --dimension; use one of " + ", ".join(DIMENSIONS)
    if len(set(args.dimension)) != len(args.dimension):
        return "a --dimension is repeated"
    if args.endpoint is not None and not loopback_endpoint(args.endpoint):
        return "--endpoint is a test override for loopback hosts only"
    return None


def main(argv=None) -> int:
    try:
        parser, args = parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else 2
    reason = invalid(args)
    if reason:
        print("clarity_export: " + reason, file=sys.stderr)
        return 2
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            print("clarity_export: cannot create the folder for --out " + args.out, file=sys.stderr)
            return 2
    project = args.project.strip()
    result = {"project": project, "checked_at": None, "days": args.days, "dimensions": list(args.dimension),
              "source": "clarity", "metrics": {}, "truncated": False, "reason": None}
    code = 0
    try:
        token, label = cro_runtime.clarity_token(args.token_file)
        if not token:
            result["reason"] = ("no Clarity token found: set NCA_CLARITY_TOKEN, save it in ~/.config/nca-conversion/clarity.token, "
                                "or pass --token-file; setup.md shows how")
        elif not usable(token):
            raise Refused("the token holds a space or a control character, so it was not sent; nothing was counted")
        else:
            data_dir = args.data_dir if args.data_dir is not None else cro_runtime.default_data_dir()
            try:
                take_one(Path(data_dir) / "clarity-budget.json", budget_key(label, args.token_file, project))
            except Refused as spent:
                code = 4
                raise spent
            query = [("numOfDays", args.days)] + [(f"dimension{i}", name) for i, name in enumerate(args.dimension, 1)]
            base = args.endpoint if args.endpoint is not None else ENDPOINT
            metrics = fetch(base + "?" + urllib.parse.urlencode(query), token, args.endpoint is not None)
            result["metrics"] = metrics
            result["truncated"] = any(len(rows) >= ROW_LIMIT for rows in metrics.values())
    except Refused as failure:
        result["reason"] = str(failure)
        code = code or 3
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    text = json.dumps(result, indent=2)
    if not args.out:
        print(text)
        return code
    try:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    except OSError:
        print("clarity_export: cannot write --out " + args.out, file=sys.stderr)
        return 2
    if result["reason"]:
        print(f"clarity_export: wrote {args.out}: {result['reason']}")
    else:
        rows = sum(len(r) for r in result["metrics"].values())
        print(f"clarity_export: wrote {args.out}: {len(result['metrics'])} metrics, {rows} rows" + (", truncated" if result["truncated"] else ""))
    return code


if __name__ == "__main__":
    sys.exit(main())
