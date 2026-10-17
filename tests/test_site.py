"""Content and structure checks for the case study page (stdlib only)."""

import base64
import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
CSS = ROOT / "assets" / "css" / "styles.css"

# Base64-encoded so this file, which is published with the site, doesn't
# itself contain the phrases it bans.
FORBIDDEN = [base64.b64decode(p).decode() for p in ['Y291cnNl', 'Y2xhc3MgcHJvamVjdA==', 'XGJjZW5cYg==', 'NDcyMg==', 'ZmFsbCAyMDI2', 'bWlsZXN0b25l', 'YXNzaWdubWVudA==', 'cHJvZmVzc29y', 'XGJncmFkZXM/XGI=', 'ZGVsaXZlcmFibGU=']]
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}


class SiteParser(HTMLParser):
    """Collects the bits of index.html the tests assert on."""

    def __init__(self):
        super().__init__()
        self.imgs, self.links, self.scripts, self.meta = [], [], [], []
        self.anchors, self.ids, self.elements = [], [], []
        self.title = ""
        self.section_text = {}
        self._text, self._stack, self._skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        a["_tag"] = tag
        a["_classes"] = (a.get("class") or "").split()
        a["_ancestors"] = [dict(e) for e in self._stack]
        self.elements.append(a)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "img":
            self.imgs.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "script":
            self.scripts.append(a)
        elif tag == "meta":
            self.meta.append(a)
        elif tag == "a":
            a["_imgs"] = []
            self.anchors.append(a)
        if tag == "img":
            for anc in self._stack:
                if anc["_tag"] == "a":
                    anc["_imgs"].append(a)
        if tag in ("script", "style", "title"):
            self._skip += 1
        if tag not in VOID:
            self._stack.append(a)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "title"):
            self._skip = max(0, self._skip - 1)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i]["_tag"] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._stack and self._stack[-1]["_tag"] == "title":
            self.title += data
        if not self._skip:
            self._text.append(data)
            sid = next((e.get("id") for e in reversed(self._stack)
                        if e["_tag"] in ("section", "header") and e.get("id")), None)
            self.section_text.setdefault(sid, []).append(data)

    def section(self, sid):
        return re.sub(r"\s+", " ", " ".join(self.section_text.get(sid, [])))

    @property
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self._text))


def load_html():
    return INDEX.read_text(encoding="utf-8")


def parse():
    p = SiteParser()
    p.feed(load_html())
    return p


def by_class(p, cls):
    return [e for e in p.elements if cls in e["_classes"]]


class TestSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = parse()
        cls.html = load_html()

    # --- Task 1 ---------------------------------------------------------
    def test_forbidden_words_absent(self):
        low = self.html.lower()
        for pat in FORBIDDEN:
            self.assertIsNone(re.search(pat, low), f"forbidden: {pat}")

    def test_published_files_have_no_forbidden_words(self):
        # GitHub Pages serves every tracked file, not just index.html.
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.split()
        for name in files:
            path = ROOT / name
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf"}:  # binary; the resume is Shashank's own document
                continue
            low = path.read_text(encoding="utf-8", errors="ignore").lower()
            for pat in FORBIDDEN:
                self.assertIsNone(re.search(pat, low), f"{name}: forbidden {pat}")

    def test_paths_are_relative(self):
        attrs = [(e, "src") for e in self.p.imgs + self.p.scripts]
        attrs += [(e, "href") for e in self.p.links + self.p.anchors]
        for e, key in attrs:
            v = e.get(key)
            if not v or v.startswith(("https://", "mailto:", "#")):
                continue
            self.assertFalse(v.startswith("/"), f"root-relative path: {v}")

    def test_images_have_alt_and_size(self):
        self.assertTrue(self.p.imgs, "no images found")
        for img in self.p.imgs:
            src = img.get("src", "")
            self.assertTrue((img.get("alt") or "").strip(), f"missing alt: {src}")
            self.assertTrue(img.get("width") and img.get("height"), f"missing size: {src}")
            self.assertTrue((ROOT / src).is_file(), f"missing file: {src}")

    def test_only_allowed_externals(self):
        for s in self.p.scripts:
            src = s.get("src", "")
            self.assertFalse(src.startswith(("http://", "https://", "//")), f"external script: {src}")
        for link in self.p.links:
            href = link.get("href", "")
            if href.startswith(("http://", "https://", "//")):
                self.assertIn(urlparse(href).hostname, ALLOWED_HOSTS, href)

    def test_hero_content(self):
        self.assertEqual(self.p.ids[0], "hero")
        for s in ["Your bus dropped off the map.", "HeadsUp"]:
            self.assertIn(s, self.p.text)
        # Labels are uppercased by CSS, so match them case-insensitively.
        for s in ["problem", "what i did", "outcome", "role"]:
            self.assertIn(s, self.p.text.lower())


    # --- Task 2 ---------------------------------------------------------
    def test_section_order(self):
        order = ["hero", "problem", "research", "decision", "design", "status"]
        found = [i for i in self.p.ids if i in order]
        self.assertEqual(found, order)

    def test_problem_facts(self):
        for s in ["1.1★", "235", "Google Maps"]:
            self.assertIn(s, self.p.text)

    def test_research_content(self):
        for s in ["designed in the 90s", "N1", "N2", "N3", "N4", "N5",
                  "Maya Garcia", "Jordan Lee", "The Daily Commuter", "The Occasional Rider"]:
            self.assertIn(s, self.p.text)

    def test_no_persona_photos(self):
        for img in self.p.imgs:
            src = img.get("src", "").lower()
            for bad in ("persona", "image5", "image6"):
                self.assertNotIn(bad, src)


    # --- Task 3 ---------------------------------------------------------
    def test_decision_content(self):
        for s in ["24 ideas", "HeadsUp", "Where2", "91", "89",
                  "New", "Useful", "Feasible", "preferences matched"]:
            self.assertIn(s, self.p.text)


    # --- Task 4 ---------------------------------------------------------
    def test_walkthrough_steps(self):
        steps = by_class(self.p, "step")
        self.assertEqual(len(steps), 8)
        self.assertEqual([s.get("data-step") for s in steps],
                         [f"{i:02d}" for i in range(1, 9)])
        step_imgs = [i for i in self.p.imgs
                     if any("step" in a["_classes"] for a in i["_ancestors"])]
        self.assertEqual(len(step_imgs), 8)
        for n, img in enumerate(step_imgs, 1):
            self.assertIn(f"assets/img/wf-{n:02d}-", img.get("src", ""))
            self.assertGreater(len(img.get("alt", "")), 20, img.get("src"))

    def test_wireflow_fallback_link(self):
        links = [a for a in self.p.anchors if a.get("href") == "assets/img/wireflow.png"]
        self.assertEqual(len(links), 1)
        self.assertTrue(any(i.get("src") == "assets/img/wireflow.png" for i in links[0]["_imgs"]))


    # --- Task 5 ---------------------------------------------------------
    def test_status_content(self):
        for s in ["usability test", "clickable prototype", "preferences matched"]:
            self.assertIn(s, self.p.text)
        self.assertNotIn("usability tested", self.p.text)
        status = self.p.text.split("Where it stands", 1)[-1]
        self.assertNotIn("%", status)

    def test_meta_tags(self):
        self.assertTrue(self.p.title.strip())
        named = {m.get("name") or m.get("property"): m.get("content") for m in self.p.meta}
        for key in ["description", "og:title", "og:description", "og:image", "og:type"]:
            self.assertTrue(named.get(key), f"missing meta {key}")
        base = "https://shashank-navale.github.io/rts-app-redesign/"
        self.assertTrue(named["og:image"].startswith(base), "og:image must be absolute")
        self.assertTrue((ROOT / named["og:image"][len(base):]).is_file())
        icons = [l for l in self.p.links if l.get("rel") == "icon"]
        self.assertEqual([l.get("href") for l in icons], ["assets/favicon.svg"])
        self.assertTrue((ROOT / "assets/favicon.svg").is_file())

    def test_reveal_hidden_only_with_js_class(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", css)
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for m in re.finditer(r"([^{}]+)\{[^{}]*opacity:\s*0\s*;", css):
            for sel in m.group(1).split(","):
                self.assertTrue(sel.strip().startswith(".js "), f"hidden without .js: {sel.strip()}")

    def test_footer_placeholders_marked(self):
        footer = [a for a in self.p.anchors
                  if any(x["_tag"] == "footer" for x in a["_ancestors"])]
        self.assertTrue(footer, "no footer links")
        for a in footer:
            if a.get("href") == "#":
                self.assertEqual(a.get("data-placeholder"), "true")


    # --- Sticky menu ----------------------------------------------------
    def test_nav_links_point_to_real_sections(self):
        links = [a for a in self.p.anchors
                 if any("topbar-links" in x["_classes"] for x in a["_ancestors"])]
        self.assertGreaterEqual(len(links), 4)
        for a in links:
            self.assertTrue(a["href"].startswith("#"), a["href"])
            self.assertIn(a["href"][1:], self.p.ids)

    def test_nav_sits_outside_hero(self):
        # position: sticky only works if no ancestor clips overflow; the hero does.
        nav = by_class(self.p, "topbar")
        self.assertEqual(len(nav), 1)
        self.assertEqual(nav[0]["_tag"], "nav")
        self.assertFalse(any(x["_tag"] == "header" for x in nav[0]["_ancestors"]))

    def test_nav_is_sticky_and_never_hidden(self):
        css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
        topbar = re.search(r"(?<![\w-])\.topbar\s*\{([^}]*)\}", css)
        self.assertIsNotNone(topbar)
        self.assertIn("position: sticky", topbar.group(1))
        self.assertIn("top: 0", topbar.group(1))
        for m in re.finditer(r"\.topbar-links[^{]*\{([^}]*)\}", css):
            self.assertNotIn("display: none", m.group(1), "menu links must stay visible on phones")
        self.assertIn("scroll-padding-top", css)


    # --- Menu highlight, more screenshots, real contact links -----------
    def test_problem_has_three_current_app_screenshots(self):
        shots = [i for i in self.p.imgs
                 if i.get("src", "").startswith("assets/img/rts-current-")
                 and any(a.get("id") == "problem" for a in i["_ancestors"])]
        self.assertEqual(len(shots), 3)
        for img in shots:
            self.assertGreater(len(img.get("alt", "")), 40, img.get("src"))

    def test_footer_contact_links_are_real(self):
        footer = [a for a in self.p.anchors
                  if any(x["_tag"] == "footer" for x in a["_ancestors"])]
        self.assertEqual([a["href"] for a in footer],
                         ["https://www.linkedin.com/in/shashank-navale/",
                          "mailto:shashanknavale@ufl.edu",
                          "assets/Shashank_Navale_Resume.pdf"])
        for a in footer:
            self.assertNotIn("data-placeholder", a)
        for a in (footer[0], footer[2]):
            self.assertIn("noopener", a.get("rel", ""))
            self.assertEqual(a.get("target"), "_blank")
        self.assertTrue((ROOT / "assets/Shashank_Navale_Resume.pdf").is_file())

    def test_menu_marks_current_section(self):
        css = CSS.read_text(encoding="utf-8")
        js = (ROOT / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn('.topbar-links a[aria-current="true"]', css)
        self.assertIn("aria-current", js)


    # --- Critique fixes: enlargeable wireframes ---------------------------
    def test_every_wireframe_is_enlargeable(self):
        steps = by_class(self.p, "step")
        opens = [a for a in self.p.anchors if "step-open" in a["_classes"]]
        self.assertEqual(len(opens), 8)
        for n, a in enumerate(opens, 1):
            # no-JS fallback: the link itself opens the full-size image
            self.assertTrue(a["href"].startswith(f"assets/img/wf-{n:02d}-"), a["href"])
            self.assertEqual(len(a["_imgs"]), 1)
            self.assertEqual(a["_imgs"][0]["src"], a["href"])
            self.assertTrue(a.get("aria-label", "").startswith("Enlarge"), a.get("aria-label"))
            self.assertTrue(any("step" in x["_classes"] for x in a["_ancestors"]))
        self.assertEqual(len(steps), 8)

    def test_screen_viewer_dialog_has_labelled_controls(self):
        self.assertIn("screen-dialog", self.p.ids)
        labels = [e.get("aria-label") for e in self.p.elements
                  if e["_tag"] == "button" and any(x.get("id") == "screen-dialog" for x in e["_ancestors"])]
        for want in ("Previous screen", "Next screen", "Close"):
            self.assertIn(want, labels)

    def test_screen_viewer_script_handles_keys_and_focus(self):
        js = (ROOT / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        for token in ("initScreenViewer", "ArrowRight", "ArrowLeft", "showModal", ".focus()"):
            self.assertIn(token, js)


    # --- Critique fixes: clarity and hierarchy -----------------------------
    def test_need_codes_only_appear_beside_their_legend(self):
        for sid in ("hero", "problem", "decision", "design", "status"):
            self.assertIsNone(re.search(r"\bN[1-5]\b", self.p.section(sid)),
                              f"need code outside research: {sid}")
        self.assertRegex(self.p.section("research"), r"\bN1\b")

    def test_decision_leads_with_the_verdict(self):
        text = self.p.section("decision")
        self.assertLess(text.index("Why HeadsUp"), text.index("Where2"))
        self.assertEqual(by_class(self.p, "funnel"), [], "heading already says 24 -> 2 -> 1")

    def test_problem_facts_are_a_list_not_cards(self):
        self.assertEqual(by_class(self.p, "stat"), [])
        lis = [e for e in self.p.elements if e["_tag"] == "li"
               and any("problem-facts" in a["_classes"] for a in e["_ancestors"])]
        self.assertEqual(len(lis), 3)

    def test_pullquote_is_smaller_than_section_headings(self):
        css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)

        def max_rem(selector):
            rule = re.search(selector + r"\s*\{([^}]*)\}", css)
            self.assertIsNotNone(rule, selector)
            size = re.search(r"font-size:\s*clamp\([^,]+,[^,]+,\s*([\d.]+)rem\)", rule.group(1))
            self.assertIsNotNone(size, selector)
            return float(size.group(1))

        self.assertLess(max_rem(r"\.pullquote blockquote p"), max_rem(r"(?<![\w.-])h2"))

    def test_callout_has_no_colored_side_border(self):
        css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
        for rule in re.finditer(r"\.callout\s*\{([^}]*)\}", css):
            self.assertNotIn("border-left", rule.group(1))


    # --- Critique fixes: type floor, contrast, touch targets ---------------
    @staticmethod
    def _css_text():
        return re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)

    @staticmethod
    def _contrast(fg, bg):
        def lum(hex_):
            r, g, b = (int(hex_.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
            f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
        hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    def test_no_text_smaller_than_12px(self):
        for m in re.finditer(r"font-size:\s*([^;]+);", self._css_text()):
            value = m.group(1).strip()
            first = re.match(r"(?:clamp\()?\s*([\d.]+)(rem|px)", value)
            if not first:
                continue
            px = float(first.group(1)) * (16 if first.group(2) == "rem" else 1)
            self.assertGreaterEqual(px, 12, f"font-size: {value}")

    def test_persona_needs_line_is_sized_and_contrasty(self):
        css = self._css_text()
        tokens = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", css))
        self.assertGreaterEqual(self._contrast(tokens["accent-deep"], tokens["panel"]), 4.5)
        rule = re.search(r"\.persona \.persona-needs\s*\{([^}]*)\}", css)
        self.assertIsNotNone(rule, "needs a class-level rule that is not outranked by '.persona > p'")
        self.assertIn("var(--accent-deep)", rule.group(1))
        self.assertIn("font-size: 0.75rem", rule.group(1))
        self.assertNotIn("!important", rule.group(1))

    def test_touch_targets_are_at_least_44px(self):
        css = self._css_text()
        for selector in (r"\.footer-links a", r"\.topbar-name"):
            rule = re.search(selector + r"\s*\{([^}]*)\}", css)
            self.assertIsNotNone(rule, selector)
            self.assertIn("min-height: 44px", rule.group(1), selector)

    def test_hero_decoration_is_hidden_on_small_screens(self):
        self.assertRegex(self._css_text(),
                         r"@media \(max-width: 899px\)\s*\{\s*\.hero-route\s*\{\s*display: none;")


    # --- Section labels: larger, no dot separators, tied to the menu ------
    SECTION_LABELS = [("problem", "01 The problem"), ("research", "02 Research"),
                      ("decision", "03 The decision"), ("design", "04 The design"),
                      ("status", "05 Where it stands")]

    def test_no_middle_dot_separators(self):
        self.assertNotIn("\u00b7", self.html, "decorative middle-dot separators read as templated")

    def test_section_labels_are_a_number_then_a_name(self):
        labels = by_class(self.p, "section-label")
        self.assertEqual(len(labels), 5)
        self.assertEqual(len(by_class(self.p, "section-num")), 5)
        for sid, expected in self.SECTION_LABELS:
            text = self.p.section(sid).strip()
            self.assertTrue(text.startswith(expected + " "), f"{sid}: {text[:40]!r}")

    def test_section_labels_are_much_larger_than_the_old_12px(self):
        rule = re.search(r"\.section-label\s*\{([^}]*)\}", self._css_text())
        self.assertIsNotNone(rule)
        self.assertIn("font-size: 1.25rem", rule.group(1))

    def test_menu_has_a_link_for_every_section(self):
        links = {a["href"][1:] for a in self.p.anchors
                 if any("topbar-links" in x["_classes"] for x in a["_ancestors"])}
        for sid, _ in self.SECTION_LABELS:
            self.assertIn(sid, links)


    # --- Polish pass ------------------------------------------------------
    def test_no_em_dashes_in_page_copy(self):
        self.assertNotIn("\u2014", self.html)

    def test_close_buttons_are_text_labelled_and_44px(self):
        self.assertNotIn("\u2715", self.html, "a glyph is standing in for an icon")
        rule = re.search(r"\.lightbox-close\s*\{([^}]*)\}", self._css_text())
        self.assertIsNotNone(rule)
        self.assertIn("min-height: 44px", rule.group(1))

    def test_colors_come_from_tokens(self):
        outside_root = re.sub(r":root\s*\{[^}]*\}", "", self._css_text(), count=1)
        for literal in ("#fff", "#ffffff", "#a8a499", "#4a4a4a", "rgba(244"):
            self.assertNotIn(literal, outside_root, f"hard-coded {literal}; use a token")

    def test_sticky_menu_is_solid_not_glass(self):
        rule = re.search(r"(?<![\w-])\.topbar\s*\{([^}]*)\}", self._css_text())
        self.assertIsNotNone(rule)
        self.assertNotIn("backdrop-filter", rule.group(1))
        self.assertIn("var(--paper)", rule.group(1))

    def test_all_caps_is_reserved_for_short_labels(self):
        allowed = {".hero-meta dt", ".list-title", ".shot figcaption .mono",
                   ".status-tag", ".footer-sub"}
        for m in re.finditer(r"([^{}]+)\{([^}]*text-transform:\s*uppercase[^}]*)\}", self._css_text()):
            self.assertIn(m.group(1).strip(), allowed)

    def test_section_intro_has_a_comfortable_measure(self):
        rule = re.search(r"\.section-head h2 \+ p\s*\{([^}]*)\}", self._css_text())
        self.assertIsNotNone(rule)
        measure = re.search(r"max-width:\s*(\d+)ch", rule.group(1))
        self.assertIsNotNone(measure, "cap the intro line length in ch")
        self.assertLessEqual(int(measure.group(1)), 70)

    def test_spacing_values_sit_on_the_even_scale(self):
        for m in re.finditer(r"(?:padding|margin|gap)[a-z-]*:\s*([^;]+);", self._css_text()):
            for n in re.findall(r"(?<![\d.])(\d+)px", m.group(1)):
                self.assertEqual(int(n) % 2, 0, m.group(0))

    def test_dead_panel_style_is_gone(self):
        self.assertNotRegex(self._css_text(), r"(?<![\w-])\.panel\s*\{")

    def test_hero_image_loads_first(self):
        hero_imgs = [i for i in self.p.imgs if any(a.get("id") == "hero" for a in i["_ancestors"])]
        self.assertEqual(len(hero_imgs), 1)
        self.assertEqual(hero_imgs[0].get("fetchpriority"), "high")
        self.assertNotEqual(hero_imgs[0].get("loading"), "lazy")

    def test_buttons_have_a_pressed_state(self):
        css = self._css_text()
        for selector in (r"\.screen-prev", r"\.lightbox-close"):
            self.assertRegex(css, selector + r"[^{]*:active")


    # --- Quick-glance copy ---------------------------------------------------
    @staticmethod
    def _blocks(html):
        """Visible words of every paragraph-like block."""
        out = []
        for m in re.finditer(r"<(p|li|figcaption|dd)\b[^>]*>(.*?)</\1>", html, re.S):
            text = re.sub(r"<[^>]+>", " ", m.group(2))
            out.append((m.group(1), len(text.split()), " ".join(text.split())[:60]))
        return out

    def test_page_can_be_skimmed_in_about_two_minutes(self):
        words = len(self.p.text.split())
        self.assertLessEqual(words, 700, f"{words} words is too much for a recruiter's quick glance")

    def test_no_block_of_copy_runs_past_30_words(self):
        for tag, n, preview in self._blocks(self.html):
            self.assertLessEqual(n, 30, f"{n} words: {preview}")

    def test_hero_gives_the_whole_story_in_four_rows(self):
        rows = re.findall(r"<dt>(.*?)</dt>", self.html)
        self.assertEqual(rows, ["Problem", "What I did", "Outcome", "Role"])

    def test_walkthrough_captions_are_short(self):
        captions = re.findall(r'<div class="step-text">\s*<p class="step-time[^>]*>.*?</p>\s*<p>(.*?)</p>', self.html, re.S)
        self.assertEqual(len(captions), 8)
        for c in captions:
            self.assertLessEqual(len(re.sub(r"<[^>]+>", " ", c).split()), 10, c)

    def test_extra_reading_has_been_cut(self):
        for leftover in ("persona-desc", "Concept score", 'class="callout"', "score-note"):
            self.assertNotIn(leftover, self.html)


if __name__ == "__main__":
    unittest.main()
