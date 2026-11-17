"""Read a form in Chrome with analytics blocked, and simulate its success and error answers without sending anything.

Run by the plugin's venv python:
    form_check.py URL --out DIR [--form CSS] [--simulate success|error] [--timeout 45]

Read-only (the default): reads every field, the status regions and the thank-you link, captures the form at 1440 and 390
wide, then presses submit once with the fields empty to see the browser's validation. A route on the browser context aborts every request to
the form's action address first, whatever its method, and the guard's context route aborts every other non-GET request.
--simulate fills archetype test data and answers the action address itself with a 200 (success) or a 500 (error), so both
states can be seen. In these two modes no non-GET request leaves the browser at any time, and after the route is installed no request to the
form's action address (the form's action and every submit control's formaction) leaves; a GET the page's own script sends
elsewhere is not covered, and neither is a GET to that address while the page loads or on the phone pass. Before any press the form's
target and the controls' formtarget are set to _self and window.open returns null. A popup the page still opens during the
press (a window.open it saved earlier, or a target="_blank" link it clicks itself) is under the guard's context rules and the
form-address route, but not under the address block the guard puts on the page it opens itself, so a GET it sends to a path on the site's own host is not covered.
The route never continues a request: it aborts or answers, or hands the request on to the guard with fallback. Exit 0 without a FAIL, 1 with one, 2 on bad input, 3 when the form
cannot be read. The browser is closed last, with browser.close() alone.
"""
import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # the scripts that do not render never need it; main() says so
    PlaywrightError = PlaywrightTimeoutError = Exception
    sync_playwright = None

import cro_runtime  # noqa: E402

DESKTOP = (1440, 900, False)
PHONE = (390, 844, True)
MAX_FIELDS = 4
SETTLE_MS = 300
SIM_LINE = "Test submission, simulated by form_check, nothing is sent"
SIM_EMAIL = "test.person@example.com"
FIELD_KEYS = ("name", "id", "label", "type", "required", "autocomplete", "inputmode", "visible")
SIMULATED = {"success": (200, {"success": True, "message": "Simulated answer from form_check"}),
             "error": (500, {"success": False, "message": "Simulated error from form_check"})}
CORS_HEADERS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "*"}
HELPERS = r"""
const clean = (t) => (t || '').replace(/\s+/g, ' ').trim();
const shown = (el) => {
  const b = el.getBoundingClientRect();
  const s = getComputedStyle(el);
  return b.width > 1 && b.height > 1 && b.right + window.scrollX > 0 && b.bottom + window.scrollY > 0
    && s.visibility !== 'hidden' && s.opacity !== '0';
};
const REGION = '[role=alert], [role=status], [aria-live]';
const describe = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
  + (el.getAttribute('role') ? '[role=' + el.getAttribute('role') + ']' : '');
const rendered = (el) => {
  const s = getComputedStyle(el);
  return el.getClientRects().length > 0 && s.visibility === 'visible' && s.opacity !== '0';
};
const faded = (el) => { for (let e = el; e; e = e.parentElement) { if (getComputedStyle(e).opacity === '0') return true; } return false; };
const formShown = (form) => !faded(form) && (rendered(form) || [...form.querySelectorAll('input, select, textarea, button')].some(rendered));
// A form that was not shown when the mark was set keeps its text in every snapshot, so being revealed (a scroll-reveal that has not played) is not a change.
const formReads = (form) => window.__formCheckShown === false || formShown(form);
const formOf = (i) => {
  if (window.__formCheckMark === true && window.__formCheckIndex === i) {
    const kept = window.__formCheckForm;
    return kept && kept.isConnected ? kept : null;
  }
  return document.querySelectorAll('form')[i] || null;
};
const regionsOf = (form) => {
  const seen = new Set();
  const found = [];
  const add = (el) => {
    if (seen.has(el)) return;
    seen.add(el);
    found.push({selector: describe(el), role: el.getAttribute('role'), aria_live: el.getAttribute('aria-live'),
                text: rendered(el) ? clean(el.innerText) : ''});
  };
  form.querySelectorAll(REGION).forEach(add);
  for (let sib = form.nextElementSibling; sib; sib = sib.nextElementSibling) {
    if (sib.matches(REGION)) add(sib);
    sib.querySelectorAll(REGION).forEach(add);
  }
  return found;
};
"""
READ_FORMS = "(css) => {" + HELPERS + r"""
const CAPTCHA = '.g-recaptcha, iframe[src*="recaptcha"], .h-captcha, iframe[src*="hcaptcha"], .cf-turnstile';
const REDIRECTS = ['redirect', '_redirect', '_next', 'next', 'redirect_to', 'success_url', 'thank_you', 'thankyou'];
const BUTTONS = ['submit', 'button', 'reset', 'image'];
const labelText = (label) => {
  const copy = label.cloneNode(true);
  copy.querySelectorAll('input, select, textarea, button, script, style').forEach((n) => n.remove());
  return clean(copy.textContent);
};
const labelOf = (el) => {
  if (el.id) {
    const named = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
    if (named && labelText(named)) return labelText(named);
  }
  const wrap = el.closest('label');
  if (wrap && labelText(wrap)) return labelText(wrap);
  const aria = clean(el.getAttribute('aria-label'));
  if (aria) return aria;
  const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
  const text = clean(ids.map((id) => { const n = document.getElementById(id); return n ? n.textContent : ''; }).join(' '));
  return text || null;
};
return [...document.querySelectorAll('form')].map((form, i) => {
  const all = [...form.querySelectorAll('input, select, textarea')];
  const fields = [];
  all.forEach((el, index) => {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'input' ? (el.type || 'text') : tag;
    if (tag === 'input' && BUTTONS.includes(type)) return;
    let visible = type !== 'hidden' && shown(el);
    if (!visible && (type === 'checkbox' || type === 'radio')) visible = [...(el.labels || [])].some(shown);
    const options = tag === 'select' ? [...el.options].filter((o) => o.value !== '' && !o.disabled) : [];
    fields.push({index, name: el.getAttribute('name'), id: el.id || null, label: labelOf(el), type, required: !!el.required,
                 autocomplete: el.getAttribute('autocomplete'), inputmode: el.getAttribute('inputmode'), visible,
                 value: el.getAttribute('value'), maxlength: typeof el.maxLength === 'number' && el.maxLength > 0 ? el.maxLength : null,
                 first_option: options.length ? options[0].value : null, disabled: !!el.disabled, readonly: !!el.readOnly});
  });
  let count = 0;
  const groups = new Set();
  fields.forEach((f) => {
    if (!f.visible || f.type === 'hidden') return;
    if (f.type === 'radio') groups.add(f.name || '#' + f.index); else count += 1;
  });
  count += groups.size;
  const scope = form.parentElement && form.parentElement.querySelectorAll('form').length === 1 ? form.parentElement : form;
  const captcha = [...scope.querySelectorAll(CAPTCHA)].some((el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
  const targets = [];
  form.querySelectorAll('input, select, textarea, button').forEach((el) => {
    if (el.tagName === 'INPUT' && el.type === 'hidden') return;
    if (!shown(el)) return;
    const b = el.getBoundingClientRect();
    if (b.width >= 44 && b.height >= 44) return;
    const name = el.id ? '#' + el.id : el.getAttribute('name') ? '[name=' + el.getAttribute('name') + ']' : el.tagName.toLowerCase();
    targets.push({name, w: Math.round(b.width), h: Math.round(b.height)});
  });
  const raw = (form.getAttribute('action') || '').trim();
  let action = document.URL;
  if (raw) { try { action = new URL(raw, document.baseURI).href; } catch (e) { action = raw; } }
  action = action.split('#')[0];
  const hidden = all.find((el) => el.type === 'hidden' && REDIRECTS.includes((el.getAttribute('name') || '').toLowerCase())
                                  && /^(https?:\/\/|\/|\.\.?\/)/.test((el.value || '').trim()));
  let thank = null;
  if (hidden) { try { thank = new URL(hidden.value.trim(), document.baseURI).href; } catch (e) { thank = null; } }
  const controls = [...form.querySelectorAll('button[type=submit], input[type=submit], input[type=image], button:not([type])')];
  const button = controls[0] || null;
  const resolve = (raw) => {
    raw = (raw || '').trim();
    if (!raw) return null;
    try { return new URL(raw, document.baseURI).href.split('#')[0]; } catch (e) { return null; }
  };
  const actions = [action];
  controls.forEach((c) => { const a = resolve(c.getAttribute('formaction')); if (a && !actions.includes(a)) actions.push(a); });
  let matches = true;
  if (css) matches = form.matches(css) || !!form.closest(css);
  return {i, action, actions, has_method: form.hasAttribute('method'), method: Object.getOwnPropertyDescriptor(HTMLFormElement.prototype, 'method').get.call(form), matches, fields, field_count: count, captcha, targets,
          regions: regionsOf(form), thank_you: thank,
          submit: {found: !!button, text: button ? clean(button.innerText || button.value || button.getAttribute('aria-label')) : null,
                   formaction: button ? resolve(button.getAttribute('formaction')) : null,
                   formmethod: button && button.hasAttribute('formmethod') ? button.formMethod : null}};
});
}"""
SNAPSHOT = "(i) => {" + HELPERS + r"""
const form = formOf(i);
return {marked: window.__formCheckMark === true, form: form && formReads(form) ? clean(form.innerText) : null,
        regions: form ? regionsOf(form).map((r) => r.text) : []};
}"""
REGIONS = "(i) => {" + HELPERS + "const form = formOf(i); return form ? regionsOf(form) : [];}"
VALIDATION = "(i) => {" + HELPERS + r"""
const form = formOf(i);
if (!form) return [];
return [...form.querySelectorAll('input, select, textarea')].filter((e) => e.willValidate && !e.validity.valid)
  .map((e) => ({field: e.getAttribute('name') || e.id || e.tagName.toLowerCase(), message: e.validationMessage}));
}"""
FORM_TEXT = "(i) => {" + HELPERS + "const form = formOf(i); return form && formReads(form) ? clean(form.innerText).slice(0, 600) : null;}"
PAGE_TEXT = r"""() => {
const main = document.querySelector('main, [role=main]') || document.body;
return (main.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 600);
}"""
NEUTRALISE = r"""(i) => {
window.open = () => null;
const form = document.querySelectorAll('form')[i];
if (!form) return;
form.setAttribute('target', '_self');
form.querySelectorAll('[formtarget]').forEach((el) => el.setAttribute('formtarget', '_self'));
}"""
CONTROL = "button[type=submit], input[type=submit], input[type=image], button:not([type])"
MARK = ("(i) => {" + HELPERS + " window.__formCheckMark = true; window.__formCheckIndex = i; window.__formCheckSeen = false;"
        " const form = document.querySelectorAll('form')[i] || null; window.__formCheckForm = form; window.__formCheckShown = !!form && formShown(form);"
        " const control = form ? form.querySelector('" + CONTROL + "') : null;"
        " document.addEventListener('click', (e) => { if (control && control.contains(e.target)) window.__formCheckSeen = true; }, true);"
        " document.addEventListener('submit', (e) => { if (form && e.target === form) window.__formCheckSeen = true; }, true); }")
LANDED = "() => ({marked: window.__formCheckMark === true, seen: window.__formCheckSeen === true})"
FORM_NODE = "([i, pressed]) => {" + HELPERS + "return pressed && window.__formCheckMark !== true ? null : formOf(i);}"
SET_FIELD = r"""(el, [action, value]) => {
if (action === 'fill') {
  el.focus(); el.value = value;
  el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
} else if (action === 'select') {
  el.value = value; el.dispatchEvent(new Event('change', {bubbles: true}));
} else if (!el.checked) {
  el.click();
}
}"""


class BadInput(Exception):
    pass


class Unreadable(Exception):
    """The page or its form could not be read; the message goes to stderr and the exit code is 3."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise BadInput(message)


def first_line(error) -> str:
    lines = str(error).strip().splitlines()
    return lines[0] if lines else error.__class__.__name__


def one_line(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def check_address(url):
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:  # an address urlsplit cannot read, such as "http://[::1"
        parts, host = None, None
    if parts is None or parts.scheme not in ("http", "https") or not host:
        raise BadInput("the page address must start with http:// or https://, got %r" % url)


def parse_args(argv):
    parser = Parser(prog="form_check", description="Read a form and simulate its answers; nothing is sent.")
    parser.add_argument("url")
    parser.add_argument("--out", required=True)
    parser.add_argument("--form")
    parser.add_argument("--simulate", choices=sorted(SIMULATED))
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args(argv)
    check_address(args.url)
    if args.timeout <= 0:
        raise BadInput("--timeout must be positive")
    make_out_dir(args.out)
    return args


def make_out_dir(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BadInput("cannot create --out: %s" % error)


def address(url):
    """(scheme, host, port, path) of an http(s) address, or None. The query and the fragment do not count."""
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https") or not parts.hostname:
            return None
        return scheme, parts.hostname.lower(), parts.port or (443 if scheme == "https" else 80), parts.path or "/"
    except ValueError:
        return None


class Session:
    """The Recorders of one run, one for each pass, and the form entries of form.json."""

    def __init__(self):
        self.recorders = []

    def recorder(self, **options):
        found = cro_runtime.Recorder(**options)
        self.recorders.append(found)
        return found

    def log(self):
        entries = []
        for found in self.recorders:
            entries.extend(found.finish())
        return entries

    def errors(self):
        seen = []
        for found in self.recorders:
            seen.extend(t for t in found.errors if t not in seen)
        return seen


def new_doc(url, mode):
    return {"url": url, "checked_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "forms": [],
            "network": {"blocked": 0, "consented": 0}, "errors": []}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_outputs(out_dir, doc, session):
    """form.json and network-log.json, written in every run that opened a browser."""
    log = session.log()
    doc["network"] = {"blocked": sum(1 for e in log if e["outcome"] == "blocked"),
                      "consented": 1 if any(e["outcome"] == "consented" for e in log) else 0}
    doc["errors"] = session.errors()
    write_json(Path(out_dir) / "network-log.json", log)
    write_json(Path(out_dir) / "form.json", doc)
    return log


def count_issues(doc):
    lines, fails, warns = [], 0, 0
    for entry in doc["forms"]:
        for issue in entry["issues"]:
            lines.append("%s form%d %s: %s" % (issue["level"], entry["index"], issue["rule"], issue["detail"]))
            fails += issue["level"] == "FAIL"
            warns += issue["level"] == "WARN"
    return lines, fails, warns


def add_issue(entry, level, rule, detail):
    entry["issues"].append({"level": level, "rule": rule, "detail": one_line(detail)})


def open_view(browser, recorder, major, view):
    """A guarded context and page at one of the two widths. Contexts are never closed: browser.close() ends them."""
    width, height, mobile = view
    context = cro_runtime.guarded_context(browser, recorder, major=major, width=width, height=height,
                                          mobile=mobile, reduced_motion="reduce")
    return cro_runtime.guarded_page(context, recorder)


def load(page, url, timeout_ms):
    """Open the page and let it settle. Raises Unreadable when it does not load or answers an error."""
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except PlaywrightError as error:
        raise Unreadable("the page could not be loaded: %s" % first_line(error))
    status = response.status if response else None
    if status is not None and status >= 400:
        raise Unreadable("the page answered HTTP %d" % status)
    try:
        page.wait_for_load_state("load", timeout=min(timeout_ms / 3, 15000))
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(1500)


def read_forms(page, css):
    try:
        return page.evaluate(READ_FORMS, css)
    except PlaywrightError as error:
        raise Unreadable("the forms could not be read: %s" % first_line(error))


def select_forms(forms, css, single):
    """The forms to act on. Raises Unreadable when there are none, or several where one is needed."""
    if not forms:
        raise Unreadable("the page holds no form")
    chosen = [f for f in forms if f["matches"]]
    if not chosen:
        raise Unreadable("--form %s matches no form on the page" % css)
    if single and len(chosen) > 1:
        raise Unreadable("the page holds %d forms; name one with --form" % len(chosen))
    return chosen


def new_entry(info):
    return {"index": info["i"] + 1, "action": info["action"], "method": info["method"],
            "fields": [{k: f[k] for k in FIELD_KEYS} for f in info["fields"]], "issues": [],
            "submit": {"text": info["submit"]["text"], "regions": info["regions"], "pressed": False, "validation": [],
                       "state": "none", "status_text": None, "status_source": "none", "time_ms": None},
            "thank_you": {"url": info["thank_you"], "text": None}, "filled": {}}


def snap_form(page, i, path):
    """Screenshot the form, else the whole page. Returns whether a file was written. After a press the form is the one that
    was pressed: when it has left the page or the document was replaced, the picture is the whole page, never another form."""
    try:
        node = page.evaluate_handle(FORM_NODE, [i, getattr(page, "form_check_pressed", False)]).as_element()
        if node is not None:
            node.screenshot(path=str(path), timeout=5000)
            return True
    except PlaywrightError:
        pass
    try:
        page.screenshot(path=str(path), full_page=True)
        return True
    except PlaywrightError:
        return False


def action_handler(recorder, targets, simulate):
    """The page route's handler. It marks the Recorder's entry first, then aborts (read-only) or answers (simulate).
    It never sends a request on: a request that is not the action address goes to the guard's route with fallback."""
    def handle(route):
        request = route.request
        if address(request.url) not in targets:
            route.fallback()
            return
        found = recorder.entry(request)
        found["outcome"] = "blocked"
        if simulate is None:
            found["rule"] = "form:action"
            route.abort()
            return
        found["rule"] = "form:simulate"
        status, body = SIMULATED[simulate]
        route.fulfill(status=status, headers=dict(CORS_HEADERS), content_type="application/json", body=json.dumps(body))
    return handle


def install_action_route(page, recorder, infos, simulate):
    targets = {a for a in (address(u) for info in infos for u in info["actions"]) if a}
    if targets:
        page.context.route(lambda url: address(url) in targets, action_handler(recorder, targets, simulate))  # the context, so a popup is covered too
    return targets


def click_submit(page, i):
    """Press the form's submit control once. Returns True when the click was made or cannot be shown to have
    failed (the page cannot be asked, or its mark is gone), False when the page is closed or the click by script fails.
    The click returns once it is made (no_wait_after), so a form that answers late does not time it out; when it raises anyway, the page says whether it landed, and a second
    click by script is made only when the page saw neither a click on the control nor a submit of the form."""
    button = page.locator("form").nth(i).locator(CONTROL).first
    try:
        button.click(timeout=4000, no_wait_after=True)
        return True
    except PlaywrightError:
        pass
    landed = safe_eval(page, LANDED, None, None)
    if page.is_closed():
        return False  # the page is gone: whether the click landed can no longer be asked
    if landed is None or not landed["marked"] or landed["seen"]:
        return True  # the document was replaced, or it saw the click or the submit: the press was made
    try:
        button.evaluate("el => el.click()")
        return True
    except PlaywrightError:
        return False


READ_BOUND_MS = None  # form_consent sets it once the consent opens: every read of the page then has this limit
READ_MISSED = False  # set when a bounded read got no answer inside its limit


def safe_eval(page, script, arg, default):
    """page.evaluate(script, arg), or default when it raises. With READ_BOUND_MS set, the read goes through wait_for_function, which
    keeps its timeout while the page is held by a request in flight, where evaluate waits for the answer without a limit (observed
    by probe on Playwright 1.62.0, UNVERIFIED beyond it; the call is documented at
    https://playwright.dev/python/docs/api/class-page#page-wait-for-function). The limit can fail for a read in progress at the instant a
    navigation begins (1 of 4 runs of a held-answer test, 6 of 24 back-to-back attempts of a reviewer's probe, none of 30 at the loop's 100 ms
    pace); the pause in press is for that. A read the page does not answer in time gives default."""
    global READ_MISSED
    try:
        if READ_BOUND_MS is None:
            return page.evaluate(script, arg)
        handle = page.wait_for_function("(arg) => ({value: (" + script + ")(arg)})", arg=arg, timeout=READ_BOUND_MS, polling=100)
        return handle.json_value()["value"]
    except PlaywrightError as error:
        if "Timeout" in type(error).__name__:
            READ_MISSED = True
        return default


def wait_for_state(page, i, before, started, limit_ms, stop=None, resume=None, hold=None):
    """After a press: "navigated" when the document is replaced, "changed" when the form's text or a region's text changes, or the form stops
    being shown, against the snapshot taken before the press, else "none" at the limit. A change is waited out: the wait goes on until the
    text has stayed the same for SETTLE_MS, so a button that says "Sending" is not the answer. Returns (state, milliseconds
    from the press to the state, or for "changed" to the last change seen). stop(elapsed_ms) ends the wait early.
    resume=(snapshot pair, ms of the last change) goes on from a state that has changed already. hold(), when given, is true
    while the page must not be asked (a document request is in flight, and the page's calls wait for it): the loop then only
    waits, in steps that do not ask the page, until the limit."""
    state, seen, changed, quiet = "none", None, 0.0, 0.0
    if resume:
        state, (seen, changed), quiet = "changed", resume, (time.monotonic() - started) * 1000
    while True:
        elapsed = (time.monotonic() - started) * 1000
        if hold is not None and hold():
            if elapsed >= limit_ms or (stop is not None and stop(elapsed)):
                break
            page.wait_for_timeout(100)
            continue
        now = safe_eval(page, SNAPSHOT, i, None)
        if now is not None and not now["marked"]:
            state = "navigated"
            break
        pair = (now["form"], now["regions"]) if now is not None else None
        if state == "none" and pair is not None and before is not None and pair != (before["form"], before["regions"]):
            state = "changed"
        if state == "changed" and pair is not None and pair != seen:
            seen, changed, quiet = pair, elapsed, elapsed
        if state == "changed" and elapsed - quiet >= SETTLE_MS:
            break
        if elapsed >= limit_ms or (stop is not None and stop(elapsed)):
            break
        page.wait_for_timeout(100)
    if state == "navigated":
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightError:
            pass
    return state, int(changed if state == "changed" else (time.monotonic() - started) * 1000)


def read_outcome(page, i, submit):
    """Read the regions and the status text as the page shows them now into submit, with status_source: "region" for a shown
    region's text, "form" for the form's own text after a change, "page" for the page's text after a navigation or when the
    form is gone or no longer shown, "none" (and no text) when nothing changed. Returns the text."""
    if submit["state"] != "navigated":
        submit["regions"] = safe_eval(page, REGIONS, i, submit["regions"])
    shown = [r["text"] for r in submit["regions"] if r["text"]]
    text, source = None, "none"
    if shown and submit["state"] != "navigated":
        text, source = shown[0], "region"
    elif submit["state"] == "navigated":
        text, source = safe_eval(page, PAGE_TEXT, None, None), "page"
    elif submit["state"] == "changed":
        text, source = safe_eval(page, FORM_TEXT, i, None), "form"
        if text is None:  # the form is gone: the page's text is what is left to read
            text, source = safe_eval(page, PAGE_TEXT, None, None), "page"
    submit["status_text"], submit["status_source"] = text, source
    return text


def press(page, i, info, limit_ms, stop=None, into=None, hold=None, shown=None):
    """Press submit once and record what followed. Returns the form's submit dict and the thank-you text.
    into, a dict, receives the submit dict as "submit" at once, so a caller that loses the page inside press still holds it.
    shown(), given with hold, is true once the caller's record holds a request made since the press."""
    submit = {"text": info["submit"]["text"], "regions": info["regions"], "pressed": False, "validation": [],
              "state": "none", "status_text": None, "status_source": "none", "time_ms": None}
    if into is not None:
        into["submit"] = submit
    text = None
    if info["submit"]["found"]:
        safe_eval(page, NEUTRALISE, i, None)  # no popup and no other target: the press stays on this page, behind the route
        safe_eval(page, MARK, i, None)
        page.form_check_pressed = True
        before = safe_eval(page, SNAPSHOT, i, None)
        started = time.monotonic()
        submit["pressed"] = click_submit(page, i)
    if submit["pressed"]:
        if hold is not None:
            # A read begun in the instant a navigation starts can wait for its answer past its limit (seen in 1 of 4 runs, UNVERIFIED
            # why), so the caller's record is given time to show the press before the first read: the wait ends as soon as shown() says
            # the record holds a request made since the press, or after 400 ms. What is left: a press that starts nothing for 400 ms is first
            # read then, so a change it makes before that is timed up to 0.4 s late.
            pause = time.monotonic()
            while (time.monotonic() - pause) * 1000 < 400 and not (shown is not None and shown()):
                page.wait_for_timeout(25)
        submit["state"], submit["time_ms"] = wait_for_state(page, i, before, started, limit_ms, stop, hold=hold)
        if hold is None or not hold():  # a page held by a request in flight is not asked
            submit["validation"] = [] if submit["state"] == "navigated" else safe_eval(page, VALIDATION, i, [])
            text = read_outcome(page, i, submit)
    return submit, text


URL_WORDS = re.compile(r"website|homepage|(?<![a-z])url(?![a-z])")


def url_like(f):
    """A free-text field the page means for an address: inputmode url, an autocomplete url token, or website, homepage
    or url in its name, id or label."""
    tokens = str(f.get("autocomplete") or "").lower().split()
    named = " ".join(str(f.get(k) or "") for k in ("name", "id", "label")).lower()
    return str(f.get("inputmode") or "").lower() == "url" or "url" in tokens or bool(URL_WORDS.search(named))


def fill_problems(page, i):
    """The fields of form i that the page's own validation refuses after the fill, as {"field", "message"}. Empty when none."""
    return safe_eval(page, VALIDATION, i, [])


def plan_fill(fields, line, email):
    """What to type, check or choose, as (field, action, value). line goes in the free-text fields, email in the email fields,
    https://example.com in the URL fields."""
    plan = []
    required_groups = {f["name"] or "#%d" % f["index"] for f in fields if f["type"] == "radio" and f["required"]}
    done = set()
    for f in fields:
        if not f["visible"] or f["disabled"] or f["readonly"] or f["type"] in ("hidden", "file", "range", "color"):
            continue
        kind = f["type"]
        blob = " ".join(str(f.get(k) or "") for k in ("name", "id", "label", "autocomplete")).lower()
        if kind == "checkbox":
            if f["required"]:
                plan.append((f, "check", f["value"] or "on"))
        elif kind == "radio":
            group = f["name"] or "#%d" % f["index"]
            if group in required_groups and group not in done:
                done.add(group)
                plan.append((f, "check", f["value"] or "on"))
        elif kind == "select":
            if f["first_option"] is not None:
                plan.append((f, "select", f["first_option"]))
        elif kind == "email" or (kind in ("text", "search", "") and ("e-mail" in blob or "email" in blob)):
            plan.append((f, "fill", email or SIM_EMAIL))
        elif kind == "tel":
            plan.append((f, "fill", "0000000000"))
        elif kind == "url" or (kind in ("text", "search", "") and url_like(f)):
            plan.append((f, "fill", "https://example.com"))
        elif kind == "number":
            plan.append((f, "fill", "1"))
        elif kind == "date":
            plan.append((f, "fill", date.today().isoformat()))
        elif kind == "password":
            plan.append((f, "fill", "Test-only-0000"))
        elif kind in ("text", "search", "textarea", ""):
            name_like = "name" in blob and not any(w in blob for w in ("company", "organi", "business", "firm", "user"))
            value = "Test Person" if name_like and line == SIM_LINE else line
            plan.append((f, "fill", value))
    return [(f, a, v[:f["maxlength"]] if a == "fill" and f["maxlength"] else v) for f, a, v in plan]


def apply_plan(page, i, plan):
    """Type, check and choose the planned values. Returns the filled values keyed by field name, else id."""
    scope = page.locator("form").nth(i).locator("input, select, textarea")
    filled = {}
    for f, action, value in plan:
        element = scope.nth(f["index"])
        try:
            if action == "fill":
                element.fill(value, timeout=3000)
            elif action == "select":
                element.select_option(value, timeout=3000)
            else:
                element.check(timeout=3000)
        except PlaywrightError:
            try:
                element.evaluate(SET_FIELD, [action, value])
            except PlaywrightError:
                continue
        filled[f["name"] or f["id"] or "field%d" % f["index"]] = value if action != "check" or f["type"] == "radio" else "checked"
    return filled


def run_read_only(args, browser, major, session, doc, out_dir, timeout_ms):
    recorder = session.recorder()
    page = open_view(browser, recorder, major, DESKTOP)
    load(page, args.url, timeout_ms)
    chosen = select_forms(read_forms(page, args.form), args.form, False)
    entries = {info["i"]: new_entry(info) for info in chosen}
    doc["forms"] = list(entries.values())
    for info in chosen:
        entry = entries[info["i"]]
        snap_form(page, info["i"], out_dir / ("form%d-1440.png" % entry["index"]))
        if info["field_count"] > MAX_FIELDS:
            add_issue(entry, "WARN", "FIELD_COUNT", "%d visible fields, a form this long asks for more than most visitors give"
                      % info["field_count"])
        if info["captcha"]:
            add_issue(entry, "WARN", "CAPTCHA", "a challenge is visible in the form; it adds a step before the visitor can send")
    mark = len(recorder.entries)
    targets = install_action_route(page, recorder, chosen, None)
    for info in chosen:
        entry = entries[info["i"]]
        entry["submit"], _text = press(page, info["i"], info, 1000)
        entry["submit"]["time_ms"] = None
        if entry["submit"]["state"] == "navigated":
            break
    page.wait_for_timeout(500)
    tripwire(entries, session, targets, {id(recorder): mark})
    recorder = session.recorder()
    page = open_view(browser, recorder, major, PHONE)
    load(page, args.url, timeout_ms)
    phone = {info["i"]: info for info in read_forms(page, None)}
    for i, entry in entries.items():
        info = phone.get(i)
        if info is None:
            continue
        snap_form(page, i, out_dir / ("form%d-390.png" % entry["index"]))
        for target in info["targets"]:
            add_issue(entry, "WARN", "TARGET", "%s %dx%d" % (target["name"], target["w"], target["h"]))


def tripwire(entries, session, targets, marks):
    """FAIL SENT when this run's own log, read after its requests settled, shows a non-GET request that was not blocked, or a request
    to an action address after the route went on that was not blocked, whatever its outcome (unset and failed count)."""
    first = next(iter(entries.values()))
    for found in session.recorders:
        found.finish()
        for e in found.entries[marks.get(id(found), 0):]:
            if e["resource_type"] == "websocket" or e["outcome"] == "blocked":
                continue
            if e["method"] not in cro_runtime.ALLOWED_METHODS or address(e["url"]) in targets:
                add_issue(first, "FAIL", "SENT", "%s %s left the browser (%s)" % (e["method"], e["url"], e["outcome"]))
                return


def run_simulate(args, browser, major, session, doc, out_dir, timeout_ms):
    recorder = session.recorder()
    page = open_view(browser, recorder, major, DESKTOP)
    load(page, args.url, timeout_ms)
    info = select_forms(read_forms(page, args.form), args.form, True)[0]
    entry = new_entry(info)
    doc["forms"] = [entry]
    targets = install_action_route(page, recorder, [info], args.simulate)
    entry["filled"] = apply_plan(page, info["i"], plan_fill(info["fields"], SIM_LINE, None))
    mark = len(recorder.entries)
    problems = fill_problems(page, info["i"])
    if problems:
        text = None
        entry["submit"]["validation"] = problems
        for p in problems:
            add_issue(entry, "WARN", "FILL", "the test data does not satisfy %s (%s); the form was not pressed"
                      % (p["field"], p["message"]))
    else:
        entry["submit"], text = press(page, info["i"], info, 10000)
    if entry["submit"]["state"] == "navigated" and address(page.url) in targets:
        # no script took the reply: the simulated answer became the document, which is not a state the site shows
        entry["submit"]["status_text"], entry["submit"]["status_source"] = None, "none"
        add_issue(entry, "SKIPPED", "SIMULATE", "this form submits without a script, so the simulated reply replaced the page and is "
                  "not a state the site shows; nothing was sent")
    else:
        entry["thank_you"]["text"] = text
        if entry["submit"]["state"] == "navigated":
            entry["thank_you"]["url"] = page.url
        snap_form(page, info["i"], out_dir / ("form%d-simulate-%s.png" % (entry["index"], args.simulate)))
    elsewhere = [e for e in recorder.entries[mark:] if e["method"] not in cro_runtime.ALLOWED_METHODS
                 and e["rule"] != "form:simulate" and address(e["url"]) not in targets]
    answered = [e for e in recorder.entries[mark:] if e["rule"] == "form:simulate"]
    if elsewhere:
        add_issue(entry, "SKIPPED", "SIMULATE", "the form sends to %s, not to its action address %s, so nothing was simulated"
                  % (elsewhere[0]["url"], info["action"]))
    elif not problems and not answered and entry["submit"]["state"] == "none":
        add_issue(entry, "SKIPPED", "SIMULATE", "the press sent nothing to %s; the form may need a field this test data does not fill"
                  % info["action"])
    page.wait_for_timeout(500)
    tripwire({1: entry}, session, targets, {id(recorder): mark})


def main(argv=None):
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except BadInput as error:
        print("form_check: %s" % error, file=sys.stderr)
        return 2
    if sync_playwright is None:
        print("form_check: Playwright is not installed; run setup.py", file=sys.stderr)
        return 3
    out_dir = Path(args.out)
    mode = "simulate-" + args.simulate if args.simulate else "read-only"
    doc = new_doc(args.url, mode)
    session = Session()
    code = 0
    playwright = sync_playwright().start()
    browser = None
    try:
        try:
            browser = cro_runtime.guarded_launch(playwright)
            major = int(browser.version.split(".")[0])
            doc["user_agent"] = cro_runtime.chrome_ua(major)
            run = run_simulate if args.simulate else run_read_only
            run(args, browser, major, session, doc, out_dir, int(args.timeout * 1000))
        except Unreadable as error:
            print("form_check: %s" % error, file=sys.stderr)
            code = 3
        except PlaywrightError as error:
            print("form_check: the page could not be read: %s" % first_line(error), file=sys.stderr)
            code = 3
        lines, fails, warns = count_issues(doc)
        write_outputs(out_dir, doc, session)
    finally:
        if browser is not None:
            try:
                browser.close()
            except PlaywrightError:
                pass
        playwright.stop()
    for text in lines:
        print(text)
    print("form_check: %d FAIL, %d WARN" % (fails, warns))
    if code:
        return code
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
