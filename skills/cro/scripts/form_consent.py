"""Send one real, labelled test submission through a form, once, with the owner's yes. The only script in the plugin that sends.

Run by the plugin's venv python, and only after the owner has said yes for this test:
    form_consent.py URL --out DIR --owner NAME --date YYYY-MM-DD --email ADDRESS [--form CSS] [--timeout 45]

Before any browser opens it exits 2 when --owner is empty, --date is not a real date or not today's local date, or --email
is not one address with a dot after the @. The page loads through a guarded Recorder with no host, so nothing the page
sends while it loads, is read or is filled can take the send. The script finds the one form and its action host, refuses a form
that submits by GET (the guard counts only non-GET requests), fills it (the address in its email field, "Test submission,
consented by <owner>, <date>" in the other text fields), and only then sets the Recorder's allow_post_host to that host and
presses submit once, timing the press to the thank-you state. The guard lets exactly one non-GET request leave, to that host; a
second is aborted. Afterwards the consented request must be to the form's own action (or the pressed control's formaction), and no
non-GET request may show as completed, which is what a 307 or 308 redirect hop looks like; either is a FAIL SEND, exit 1. A form
that sends anywhere else, or by GET, is SKIPPED and exit 3, with nothing sent. So is a form whose own validation refuses the fill. Claude Code asks before every run: no allow rule covers this script.
Exit 0 when the send went through, 1 on a FAIL, 2 on bad input, 3 when nothing was sent. The browser is closed last, with
browser.close() alone.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cro_runtime  # noqa: E402
import form_check  # noqa: E402
from form_check import (BadInput, Parser, Unreadable, add_issue, count_issues, first_line, load, new_doc,  # noqa: E402
                        new_entry, open_view, press, read_forms, select_forms, snap_form, write_outputs)

EMAIL = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
NON_GET = ("GET", "HEAD", "OPTIONS")
WAIT_MS = 30000
GIVE_UP_MS = 2000


def parse_args(argv):
    parser = Parser(prog="form_consent", description="Send one labelled test submission with the owner's yes.")
    parser.add_argument("url")
    parser.add_argument("--out", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--form")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args(argv)
    args.owner = args.owner.strip()
    if not args.owner:
        raise BadInput("--owner is empty; the consent line needs the owner's name")
    if re.search(r"[\x00-\x1f\x7f]", args.owner):
        raise BadInput("--owner holds a control character")
    if not DATE.fullmatch(args.date):
        raise BadInput("--date must be YYYY-MM-DD, got %r" % args.date)
    try:
        date.fromisoformat(args.date)
    except ValueError:
        raise BadInput("--date %s is not a real date" % args.date)
    if args.date != date.today().isoformat():
        raise BadInput("--date must be today's date (%s), the day the owner said yes; got %s" % (date.today().isoformat(), args.date))
    if not EMAIL.fullmatch(args.email):
        raise BadInput("--email must be one address with a dot after the @, got %r" % args.email)
    form_check.check_address(args.url)
    if args.timeout <= 0:
        raise BadInput("--timeout must be positive")
    form_check.make_out_dir(args.out)
    return args


def consent_page(browser, recorder, major):
    """The sending context and page: the guard's own, with the Recorder that lets one POST reach the action host."""
    width, height, mobile = form_check.DESKTOP
    context = cro_runtime.guarded_context(browser, recorder, major=major, width=width, height=height,
                                          mobile=mobile, reduced_motion="reduce")
    return cro_runtime.guarded_page(context, recorder)


def host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def run_consent(args, browser, major, session, doc, out_dir, timeout_ms):
    """Returns True when the form itself was sent, False when nothing was sent (SKIPPED) or the send went wrong (FAIL)."""
    line = "Test submission, consented by %s, %s" % (args.owner, args.date)
    # The sending Recorder starts with no host, so nothing the page sends while it loads, is read or is filled can take the send.
    sender = cro_runtime.Recorder()
    session.recorders.append(sender)
    page = consent_page(browser, sender, major)
    load(page, args.url, timeout_ms)
    info = select_forms(read_forms(page, args.form), args.form, True)[0]
    control = info["submit"]
    action = control["formaction"] or info["action"]
    host = host_of(action)
    if not host or not action.lower().startswith(("http://", "https://")):
        raise Unreadable("the form's action is not an http or https address: %s" % action)
    entry = new_entry(info)
    doc["forms"] = [entry]
    if info["method"] == "get" or control["formmethod"] == "get":
        if info["has_method"] or control["formmethod"] == "get":
            why = "this form submits by GET"
        else:
            why = "this form has no method, so a plain submission would go by GET"
        add_issue(entry, "SKIPPED", "SEND", why + ", which the guard can neither count nor limit; nothing was sent")
        return False
    entry["filled"] = form_check.apply_plan(page, info["i"], form_check.plan_fill(info["fields"], line, args.email))
    problems = form_check.fill_problems(page, info["i"])
    if problems:
        entry["submit"]["validation"] = problems
        for p in problems:
            print("not sent: the fill does not satisfy %s (%s)" % (p["field"], p["message"]))
        add_issue(entry, "SKIPPED", "SEND", "the fill does not satisfy %s; nothing was sent" % ", ".join(p["field"] for p in problems))
        return False
    sender.allow_post_marker = args.email  # only a request that carries the typed address can take the send
    sender.allow_post_host = host  # open the consent now, for the press alone
    mark = len(sender.entries)

    def stop(elapsed):
        posts = [e for e in sender.entries[mark:] if e["method"] not in NON_GET]
        sent = any(e["outcome"] == "consented" for e in posts)
        return not sent and any(e["outcome"] == "blocked" for e in posts) and elapsed >= GIVE_UP_MS

    entry["submit"], text = press(page, info["i"], info, WAIT_MS, stop)
    entry["thank_you"]["text"] = text
    if entry["submit"]["state"] == "navigated":
        entry["thank_you"]["url"] = page.url
    snap_form(page, info["i"], out_dir / ("form%d-consented.png" % entry["index"]))
    page.wait_for_timeout(500)
    sender.finish()

    after = sender.entries[mark:]
    sent = [e for e in after if e["outcome"] == "consented"]
    ours = {a for a in (form_check.address(info["action"]), form_check.address(action)) if a}
    ok = True
    sent_at = after.index(sent[0]) if sent else len(after)
    for n, e in enumerate(after):
        if e["method"] not in NON_GET and e["outcome"] == "completed":
            add_issue(entry, "FAIL", "SEND", "a second %s reached %s by a redirect the guard cannot see" % (e["method"], e["url"]))
            ok = False
        elif n < sent_at or (n > sent_at and e["method"] not in ("GET", "HEAD")):
            # a GET after the consented entry is the page's follow-up (a post-redirect-get, the thank-you load), not a second send
            if e["outcome"] != "blocked" and form_check.address(e["url"]) in ours and e["resource_type"] != "websocket":
                add_issue(entry, "FAIL", "SEND", "a %s request to the action address %s went out besides the consented send"
                          % (e["method"], e["url"]))
                ok = False
    if not sent:
        posts = [e for e in after if e["method"] not in NON_GET and e["outcome"] == "blocked"]
        if not posts:
            add_issue(entry, "SKIPPED", "SEND", "the press sent nothing to %s; nothing was sent. The form may need a field this test "
                      "data does not fill" % host)
        elif posts[0]["rule"] == "consent:no-marker":
            add_issue(entry, "SKIPPED", "SEND", "no request to %s carried the address typed into the form; nothing was sent" % host)
        elif posts[0]["rule"] == "consent:used":
            add_issue(entry, "SKIPPED", "SEND", "the single send was already used before this request; nothing more was sent")
        elif host_of(posts[0]["url"]) == host:
            add_issue(entry, "SKIPPED", "SEND", "the guard blocks %s (%s), so nothing was sent" % (host, posts[0]["rule"]))
        else:
            add_issue(entry, "SKIPPED", "SEND", "the form sent to %s, not to its action host %s, so nothing was sent"
                      % (host_of(posts[0]["url"]) or posts[0]["url"], host))
        return False
    if form_check.address(sent[0]["url"]) not in ours:
        aborted = [e for e in after if e["rule"] == "consent:used" and form_check.address(e["url"]) in ours]
        if aborted:
            add_issue(entry, "FAIL", "SEND", "the request to %s took the single send and the form's own request was aborted, so the "
                      "form itself was not sent" % sent[0]["url"])
            return False
        add_issue(entry, "WARN", "SEND", "the one consented request went to %s, not to the form's action address %s, most likely the "
                  "page's script sending the form there; check that the test lead arrived before any rerun" % (sent[0]["url"], action))
        return True
    status = sent[0]["status"]
    if status is not None and status >= 400:
        add_issue(entry, "FAIL", "SEND", "the action host %s answered HTTP %d" % (host, status))
    return ok


def main(argv=None):
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except BadInput as error:
        print("form_consent: %s" % error, file=sys.stderr)
        return 2
    if form_check.sync_playwright is None:
        print("form_consent: Playwright is not installed; run setup.py", file=sys.stderr)
        return 3
    out_dir = Path(args.out)
    doc = new_doc(args.url, "consented")
    doc["consent"] = "%s, %s" % (args.owner, args.date)
    session = form_check.Session()
    code = 0
    sent_ok = True
    playwright = form_check.sync_playwright().start()
    browser = None
    try:
        try:
            browser = cro_runtime.guarded_launch(playwright)
            major = int(browser.version.split(".")[0])
            doc["user_agent"] = cro_runtime.chrome_ua(major)
            sent_ok = run_consent(args, browser, major, session, doc, out_dir, int(args.timeout * 1000))
        except Unreadable as error:
            print("form_consent: %s" % error, file=sys.stderr)
            code = 3
        except form_check.PlaywrightError as error:
            print("form_consent: the page could not be read: %s" % first_line(error), file=sys.stderr)
            code = 3
        lines, fails, warns = count_issues(doc)
        if not sent_ok and not fails and not code:
            code = 3
        write_outputs(out_dir, doc, session)
    finally:
        if browser is not None:
            try:
                browser.close()
            except form_check.PlaywrightError:
                pass
        playwright.stop()
    for text in lines:
        print(text)
    print("form_consent: %d FAIL, %d WARN" % (fails, warns))
    if code:
        return code
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
