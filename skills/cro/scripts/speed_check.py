"""Measure a page's speed: PageSpeed Insights with a key, else local Lighthouse, else nothing.

    speed_check.py URL [--strategy mobile|desktop|both] [--out FILE]

One source per run, so every number in a result comes from the same place. The key is read by
cro_runtime.pagespeed_key() and travels only in the X-Goog-Api-Key header. No exception text,
stderr text or URL is ever printed or written: a failure becomes a fixed reason string.
Exit 0 whether the page was measured or not, 2 on bad arguments or when --out cannot be written.
"""
import argparse
import datetime
import http.client
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cro_runtime  # noqa: E402

LIGHTHOUSE_VERSION = "13.6.0"
ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
LABELS = {"pagespeed": "PageSpeed Insights", "lighthouse-lab": "lab data", "none": "could not check"}


class Failure(Exception):
    """Carries only a fixed reason string."""


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _audit(audits, name):
    audit = audits.get(name) if isinstance(audits, dict) else None
    return _number(audit.get("numericValue")) if isinstance(audit, dict) else None


def _scaled(value, divisor, digits):
    return None if value is None else round(value / divisor, digits)


def lab_values(categories, audits):
    score = _number(categories["performance"].get("score"))
    tbt = _audit(audits, "total-blocking-time")
    return {
        "performance": None if score is None else round(score * 100),
        "lcp_s": _scaled(_audit(audits, "largest-contentful-paint"), 1000, 1),
        "cls": None if _audit(audits, "cumulative-layout-shift") is None
        else round(_audit(audits, "cumulative-layout-shift"), 2),
        "tbt_ms": None if tbt is None else round(tbt),
    }


def field_values(experience):
    if not isinstance(experience, dict) or experience.get("origin_fallback"):
        return None
    metrics = experience.get("metrics")
    if not isinstance(metrics, dict):
        return None
    names = ("LARGEST_CONTENTFUL_PAINT_MS", "INTERACTION_TO_NEXT_PAINT", "CUMULATIVE_LAYOUT_SHIFT_SCORE")

    def percentile(name):
        metric = metrics.get(name)
        return _number(metric.get("percentile")) if isinstance(metric, dict) else None

    if all(percentile(name) is None for name in names):
        return None
    return {
        "lcp_s": _scaled(percentile(names[0]), 1000, 1),
        "inp_ms": percentile(names[1]),
        "cls": _scaled(percentile(names[2]), 100, 2),
    }


def pagespeed(url, strategy, key):
    query = urllib.parse.urlencode({"url": url, "strategy": strategy.upper(), "category": "PERFORMANCE"})
    request = urllib.request.Request(ENDPOINT + "?" + query, headers={"X-Goog-Api-Key": key})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise Failure("pagespeed quota" if error.code == 429 else "pagespeed refused") from None
    except (OSError, http.client.HTTPException):
        raise Failure("pagespeed unreachable") from None
    try:
        data = json.loads(body)
        result = data["lighthouseResult"]
        values = lab_values(result["categories"], result.get("audits"))
        values["field"] = field_values(data.get("loadingExperience"))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise Failure("pagespeed bad response") from None
    return values


def host_rules():
    return ", ".join("MAP %s ~NOTFOUND, MAP *.%s ~NOTFOUND" % (s, s) for s in cro_runtime.BLOCKED_HOSTS)


def lighthouse_command(url, strategy):
    args = ["npx", "--yes", "lighthouse@" + LIGHTHOUSE_VERSION, url, "--output=json", "--output-path=stdout",
            "--quiet", "--only-categories=performance",
            '--chrome-flags=--headless=new --host-resolver-rules="%s"' % host_rules(),
            "--skip-audits=bf-cache"]
    if strategy == "desktop":
        args.append("--preset=desktop")
    return args + ["--blocked-url-patterns=" + glob for glob in cro_runtime.lighthouse_block_patterns()]


def lighthouse(url, strategy):
    try:
        done = subprocess.run(lighthouse_command(url, strategy), capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise Failure("lighthouse timed out") from None
    except OSError:
        raise Failure("lighthouse missing") from None
    if done.returncode != 0:
        raise Failure("lighthouse exited %d" % done.returncode)
    try:
        report = json.loads(done.stdout)
        values = lab_values(report["categories"], report.get("audits"))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise Failure("lighthouse bad output") from None
    values["field"] = None
    return values


def measure(url, strategies):
    reasons = []
    key, _source = cro_runtime.pagespeed_key()
    if key:
        try:
            return "pagespeed", {s: pagespeed(url, s, key) for s in strategies}, None
        except Failure as failure:
            reasons.append(str(failure))
    else:
        reasons.append("pagespeed key missing")
    try:
        return "lighthouse-lab", {s: lighthouse(url, s) for s in strategies}, "; ".join(reasons)
    except Failure as failure:
        reasons.append(str(failure))
    return "none", {}, "; ".join(reasons)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="speed_check.py", description="Measure a page's speed.")
    parser.add_argument("url")
    parser.add_argument("--strategy", choices=("mobile", "desktop", "both"), default="both")
    parser.add_argument("--out", metavar="FILE")
    args = parser.parse_args(argv)
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            parser.error("cannot create the folder for --out " + args.out)
    strategies = ("mobile", "desktop") if args.strategy == "both" else (args.strategy,)
    source, results, reason = measure(args.url, strategies)
    text = json.dumps({
        "url": args.url,
        "checked_at": datetime.date.today().isoformat(),
        "source": source,
        "label": LABELS[source],
        "results": results,
        "reason": reason,
    }, indent=2)
    print(text)
    if args.out:
        try:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        except OSError:
            print("speed_check: cannot write --out " + args.out, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
