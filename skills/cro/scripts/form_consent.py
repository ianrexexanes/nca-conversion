"""Send one real, labelled test submission through a form, once, with the owner's yes. The only script in the plugin that sends.

Run by the owner in a terminal, with the plugin's venv python, and only after the owner has said yes for this test:
    form_consent.py URL --out DIR --owner NAME --date YYYY-MM-DD --email ADDRESS [--form CSS] [--timeout 45]

Before any browser opens it exits 2 when --owner is empty, --date is not a real date or not today's local date, or --email
is not one address with a dot after the @. The page loads through a guarded Recorder with no host, so nothing the page
sends while it loads, is read or is filled can take the send. The script finds the one form and its action host, refuses a form
that submits by GET (the guard counts only non-GET requests), fills it (the address in its email field, "Test submission,
consented by <owner>, <date>" in the other text fields), and only then sets the Recorder's allow_post_host to that host and
presses submit once, timing the press to the thank-you state. After the press it waits for the form's host to answer, closes the consent, and only then judges the send; a send the host has not answered by the end of the wait is a WARN. So is a page that cannot be read after the press when the request has left: the thank-you state is not known, so check that the test lead arrived before any rerun. A failure of the script after the consent was opened prints a line on standard error to the same effect. The guard lets exactly one non-GET request leave the page, to that host; a
second is aborted. A resend inside the browser's network stack after a connection that closed with no answer is below the guard: it is
reported afterwards (a FAIL SEND for a host that ended the connection), like the redirect that keeps the method. Afterwards the consented request must be to the form's own action (or the pressed control's formaction), and no
non-GET request may show as completed, which is what a 307 or 308 redirect hop looks like; either is a FAIL SEND, exit 1. A form
that sends anywhere else, or by GET, is SKIPPED and exit 3, with nothing sent. So is a form whose own validation refuses the fill. The yes in the chat comes first, as `form.md` step 7 says. Then, unless the action host is loopback (127.0.0.1, ::1 or localhost), the script asks at the terminal before it opens the consent: it prints the action host and goes on only when that host is typed back on standard input. With no terminal on standard input, or any other answer, the form is SKIPPED and exit 3, with nothing sent. No flag, variable or file answers for the terminal.
Exit 0 when the send went through, 1 on a FAIL, 2 on bad input, 3 when nothing was sent. The browser is closed last, with
browser.close() alone.
"""
import argparse
import re
import sys
import time
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
WAIT_MS = 30000
POST_WAIT_MS = 10000
GIVE_UP_MS = 2000
LOOPBACK = ("127.0.0.1", "::1", "localhost")


def ask_host(host, url):
    """The host a person types at the terminal, or None when there is no terminal on standard input (nothing is written then).
    A terminal that fails on the read, or Ctrl-C at the question, counts as nothing typed."""
    try:
        if sys.stdin is None or not sys.stdin.isatty():
            return None
    except (AttributeError, ValueError, OSError):
        return None
    sys.stderr.write("form_consent: this sends one real test submission to %s, through the form on %s.\n" % (host, url))
    sys.stderr.write("Type %s to send it, or press Enter to stop: " % host)
    sys.stderr.flush()
    try:
        return sys.stdin.readline().strip().lower()
    except (OSError, UnicodeError):
        return ""
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        return ""


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
    if host not in LOOPBACK:
        typed = ask_host(host, args.url)
        if typed != host:
            why = ("a send to %s needs a person at a terminal: run this command yourself in a terminal and type the host when asked; nothing was sent" % host
                   if typed is None else "the host typed at the terminal was not %s; nothing was sent" % host)
            add_issue(entry, "SKIPPED", "SEND", why)
            return False
    sender.allow_post_marker = args.email  # only a request that carries the typed address can take the send
    sender.allow_post_host = host  # open the consent now, for the press alone
    session.consent_opened = True  # for main: a send may have left if the script fails from here on
    page_error = None
    held = False  # a document request made since the press was still in flight when the wait ended
    kept = {}  # press hands its submit block here, so a page lost inside it still leaves the block
    mark = len(sender.entries)
    try:

        def stop(elapsed):
            posts = [e for e in sender.entries[mark:] if e["method"] not in cro_runtime.ALLOWED_METHODS]
            sent = any(e["outcome"] == "consented" for e in posts)
            if any(e["outcome"] == "consented" and "failure" in e for e in posts):
                return True  # the form's host ended the connection: no answer is coming
            return not sent and any(e["outcome"] == "blocked" for e in posts) and elapsed >= GIVE_UP_MS

        pressed_at = time.monotonic()
        waited = lambda: (time.monotonic() - pressed_at) * 1000  # noqa: E731
        posts = lambda: [e for e in sender.entries[mark:] if e["method"] not in cro_runtime.ALLOWED_METHODS]  # noqa: E731
        in_flight = lambda: any(e["resource_type"] == "document" and e["status"] is None and e["outcome"] in (None, "consented")  # noqa: E731
                                and "failure" not in e for e in sender.entries[mark:])
        entry["submit"], text = press(page, info["i"], info, WAIT_MS, stop, into=kept, hold=in_flight)
        submit = entry["submit"]
        # wait for the form's host to answer before anything is judged: first for a late request, then for its answer
        pressed_back = waited()
        own = lambda: [e for e in posts() if host_of(e["url"]) == host]  # noqa: E731  (a request elsewhere is not the form's)
        while submit["state"] != "navigated" and not own() and waited() - pressed_back < POST_WAIT_MS:
            page.wait_for_timeout(100)
        while any(e["outcome"] == "consented" and e["status"] is None and "failure" not in e for e in posts()) and waited() < WAIT_MS:
            page.wait_for_timeout(100)
        sender.allow_post_host = None  # the consent is closed: a later request of the page is aborted like any other
        held = in_flight()  # while one is in flight the page's calls wait for it: the page is not asked
        if not held and submit["state"] == "changed" and any(e["outcome"] == "consented" and e["status"] is not None for e in posts()):
            # read the page again after the answer: it may have moved on to a thank-you page, which is mid-load while no snapshot reads
            now, looked = None, waited()
            while now is None and waited() - looked < 3000:
                now = form_check.safe_eval(page, form_check.SNAPSHOT, info["i"], None)
                if now is None:
                    page.wait_for_timeout(100)
            if now is not None:
                submit["state"], submit["time_ms"] = form_check.wait_for_state(
                    page, info["i"], None, pressed_at, waited() + 3000, resume=((now["form"], now["regions"]), submit["time_ms"]))
                text = form_check.read_outcome(page, info["i"], submit)
        if not page.url.startswith("chrome-error://"):  # the browser's own error page is not the form's thank-you step
            entry["thank_you"]["text"] = text
            if entry["submit"]["state"] == "navigated":
                entry["thank_you"]["url"] = page.url
        if not held:
            snap_form(page, info["i"], out_dir / ("form%d-consented.png" % entry["index"]))
        page.wait_for_timeout(500)
    except form_check.PlaywrightError as error:
        entry["submit"] = kept.get("submit", entry["submit"])  # the press may have been made before the page was lost
        page_error = error  # the page cannot be read any more; what was sent is judged from the recorder
    finally:
        sender.allow_post_host = None
    sender.finish()

    after = sender.entries[mark:]
    sent = [e for e in after if e["outcome"] == "consented"]
    if page_error is not None and sent:
        add_issue(entry, "WARN", "SEND", "the page could not be read after the press (%s), so the thank-you state is not known%s; check that "
                  "the test lead arrived before any rerun" % (first_line(page_error), "" if sent[0]["status"] is not None
                                                              else "; the form's host had not answered yet"))
    ours = {a for a in (form_check.address(info["action"]), form_check.address(action)) if a}
    ok = True
    sent_at = after.index(sent[0]) if sent else len(after)
    for n, e in enumerate(after):
        if e["method"] not in cro_runtime.ALLOWED_METHODS and e["outcome"] == "completed":
            add_issue(entry, "FAIL", "SEND", "a second %s reached %s by a redirect the guard cannot see" % (e["method"], e["url"]))
            ok = False
        elif n < sent_at or (n > sent_at and e["method"] not in ("GET", "HEAD")):
            # a GET after the consented entry is the page's follow-up (a post-redirect-get, the thank-you load), not a second send
            if e["outcome"] != "blocked" and form_check.address(e["url"]) in ours and e["resource_type"] != "websocket":
                add_issue(entry, "FAIL", "SEND", "a %s request to the action address %s went out besides the consented send"
                          % (e["method"], e["url"]))
                ok = False
    if not sent:
        posts = [e for e in after if e["method"] not in cro_runtime.ALLOWED_METHODS and e["outcome"] == "blocked"]
        if not posts and page_error is not None:
            add_issue(entry, "SKIPPED", "SEND", "the page could not be read after the press (%s) and no request to %s had left; "
                      "nothing was sent" % (first_line(page_error), host))
        elif not posts:
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
    elsewhere = form_check.address(sent[0]["url"]) not in ours
    if elsewhere:
        aborted = [e for e in after if e["rule"] == "consent:used" and form_check.address(e["url"]) in ours]
        if aborted:
            add_issue(entry, "FAIL", "SEND", "the request to %s took the single send and the form's own request was aborted, so the "
                      "form itself was not sent" % sent[0]["url"])
            return False
        add_issue(entry, "WARN", "SEND", "the one consented request went to %s, not to the form's action address %s, most likely the "
                  "page's script sending the form there; check that the test lead arrived before any rerun" % (sent[0]["url"], action))
    status = sent[0]["status"]
    if status is None and sent[0].get("failure"):
        add_issue(entry, "FAIL", "SEND", "the request left and the form's host ended the connection with no answer (%s); a browser can send "
                  "such a request again by itself, so the host may have received the submission twice, once or not at all; check before any "
                  "rerun" % sent[0]["failure"])
    elif status is None and page_error is None:
        add_issue(entry, "WARN", "SEND", "the form's host had not answered %d seconds after the press, so whether the test lead arrived "
                  "is not known; check before any rerun" % round(waited() / 1000))
    elif status is not None and status >= 400:
        add_issue(entry, "FAIL", "SEND", "%s answered HTTP %d" % (sent[0]["url"] if elsewhere else "the action host " + host, status))
    if held and status is not None:
        add_issue(entry, "WARN", "SEND", "the page that follows the send had not loaded %d seconds after the press, so the thank-you state "
                  "is not known; the send was answered HTTP %d; check that the test lead arrived before any rerun" % (round(waited() / 1000), status))
    return True if elsewhere else ok


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
        except (Exception, KeyboardInterrupt):
            if getattr(session, "consent_opened", False):
                print("form_consent: the script failed after the consent was opened; a submission may have been sent, check that the test "
                      "lead arrived before any rerun", file=sys.stderr)
            raise
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
