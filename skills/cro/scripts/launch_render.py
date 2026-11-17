"""The rendered launch gate of /cro check: what a visitor would hit on a built page, at four widths.

Run by the plugin's venv python:
    launch_render.py URL... --out DIR [--widths 375,390,820,1440] [--deck DECK.md [--variant V]]
                     [--action-color HEX] [--landing] [--timeout 45]

Every page is opened through the plugin's one analytics guard (cro_runtime), with reduced motion, and read
the way render_check.py reads it: domcontentloaded, the load event within a capped wait, a scroll through
the page and back to the top. Nothing is clicked, typed or sent. Prints one line per finding,
`FAIL|WARN|SKIPPED <page>@<width> <RULE>: <detail>`, then `launch_render: <f> FAIL, <w> WARN`, and writes
DIR/launch.json and DIR/network-log.json. Exit 0 without a FAIL, 1 with one, 2 on bad input (before any
browser opens), 3 when the browser cannot start.

Measured against WCAG 2.2: 1.4.3 contrast, 2.5.8 target size with its Spacing and Inline exceptions
(https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), 2.5.5 for the 44 px advice.
"""
import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cro_runtime  # noqa: E402
from deck_check import parse_deck  # noqa: E402
from design_check import contrast, normal  # noqa: E402
from form_check import BadInput as AddressRefused, check_address  # noqa: E402
from urllib.parse import urlsplit  # noqa: E402

DEFAULT_WIDTHS = (375, 390, 820, 1440)
# texts of a page error that show a failed network call; add only a text seen in a run
NETWORK_FAILURES = ("Failed to fetch",)
PHONE_BELOW = 600  # render_check's two views: a phone context under this width, a desktop at or above it
PHONE_HEIGHT, DESKTOP_HEIGHT = 844, 900
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\Z")
MIN_TARGET, WANT_TARGET, CIRCLE = 24, 44, 24
SHOWN = 3  # examples named on a grouped line

MEASURE_PAGE = r"""
(opts) => {
  const doc = document.documentElement;
  const clean = (text) => (text || '').replace(/\s+/g, ' ').trim();
  // Any syntax Chromium paints (rgb, oklch, lab, color()) goes through a 1x1 canvas to sRGB. A value the canvas
  // rejects leaves fillStyle on the sentinel, and is not measured.
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const pen = canvas.getContext('2d', {willReadFrequently: true});
  const seen = new Map();
  const colour = (value) => {
    if (!value) return null;
    if (seen.has(value)) return seen.get(value);
    let result = null;
    pen.fillStyle = '#010203'; pen.fillStyle = value;
    const first = pen.fillStyle;
    pen.fillStyle = '#040506'; pen.fillStyle = value;
    if (!(first === '#010203' && pen.fillStyle === '#040506')) {
      pen.clearRect(0, 0, 1, 1);
      pen.fillRect(0, 0, 1, 1);
      const px = pen.getImageData(0, 0, 1, 1).data;
      result = {r: px[0], g: px[1], b: px[2], a: px[3] / 255};
    }
    seen.set(value, result);
    return result;
  };
  const hex = (c) => '#' + [c.r, c.g, c.b].map((n) => Math.round(n).toString(16).padStart(2, '0')).join('');
  const visible = (el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return box.width > 1 && box.height > 1 && box.right > 0 && box.bottom + window.scrollY > 0
      && style.visibility !== 'hidden' && style.display !== 'none' && parseFloat(style.opacity) !== 0
      && el.checkVisibility({opacityProperty: true, visibilityProperty: true});  // an ancestor's display, visibility and opacity too
  };
  const textOf = (el) => clean(el.tagName === 'INPUT' ? el.value : el.textContent);
  const name = (el) => {
    const tag = el.tagName.toLowerCase();
    if (el.id) return tag + '#' + el.id;
    const text = textOf(el).slice(0, 40);
    return text ? tag + ' "' + text + '"' : tag;
  };
  // an element carries the deck's label when its text and the label match once everything but letters and digits is cut from both ends
  const core = (t) => t.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
  const carries = (el) => opts.label !== null && (core(opts.label) !== '' ? core(textOf(el)) === core(opts.label) : textOf(el) === opts.label);
  const labelEls = opts.label === null ? [] : Array.from(document.querySelectorAll('a, button, input[type=submit], input[type=button], [role=button]')).filter((el) => visible(el) && carries(el));
  const ownText = (el) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim() !== '');
  const body = document.body || doc;
  const out = {};

  out.scroll = {scroll_width: doc.scrollWidth, client_width: doc.clientWidth};

  const root = document.querySelector('main') || body;
  const textEls = Array.from(root.querySelectorAll('p, li, dd, td, blockquote'))
    .filter((el) => !el.closest('nav, footer, small, figcaption') && visible(el) && textOf(el) !== '');
  out.body_text = textEls.map((el) => {
    const style = getComputedStyle(el);
    return {name: name(el), size: parseFloat(style.fontSize), color: style.color, chars: textOf(el).length};
  });
  const bodyStyle = getComputedStyle(body);
  out.body_element = {size: parseFloat(bodyStyle.fontSize), color: bodyStyle.color};
  out.h1 = Array.from(document.querySelectorAll('h1')).filter(visible)
    .map((el) => ({name: name(el), size: parseFloat(getComputedStyle(el).fontSize)}));
  out.images_without_alt = Array.from(document.querySelectorAll('img'))
    .filter((el) => !el.hasAttribute('alt')).map((el) => name(el) + ' ' + (el.getAttribute('src') || '').slice(0, 40));

  // targets
  const targetSelector = 'button, input[type=submit], input[type=button], input[type=checkbox], input[type=radio], select, summary, [role=button], a';
  const targetEls = Array.from(document.querySelectorAll(targetSelector)).filter(visible);
  const index = new Map(targetEls.map((el, i) => [el, i]));
  out.targets = targetEls.map((el) => {
    const box = el.getBoundingClientRect();
    let parent = -1;
    for (let up = el.parentElement; up; up = up.parentElement) {
      if (index.has(up)) { parent = index.get(up); break; }
    }
    const inline = el.tagName === 'A' && getComputedStyle(el).display === 'inline' && !!el.parentElement
      && Array.from(el.parentElement.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim() !== '');
    return {name: name(el), x: box.left, y: box.top, w: box.width, h: box.height, inline: inline, parent: parent};
  });

  // the deck's label
  let candidates = null;
  if (opts.label !== null) {
    const forms = Array.from(document.forms);
    const formTarget = (form) => 'form:' + forms.indexOf(form);
    const resolve = (el) => {
      if (el.tagName === 'A') {
        if (el.getAttribute('href') === null) return 'script';
        let url, here;
        try { url = new URL(el.href); here = new URL(location.href); } catch (e) { return el.href; }
        if (url.hash.length > 1 && url.origin + url.pathname + url.search === here.origin + here.pathname + here.search) {
          let id = url.hash.slice(1);
          try { id = decodeURIComponent(id); } catch (e) { /* keep the raw fragment */ }
          const hit = document.getElementById(id);
          if (hit) {
            if (hit.tagName === 'FORM') return formTarget(hit);
            const owner = hit.closest('form');
            if (owner) return formTarget(owner);
            const inside = hit.querySelectorAll('form');
            if (inside.length === 1) return formTarget(inside[0]);
          }
        }
        return el.href;
      }
      const submits = (el.tagName === 'INPUT' && el.type === 'submit') || (el.tagName === 'BUTTON' && el.type === 'submit');
      const form = el.form || el.closest('form');
      return submits && form ? formTarget(form) : 'script';
    };
    const matched = labelEls;
    // matches inside one another are one element: the outermost, going where a match inside it goes when it only runs a script
    candidates = matched.filter((el) => !matched.some((outer) => outer !== el && outer.contains(el)))
      .map((el) => {
        const box = el.getBoundingClientRect();
        let target = resolve(el);
        if (target === 'script') {
          const inner = matched.map(resolve).find((t, i) => el.contains(matched[i]) && t !== 'script');
          if (inner !== undefined) target = inner;
        }
        return {name: name(el), top: box.top, bottom: box.bottom, left: box.left, right: box.right, target: target};
      });
    out.viewport = {w: window.innerWidth, h: window.innerHeight};
  }
  out.candidates = candidates;

  // the action colour
  if (opts.action !== null) {
    const same = (c) => c && c.a > 0 && Math.abs(c.r - opts.action[0]) <= 1 && Math.abs(c.g - opts.action[1]) <= 1 && Math.abs(c.b - opts.action[2]) <= 1;
    const actionRoots = candidates !== null
      ? labelEls
      : targetEls;
    const inAction = (el) => actionRoots.some((root) => root === el || root.contains(el));
    out.action_carriers = [];
    for (const el of Array.from(body.querySelectorAll('*')).concat([body])) {
      if (!visible(el) || inAction(el)) continue;
      const style = getComputedStyle(el);
      if (same(colour(style.backgroundColor))) out.action_carriers.push(name(el) + ' (background)');
      else if (ownText(el) && same(colour(style.color))) out.action_carriers.push(name(el) + ' (text)');
      else {
        for (const pseudo of ['::before', '::after']) {
          const ps = getComputedStyle(el, pseudo);
          if (ps.content !== 'none' && ps.content !== 'normal' && same(colour(ps.backgroundColor))) {
            out.action_carriers.push(name(el) + ' ' + pseudo + ' (background)');
            break;
          }
        }
      }
    }
  }

  // markup read once per page
  out.has_nav = Array.from(document.querySelectorAll('nav')).some((nav) => nav.querySelector('a[href]'));
  out.autoplay = Array.from(document.querySelectorAll('video[autoplay]')).map(name);
  const sliderWords = ['swiper', 'slick', 'splide', 'glide', 'carousel'];
  out.sliders = Array.from(document.querySelectorAll('[class], [aria-roledescription]')).filter((el) => {
    const role = (el.getAttribute('aria-roledescription') || '').toLowerCase();
    const classes = (el.getAttribute('class') || '').toLowerCase().split(/\s+/);
    return role === 'carousel' || classes.some((token) => sliderWords.some((word) => token.includes(word)));
  }).map(name);

  // contrast, last: it scrolls
  const measured = [], skipped = [];
  const textNodeEls = Array.from(body.querySelectorAll('*')).filter((el) =>
    ownText(el) && !el.closest('script, style, noscript, template, svg, select, option') && visible(el)).slice(0, 4000);
  const mediaBeneath = (node) => !!node.closest('img, picture, video, canvas, svg') || getComputedStyle(node).backgroundImage !== 'none';
  for (const el of textNodeEls) {
    const style = getComputedStyle(el);
    const fg = colour(style.color);
    const label = name(el);
    if (!fg || fg.a < 1) { skipped.push(label); continue; }
    let reason = null, owner = null, bg = null;
    for (let node = el; node; node = node.parentElement) {
      const s = getComputedStyle(node);
      if (parseFloat(s.opacity) < 1) { reason = 'opacity'; break; }
      if (s.backgroundImage !== 'none') { reason = 'image'; break; }
      const c = colour(s.backgroundColor);
      if (!c) { reason = 'unreadable'; break; }
      if (c.a === 1) { owner = node; bg = c; break; }
      if (c.a > 0) { reason = 'translucent'; break; }
    }
    if (reason) { skipped.push(label); continue; }
    if (!bg) bg = {r: 255, g: 255, b: 255, a: 1};
    const range = document.createRange();
    range.selectNodeContents(el);
    let box = range.getBoundingClientRect();
    if (!(box.width > 0 && box.height > 0)) continue;
    if (box.top < 0 || box.bottom > window.innerHeight || box.left < 0 || box.right > window.innerWidth) {
      window.scrollBy(0, box.top + box.height / 2 - window.innerHeight / 2);
      box = range.getBoundingClientRect();
    }
    const stack = document.elementsFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    let from = -1;
    stack.forEach((n, i) => { if (n === el || el.contains(n)) from = i; });
    let to = owner ? stack.indexOf(owner) : -1;
    if (to < 0) to = stack.length;
    if (stack.slice(from + 1, to).some(mediaBeneath)) { skipped.push(label); continue; }
    const size = parseFloat(style.fontSize), weight = parseInt(style.fontWeight, 10) || 400;
    measured.push({name: label, fg: hex(fg), bg: hex(bg), large: size >= 24 || (size >= 18.66 && weight >= 700)});
  }
  window.scrollTo(0, 0);
  out.contrast = measured;
  out.contrast_skipped = skipped;
  return out;
}
"""


class BadInput(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise BadInput(message)


def first_line(error) -> str:
    lines = str(error).strip().splitlines()
    return lines[0] if lines else error.__class__.__name__


def one_line(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def check_page_address(url):
    """http and https addresses by form_check's rule, and a file address with a path (0.4.0 read those too)."""
    try:
        check_address(url)
        return
    except AddressRefused:
        pass
    try:
        parts = urlsplit(url)
        local = parts.scheme == "file" and bool(parts.path)
    except ValueError:  # an address urlsplit cannot read, such as "http://[::1"
        local = False
    if not local:
        raise BadInput("the page address must start with http://, https:// or file://, got %r" % url)


def parse_args(argv):
    parser = Parser(description="Read built pages through the analytics guard and report launch blockers.")
    parser.add_argument("urls", nargs="*", metavar="URL")
    parser.add_argument("--out", required=True)
    parser.add_argument("--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS))
    parser.add_argument("--deck")
    parser.add_argument("--variant")
    parser.add_argument("--action-color", dest="action_color")
    parser.add_argument("--landing", action="store_true")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args(argv)
    if not args.urls:
        raise BadInput("no page address given")
    for url in args.urls:
        check_page_address(url)
    widths = []
    for part in args.widths.split(","):
        if not re.fullmatch(r"[0-9]+", part.strip()) or int(part) < 1:
            raise BadInput("--widths must be a comma list of positive integers, got %r" % args.widths)
        if int(part) not in widths:
            widths.append(int(part))
    args.widths = widths
    if args.variant is not None and not args.deck:
        raise BadInput("--variant needs --deck")
    args.label = args.label_key = None
    args.variant_used = None
    if args.deck:
        read_label(args)
    if args.action_color is not None:
        if not HEX.match(args.action_color):
            raise BadInput("--action-color must be #rgb or #rrggbb, got %r" % args.action_color)
        args.action_color = normal(args.action_color)
    try:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BadInput("cannot create --out: %s" % error)
    return args


def read_label(args):
    try:
        deck = parse_deck(Path(args.deck).read_text(encoding="utf-8"))
    except OSError:
        raise BadInput("cannot read %s" % args.deck)
    except UnicodeDecodeError:
        raise BadInput("%s is not UTF-8 text" % args.deck)
    if len(deck.namespaces) != 1:
        raise BadInput("%s has %d pages (## ns: sections); this check reads one page per deck" % (args.deck, len(deck.namespaces)))
    ns = deck.namespaces[0]
    variants = deck.variants(ns)
    if args.variant is None:
        if len(variants) > 1:
            raise BadInput("the deck has variants %s; name one with --variant" % ", ".join(variants))
        v = variants[0]
    elif args.variant not in variants:
        raise BadInput("%r is not a variant of the deck (it has %s)" % (args.variant, ", ".join(repr(x) for x in variants)))
    else:
        v = args.variant
    label = deck.label(ns, v)
    if label is None:
        raise BadInput("the deck has no button label for %s (neither %s.cta.hook.<variant> nor %s.cta.button)" % (ns, ns, ns))
    args.label = " ".join(label.split())  # the page side is folded the same way (clean() in the page script)
    args.label_key = deck.label_key(ns, v)
    args.variant_used = v


def listing(items, shown=SHOWN):
    items = [one_line(i) for i in items]
    text = "; ".join(items[:shown])
    return text + (" (and %d more)" % (len(items) - shown) if len(items) > shown else "")


def rect_distance(cx, cy, t):
    dx = max(t["x"] - cx, 0, cx - (t["x"] + t["w"]))
    dy = max(t["y"] - cy, 0, cy - (t["y"] + t["h"]))
    return math.hypot(dx, dy)


def small(t):
    return round(t["w"], 2) < MIN_TARGET or round(t["h"], 2) < MIN_TARGET


def spacing_exception(targets, i):
    """WCAG 2.5.8's Spacing exception: a 24 px circle on the target's centre meets no other target's box and
    no other undersized target's circle. Circles that only touch do not meet."""
    me = targets[i]
    cx, cy = me["x"] + me["w"] / 2, me["y"] + me["h"] / 2
    related = set()  # this target's own ancestors; its descendants are skipped below
    up = me["parent"]
    while up >= 0:
        related.add(up)
        up = targets[up]["parent"]
    for j, other in enumerate(targets):
        if j == i or j in related:
            continue
        up, nested = other["parent"], False
        while up >= 0:
            if up == i:
                nested = True
                break
            up = targets[up]["parent"]
        if nested:
            continue
        if rect_distance(cx, cy, other) < CIRCLE / 2 - 1e-6:
            return False
        if small(other):
            ox, oy = other["x"] + other["w"] / 2, other["y"] + other["h"] / 2
            if math.hypot(cx - ox, cy - oy) < CIRCLE - 1e-6:
                return False
    return True


def target_findings(targets):
    rows, under = [], []
    for i, t in enumerate(targets):
        if t["inline"]:
            continue
        size = "%s %dx%d" % (t["name"], round(t["w"]), round(t["h"]))
        if small(t) and not spacing_exception(targets, i):
            rows.append(("FAIL", "TARGET", "%s is under %d by %d CSS px and a %d px circle on it meets another target" % (size, MIN_TARGET, MIN_TARGET, CIRCLE)))
        elif round(t["w"], 2) < WANT_TARGET or round(t["h"], 2) < WANT_TARGET:
            under.append(size)
    if under:
        rows.append(("WARN", "TARGET", "%d target(s) under %d by %d CSS px: %s" % (len(under), WANT_TARGET, WANT_TARGET, listing(under))))
    return rows


def analyse(facts, args, widest, view_width, markup):
    """The findings for one page at one width, in print order."""
    rows = []
    add = lambda level, rule, detail: rows.append((level, rule, one_line(detail)))  # noqa: E731
    scroll = facts["scroll"]
    if scroll["scroll_width"] > scroll["client_width"]:
        add("FAIL", "SCROLL", "the page is %d px wide in a %d px viewport" % (scroll["scroll_width"], scroll["client_width"]))
    text = facts["body_text"]
    under = [t for t in text if t["size"] < 16]
    if under:
        add("FAIL", "BODY_TEXT", "%d body text element(s) under 16 px: %s" % (
            len(under), listing("%s at %gpx" % (t["name"], t["size"]) for t in under)))
    if len(facts["h1"]) != 1:
        add("FAIL", "H1", "%d visible h1 elements; one is needed%s" % (
            len(facts["h1"]), ": " + listing(h["name"] for h in facts["h1"]) if facts["h1"] else ""))
    if facts["images_without_alt"]:
        add("FAIL", "ALT", "%d img element(s) with no alt attribute (alt=\"\" marks a decorative image): %s" % (
            len(facts["images_without_alt"]), listing(facts["images_without_alt"])))
    if args.label is None:
        add("SKIPPED", "LABEL_FOLD", "no --deck given, so the button label is not known")
        add("SKIPPED", "ONE_TARGET", "no --deck given, so the button label is not known")
    else:
        found = facts["candidates"]
        view = facts["viewport"]
        inside = [c for c in found if c["top"] >= 0 and c["bottom"] <= view["h"] and c["left"] >= -0.5 and c["right"] <= view["w"] + 0.5]
        if not inside:
            where = ("the nearest sits %d px down" % round(min(c["top"] for c in found))) if found else "no button or link shows it"
            add("FAIL", "LABEL_FOLD", "\"%s\" (%s) is not wholly inside the first screen of %d px: %s" % (
                args.label, args.label_key, view["h"], where))
        targets = sorted({c["target"] for c in found})
        if len(targets) > 1:
            add("FAIL", "ONE_TARGET", "%d elements showing \"%s\" go to %d targets: %s" % (len(found), args.label, len(targets), listing(targets, 4)))
    rows.extend(target_findings(facts["targets"]))
    carriers = facts.get("action_carriers") or []
    if carriers:
        add("FAIL", "ACTION_COLOUR", "%s is on %d element(s) outside the action: %s" % (args.action_color, len(carriers), listing(carriers)))
    bad = []
    for m in facts["contrast"]:
        need = 3.0 if m["large"] else 4.5
        ratio = contrast(m["fg"], m["bg"])
        if ratio < need:
            bad.append("%s %s on %s is %.2f:1 (needs %g:1)" % (m["name"], m["fg"], m["bg"], ratio, need))
    if bad:
        add("FAIL", "CONTRAST", "%d text element(s) under the WCAG 1.4.3 ratio: %s" % (len(bad), listing(bad)))
    if facts["contrast_skipped"]:
        add("SKIPPED", "CONTRAST", "%d text element(s) on an image, gradient, translucent colour or fading element, not measured: %s" % (
            len(facts["contrast_skipped"]), listing(facts["contrast_skipped"])))
    blacks = [t for t in text if t["color"] == "rgb(0, 0, 0)"]
    if blacks or (not text and facts["body_element"]["color"] == "rgb(0, 0, 0)"):
        add("WARN", "BODY_BLACK", "body text is pure black%s; dark grey reads easier" % (
            ": " + listing(t["name"] for t in blacks) if blacks else ""))
    if view_width == widest and len(facts["h1"]) == 1:
        sizes = {}
        for t in text:
            sizes[t["size"]] = sizes.get(t["size"], 0) + t["chars"]
        body_size = max(sizes, key=sizes.get) if sizes else facts["body_element"]["size"]
        ratio = facts["h1"][0]["size"] / body_size if body_size else 0
        if not 3 <= ratio <= 4:
            add("WARN", "HEADLINE_RATIO", "the headline is %.2f times the body size (%gpx over %gpx); three to four is the rule" % (
                ratio, facts["h1"][0]["size"], body_size))
    if markup:
        if not facts["has_nav"] and not args.landing:
            add("WARN", "NAV", "no nav element holds a link; pass --landing for a page built without a menu on purpose")
        if facts["autoplay"]:
            add("WARN", "AUTOPLAY", "autoplaying video: %s" % listing(facts["autoplay"]))
        if facts["sliders"]:
            add("WARN", "SLIDER", "slider or carousel markup: %s" % listing(facts["sliders"]))
    return rows


def read_view(recorder, browser, major, url, width, timeout_ms, args):
    """One page at one width in its own context (contexts are never closed: browser.close() ends them).

    Returns (status, final_url, facts or None, detail). detail is why the page was not read, else None."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    mobile = width < PHONE_BELOW
    height = PHONE_HEIGHT if mobile else DESKTOP_HEIGHT
    context = cro_runtime.guarded_context(browser, recorder, major=major, width=width, height=height,
                                          mobile=mobile, reduced_motion="reduce")
    page = cro_runtime.guarded_page(context, recorder)
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except PlaywrightError as error:
        return None, None, None, first_line(error)
    status = response.status if response else None
    if status != 200:
        return status, page.url, None, "HTTP %s" % status if status is not None else "no response"
    try:
        # the load event gets a third of the timeout, 15 s at most; the pass carries on without it
        try:
            page.wait_for_load_state("load", timeout=min(timeout_ms / 3, 15000))
        except PlaywrightTimeoutError:
            pass
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
        action = None
        if args.action_color:
            action = [int(args.action_color[i:i + 2], 16) for i in (1, 3, 5)]
        facts = page.evaluate(MEASURE_PAGE, {"label": args.label, "action": action})
    except PlaywrightError as error:
        return status, page.url, None, first_line(error)
    return status, page.url, facts, None


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except BadInput as error:
        print("launch_render: %s" % error, file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("launch_render: Playwright is not installed; run setup.py", file=sys.stderr)
        return 3
    out_dir = Path(args.out)
    widest = max(args.widths)
    recorders, pages = [], []
    lines = []
    fails = warns = 0
    playwright = sync_playwright().start()
    browser = None
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "user_agent": None, "widths": args.widths,
              "deck": args.deck, "variant": args.variant_used, "label": args.label, "label_key": args.label_key,
              "action_color": args.action_color, "landing": args.landing, "pages": pages, "errors": [], "fail": 0, "warn": 0}
    try:
        try:
            browser = cro_runtime.guarded_launch(playwright)
            major = int(browser.version.split(".")[0])
        except PlaywrightError as error:
            print("launch_render: the browser could not start: %s" % first_line(error), file=sys.stderr)
            return 3
        result["user_agent"] = cro_runtime.chrome_ua(major)
        for url in args.urls:
            entry = {"url": url, "final_url": None, "views": []}
            pages.append(entry)
            reads = {}
            for width in args.widths:
                recorder = cro_runtime.Recorder()
                recorders.append(recorder)
                try:
                    status, final_url, facts, detail = read_view(recorder, browser, major, url, width, int(args.timeout * 1000), args)
                except PlaywrightError as error:
                    status, final_url, facts, detail = None, None, None, first_line(error)
                view = {"width": width, "height": PHONE_HEIGHT if width < PHONE_BELOW else DESKTOP_HEIGHT,
                        "status": status, "findings": []}
                entry["views"].append(view)
                if final_url:
                    entry["final_url"] = final_url
                if facts is None:
                    view["findings"].append({"level": "FAIL", "rule": "STATUS", "detail": one_line(detail)})
                else:
                    reads[width] = (view, facts, recorder)
            readable = max(reads) if reads else None
            for width, (view, facts, recorder) in reads.items():
                rows = analyse(facts, args, widest, width, width == readable)
                if width == readable and widest not in reads:
                    rows.append(("SKIPPED", "HEADLINE_RATIO", "the widest view (%d px) did not load, so the headline ratio was not checked" % widest))
                # fetch() is what rejects with these texts: the guard can be the cause only when it stopped a fetch
                # and no fetch failed on its own (rows are made before recorder.finish(), so one still under way is not failed)
                blocked = sum(1 for e in recorder.entries if e["resource_type"] == "fetch" and e["outcome"] == "blocked")
                failed = any(e["resource_type"] == "fetch" and e["outcome"] == "failed" for e in recorder.entries)
                for e in recorder.errors:
                    if blocked and not failed and any(t in e for t in NETWORK_FAILURES):
                        rows.append(("WARN", "PAGE_ERROR", "%s; the guard blocked %d fetch request(s) on this view, so this may be its own doing: confirm in an ordinary browser" % (one_line(e)[:300], blocked)))
                    else:
                        rows.append(("FAIL", "PAGE_ERROR", one_line(e)[:300]))
                view["findings"].extend({"level": lv, "rule": rule, "detail": detail} for lv, rule, detail in rows)
            for view in entry["views"]:
                for f in view["findings"]:
                    lines.append("%s %s@%d %s: %s" % (f["level"], url, view["width"], f["rule"], f["detail"]))
                    fails += f["level"] == "FAIL"
                    warns += f["level"] == "WARN"
        log = []
        for recorder in recorders:
            log.extend(recorder.finish())
            for text in recorder.errors:
                if text not in result["errors"]:
                    result["errors"].append(text)
        result["fail"], result["warn"] = fails, warns
        write_json(out_dir / "network-log.json", log)
        write_json(out_dir / "launch.json", result)
    finally:
        if browser is not None:
            try:
                browser.close()
            except PlaywrightError:
                pass
        playwright.stop()
    for text in lines:
        print(text)
    print("launch_render: %d FAIL, %d WARN" % (fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
