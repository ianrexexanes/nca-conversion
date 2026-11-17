"""Render a page in Chrome with analytics and tags blocked, and report what it shows.

Run by the plugin's venv python:
    render_check.py URL --out DIR [--timeout 45] [--blur]

Nothing is clicked, typed or sent. Only GET, HEAD and OPTIONS leave the browser, and a
blocked request is logged instead of sent. Frames stay in the page's process, the popup blocker
is on and no worker runs, so the page's one URL block covers everything. The browser is closed last, with browser.close()
alone: closing a context or page fires unload handlers whose requests are not intercepted.
With --blur, a blurred first screen at each width is saved too, for the question "is the button the most
visible thing here?". Exit 0 when the page rendered, 3 when it could not load, 2 on bad arguments.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import Error as PlaywrightError  # noqa: E402
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

import cro_runtime  # noqa: E402

VIEWPORTS = (
    ("desktop", 1440, 900, False),
    ("phone", 390, 844, True),
)
READ_PAGE = """
(fold) => {
  const doc = document.documentElement;
  const visible = (el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return box.width > 1 && box.height > 1 && box.right > 0 && box.bottom + window.scrollY > 0
      && style.visibility !== 'hidden' && style.opacity !== '0';
  };
  const clean = (text) => (text || '').replace(/\\s+/g, ' ').trim();
  const ctas = [];
  for (const el of document.querySelectorAll('button, input[type=submit], [role=button], a')) {
    if (!visible(el)) continue;
    if (el.tagName === 'A' && getComputedStyle(el).backgroundColor === 'rgba(0, 0, 0, 0)') continue;
    const text = clean(el.tagName === 'INPUT' ? el.value : el.innerText);
    const top = Math.round(el.getBoundingClientRect().top + window.scrollY);
    ctas.push({text: text, top: top, in_first_screen: top < fold});
  }
  const forms = [];
  for (const form of document.querySelectorAll('form')) {
    const fields = Array.from(form.querySelectorAll('input, select, textarea'))
      .filter((f) => !(f.tagName === 'INPUT' && ['hidden', 'submit'].includes(f.type)));
    forms.push({
      fields: fields.length,
      required: fields.filter((f) => f.required).length,
      top: Math.round(form.getBoundingClientRect().top + window.scrollY),
    });
  }
  const words = [];
  const walker = document.createTreeWalker(document.body || doc, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || parent.closest('script, style, noscript, template') || !visible(parent)) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const box = range.getBoundingClientRect();
    if (box.width > 0 && box.height > 0 && box.top + window.scrollY < fold) words.push(node.textContent);
  }
  return {
    first_screen_text: clean(words.join(' ')),
    ctas: ctas,
    forms: forms,
    page_height: doc.scrollHeight,
    horizontal_scroll: doc.scrollWidth > doc.clientWidth,
  };
}
"""


def first_line(error) -> str:
    lines = str(error).strip().splitlines()
    return lines[0] if lines else error.__class__.__name__


BLUR_RULE = "html { filter: blur(8px) }"
# Added through the style sheet object model, so a page's content security policy cannot refuse it.
ADD_BLUR = """
(rule) => {
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(rule);
  document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
}
"""


def read_pass(recorder, browser, major, name, width, height, mobile, timeout_ms, out):
    """One viewport pass in its own context. Contexts are never closed: browser.close() ends them.

    With out["blur"] set, the blurred first screen is the last thing taken, after the regular shots."""
    context = cro_runtime.guarded_context(browser, recorder, major=major, width=width, height=height, mobile=mobile)
    page = cro_runtime.guarded_page(context, recorder)
    # domcontentloaded, not load: one file that never arrives must not cost the whole view.
    # Then the load event gets a third of the timeout, 15 s at most, and the pass carries on without it.
    response = page.goto(out["url"], wait_until="domcontentloaded", timeout=timeout_ms)
    status = response.status if response else None
    result = {"status": status, "final_url": page.url, "view": None}
    if status is not None and status >= 300:
        return result
    try:
        page.wait_for_load_state("load", timeout=min(timeout_ms / 3, 15000))
        load_event = True
    except PlaywrightTimeoutError:
        load_event = False
    page.wait_for_timeout(2000)
    position = 0
    for _step in range(60):
        total = page.evaluate("document.documentElement.scrollHeight")
        if position + height >= total:
            break
        position += height
        page.evaluate("window.scrollTo(0, %d)" % position)
        page.wait_for_timeout(100)
    page.evaluate("window.scrollTo(0, 0)")
    result["final_url"] = page.url
    facts = page.evaluate(READ_PAGE, height)
    first_name, full_name = "%s-first-screen.png" % name, "%s-full.png" % name
    page.screenshot(path=str(Path(out["dir"]) / first_name))
    page.screenshot(path=str(Path(out["dir"]) / full_name), full_page=True)
    facts.update({"width": width, "height": height, "screenshots": {"first_screen": first_name, "full": full_name},
                  "load_event": load_event})
    result["view"] = facts
    if out.get("blur"):
        page.evaluate(ADD_BLUR, BLUR_RULE)
        result["blur_shot"] = "%s-blur.png" % name
        page.screenshot(path=str(Path(out["dir"]) / result["blur_shot"]))
    return result


WORKERS_NOTE = ("Web workers are off in this capture, so a map, video or 3D viewer can look blank here "
                "while it shows for a visitor.")


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a page with analytics blocked.")
    parser.add_argument("url")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--blur", action="store_true", help="also save the first screen blurred, at both widths")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        parser.error("cannot create --out: %s" % error)

    recorder = cro_runtime.Recorder()
    render = {"url": args.url, "final_url": None, "checked_at": datetime.now(timezone.utc).isoformat(),
              "user_agent": None, "status": None, "viewports": {}, "blocked": [], "errors": [],
              "could_not_check": [], "notes": [WORKERS_NOTE]}
    out = {"url": args.url, "dir": str(out_dir), "blur": args.blur}
    blur_shots = {}
    playwright = sync_playwright().start()
    browser = None
    try:
        try:
            browser = cro_runtime.guarded_launch(playwright)
            major = int(browser.version.split(".")[0])
            render["user_agent"] = cro_runtime.chrome_ua(major)
            for name, width, height, mobile in VIEWPORTS:
                result = read_pass(recorder, browser, major, name, width, height, mobile, int(args.timeout * 1000), out)
                if name == "desktop":
                    render["status"], render["final_url"] = result["status"], result["final_url"]
                if result["view"] is None:
                    render["could_not_check"] = ["HTTP %d" % result["status"]]
                    break
                render["viewports"][name] = result["view"]
                if "blur_shot" in result:
                    blur_shots[name] = result["blur_shot"]
        except PlaywrightError as error:
            render["could_not_check"] = [first_line(error)]
        if blur_shots:
            render["blur"] = blur_shots
        log = recorder.finish()
        render["blocked"] = [{"url": e["url"], "rule": e["rule"], "method": e["method"]}
                             for e in log if e["outcome"] == "blocked"]
        render["errors"] = recorder.errors
        write_json(out_dir / "network-log.json", log)
        write_json(out_dir / "render.json", render)
    finally:
        if browser is not None:
            try:
                browser.close()
            except PlaywrightError:
                pass
        playwright.stop()
    print(out_dir / "render.json")
    return 3 if render["could_not_check"] else 0


if __name__ == "__main__":
    sys.exit(main())
