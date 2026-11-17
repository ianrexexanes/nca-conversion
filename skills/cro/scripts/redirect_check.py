#!/usr/bin/env python3
"""Redirect check: each redirect followed hop by hop, then judged. Python 3 stdlib only.

    redirect_check.py --cases FILE.json

FILE.json is a list of {"from": url, "to": url, "status": int, "hops": [int] | absent}. Every hop is fetched with the ordinary
Chrome agent page_facts.CHROME_UA. The chain ends at `to` with `status`; unless `hops` lists the status of every hop, each
earlier hop is a 301. More than five redirects, or an end that is not HTTPS, fails. Lines are `<FAIL> <from> <RULE>: <detail>`,
then `redirect_check: <f> FAIL, <w> WARN`. Exit 1 on any FAIL, 2 on bad input.
"""
import http.client
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_check import BadInput, Parser, finish  # noqa: E402  (puts conversion-page-audit/scripts on the path)
from page_facts import CHROME_UA  # noqa: E402

MAX_REDIRECTS = 5


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def follow(url: str, max_hops: int = MAX_REDIRECTS) -> list:
    """[(url, status)] for each hop. It stops at the first answer that is not a redirect, or after the redirect past
    `max_hops` (so judge() can see the limit was broken), or at a hop whose Location cannot be parsed; status 0 means no answer."""
    hops = []
    while True:
        if urllib.parse.urlparse(url).scheme not in ("http", "https"):  # never open ftp:, file: or the like
            hops.append((url, 0))
            return hops
        request = urllib.request.Request(url, headers={"User-Agent": CHROME_UA, "Accept": "text/html,*/*;q=0.8"})
        try:
            with _OPENER.open(request, timeout=20) as response:
                status, location = response.status, None
        except urllib.error.HTTPError as error:
            status, location = error.code, error.headers.get("Location")
            error.close()
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException):
            hops.append((url, 0))
            return hops
        hops.append((url, status))
        redirects = sum(1 for _, s in hops if 300 <= s < 400)
        if not (300 <= status < 400 and location) or redirects > max_hops:
            return hops
        try:
            url = urllib.parse.urljoin(url, location)
        except ValueError:  # a Location that cannot be parsed ends the chain at the hop that answered
            return hops


def judge(case: dict, hops: list) -> list:
    """(level, rule, detail) for each rule the chain breaks."""
    out = []
    last_url, last_status = hops[-1]
    statuses = [s for _, s in hops]
    if last_url != case["to"]:
        out.append(("FAIL", "REDIRECT_TARGET", "the chain ends at %s, not %s" % (last_url, case["to"])))
    if last_status != case["status"]:
        detail = "the last answer is %d, not %d" % (last_status, case["status"])
        if 300 <= case["status"] < 400:
            detail += "; status is the final answer's status at \"to\" (usually 200), not the redirect's"
        out.append(("FAIL", "REDIRECT_STATUS", detail))
    if case.get("hops") is not None:
        if statuses != case["hops"]:
            out.append(("FAIL", "REDIRECT_STATUS", "the hops answered %s, not %s" % (statuses, case["hops"])))
    elif any(s != 301 for s in statuses[:-1]):
        out.append(("FAIL", "REDIRECT_STATUS", "a hop before the last is not a 301: %s" % statuses))
    redirects = sum(1 for s in statuses if 300 <= s < 400)
    if redirects > MAX_REDIRECTS:
        out.append(("FAIL", "REDIRECT_HOPS", "%d redirects; the limit is %d" % (redirects, MAX_REDIRECTS)))
    if urllib.parse.urlparse(last_url).scheme != "https":
        out.append(("FAIL", "REDIRECT_HTTPS", "the chain ends at %s, which is not HTTPS" % last_url))
    return out


def load_cases(path):
    try:
        cases = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BadInput("cannot read %s as JSON" % path)
    ok = isinstance(cases, list) and cases
    for case in cases if ok else []:
        ok = ok and isinstance(case, dict) and isinstance(case.get("from"), str) and isinstance(case.get("to"), str) \
            and isinstance(case.get("status"), int) and not isinstance(case.get("status"), bool) \
            and (case.get("hops") is None or (isinstance(case["hops"], list) and all(isinstance(s, int) for s in case["hops"])))
    if not ok:
        raise BadInput('%s must be a list of {"from": url, "to": url, "status": int, "hops": [int] (optional)}' % path)
    for case in cases:
        try:
            urllib.parse.urlparse(case["from"])
        except ValueError:
            raise BadInput("cannot read the from address %s" % case["from"])
    return cases


def main(argv=None):
    parser = Parser(prog="redirect_check", description="Follow each redirect hop by hop and judge the chain.")
    parser.add_argument("--cases", required=True, metavar="FILE.json")
    args = parser.parse_args(argv)
    try:
        cases = load_cases(args.cases)
    except BadInput as error:
        print("redirect_check: %s" % error, file=sys.stderr)
        return 2
    rows = []
    for case in cases:
        rows += [(level, case["from"], rule, detail) for level, rule, detail in judge(case, follow(case["from"]))]
    return finish("redirect_check", rows)


if __name__ == "__main__":
    sys.exit(main())
