"""Side stars on wide screens (TASK-018): CSS only, beside the content column, scattered."""

import re
from itertools import pairwise
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
TILE = 1600
WIDE = ("(min-width: 64rem)", "(min-width: 80rem)", "(min-width: 100rem)")
GROUP_SIZES = {"a": 8, "b": 8, "c": 10}
TIERS = {"(min-width: 64rem)": "a", "(min-width: 80rem)": "ab", "(min-width: 100rem)": "abc"}
STAR_IMAGES = {"var(--star-yellow)", "var(--star-lilac)"}
SIDES = (".site-main::before", ".site-main::after")


def _css() -> str:
    text = (BASE / "static/css/theme.css").read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _media_blocks(css: str) -> tuple[list[tuple[str, str]], str]:
    """Return ([(condition, body)] of the top-level @media blocks, the CSS outside them)."""
    blocks, outside, i = [], [], 0
    while True:
        start = css.find("@media", i)
        if start == -1:
            outside.append(css[i:])
            return blocks, "".join(outside)
        outside.append(css[i:start])
        open_brace = css.index("{", start)
        depth = 0
        for j in range(open_brace, len(css)):
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        blocks.append((css[start + len("@media") : open_brace].strip(), css[open_brace + 1 : j]))
        i = j + 1


def _rules(css: str) -> list[tuple[list[str], str]]:
    return [
        ([part.strip() for part in sel.split(",")], body)
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    ]


def _decl(body: str, name: str) -> str | None:
    match = re.search(rf"(?:^|[;{{\s]){re.escape(name)}\s*:\s*([^;]+);", body)
    return " ".join(match.group(1).split()) if match else None


def _block(condition: str) -> str:
    blocks, _ = _media_blocks(_css())
    bodies = [body for cond, body in blocks if cond == condition]
    if not bodies:
        raise AssertionError(f"no @media {condition} block")
    return "\n".join(bodies)


def _rule_in(css: str, selector: str, alone: bool = False) -> str:
    return "\n".join(
        body
        for selectors, body in _rules(css)
        if selector in selectors and (not alone or selectors == [selector])
    )


def _stars(side: str) -> dict[str, list[tuple[str, int, int]]]:
    body = _rule_in(_block(WIDE[0]), side, alone=True)
    groups = {}
    for group in GROUP_SIZES:
        images = _decl(body, f"--stars-{group}-image")
        positions = _decl(body, f"--stars-{group}-position")
        if images is None or positions is None:
            raise AssertionError(f"{side}: group {group} missing")
        image_list = [part.strip() for part in images.split(",")]
        position_list = [part.strip() for part in positions.split(",")]
        if len(image_list) != len(position_list):
            raise AssertionError(f"{side}: group {group} image/position counts differ")
        stars = []
        for image, position in zip(image_list, position_list, strict=True):
            match = re.fullmatch(r"(\d+)% (\d+)px", position)
            if not match:
                raise AssertionError(f"{side}: bad position {position!r}")
            stars.append((image, int(match.group(1)), int(match.group(2))))
        groups[group] = stars
    return groups


def _dy(a: int, b: int) -> int:
    d = abs(a - b)
    return min(d, TILE - d)


class WideStarsPlacementTests(SimpleTestCase):
    def test_narrow_screens_keep_edge_stars(self):
        blocks, outside = _media_blocks(_css())
        self.assertIn("left: 4px", _rule_in(outside, "body::before"))
        self.assertIn("box-shadow", _rule_in(outside, "body::before"))
        self.assertIn("right: 5px", _rule_in(outside, "body::after"))
        for side in SIDES:
            with self.subTest(side=side):
                self.assertEqual(_rule_in(outside, side), "")
                for condition, body in blocks:
                    if condition not in WIDE:
                        self.assertEqual(_rule_in(body, side), "", condition)

    def test_wide_screens_hide_edge_columns(self):
        block = _block(WIDE[0])
        for selector in ("body::before", "body::after"):
            with self.subTest(selector=selector):
                self.assertEqual(_decl(_rule_in(block, selector), "display"), "none")

    def test_layers_beside_content_column(self):
        block = _block(WIDE[0])
        shared = "\n".join(body for selectors, body in _rules(block) if selectors == list(SIDES))
        expected = {
            "content": '""',
            "position": "absolute",
            "top": "0",
            "bottom": "0",
            "width": "calc(50vw - 50% - 1rem)",
            "pointer-events": "none",
            "z-index": "-1",
            "background-size": "3px 1600px",
            "background-repeat": "no-repeat repeat",
        }
        for name, value in expected.items():
            with self.subTest(declaration=name):
                self.assertEqual(_decl(shared, name), value)
        self.assertEqual(_decl(_rule_in(block, SIDES[0], alone=True), "right"), "100%")
        self.assertEqual(_decl(_rule_in(block, SIDES[1], alone=True), "left"), "100%")

    def test_stars_are_token_coloured_gradients(self):
        shared = _rule_in(_block(WIDE[0]), SIDES[0])
        self.assertEqual(
            _decl(shared, "--star-yellow"),
            "linear-gradient(var(--color-star-yellow) 0 3px, transparent 3px)",
        )
        self.assertEqual(
            _decl(shared, "--star-lilac"),
            "linear-gradient(var(--color-star-lilac) 0 3px, transparent 3px)",
        )
        for condition in WIDE:
            with self.subTest(condition=condition):
                self.assertNotIn("url(", _block(condition))

    def test_breakpoints_add_groups(self):
        for condition, groups in TIERS.items():
            body = _rule_in(_block(condition), SIDES[0])
            with self.subTest(condition=condition):
                self.assertEqual(
                    _decl(body, "background-image"),
                    ", ".join(f"var(--stars-{g}-image)" for g in groups),
                )
                self.assertEqual(
                    _decl(body, "background-position"),
                    ", ".join(f"var(--stars-{g}-position)" for g in groups),
                )

    def test_no_star_markup_or_inline_style(self):
        base = (BASE / "templates/base.html").read_text(encoding="utf-8")
        self.assertNotRegex(base, r'class="[^"]*\bstar')
        self.assertNotIn("style=", base)


class WideStarsScatterTests(SimpleTestCase):
    """The stars of every breakpoint form no column, row or straight line (the old "ladder")."""

    def test_group_sizes_and_values(self):
        for side in SIDES:
            for group, stars in _stars(side).items():
                with self.subTest(side=side, group=group):
                    self.assertEqual(len(stars), GROUP_SIZES[group])
                    self.assertTrue({image for image, _, _ in stars} <= STAR_IMAGES)
                    self.assertEqual({image for image, _, _ in stars}, STAR_IMAGES)
                    for _, x, y in stars:
                        self.assertTrue(0 <= x <= 100 and 0 <= y < TILE, (x, y))

    def _tiers(self):
        for side in SIDES:
            groups = _stars(side)
            for condition, names in TIERS.items():
                yield side, condition, [(x, y) for n in names for _, x, y in groups[n]]

    def test_no_columns(self):
        # Two stars closer than 400 px vertically are at least 6 % of the margin apart.
        for side, condition, stars in self._tiers():
            with self.subTest(side=side, condition=condition):
                for i, a in enumerate(stars):
                    for b in stars[i + 1 :]:
                        if _dy(a[1], b[1]) < 400:
                            self.assertGreaterEqual(abs(a[0] - b[0]), 6, (a, b))

    def test_no_rows_or_lines(self):
        for side, condition, stars in self._tiers():
            ordered = sorted(stars, key=lambda s: s[1])
            with self.subTest(side=side, condition=condition):
                for a, b, c in zip(ordered, ordered[1:], ordered[2:], strict=False):
                    # Three neighbours never share a 48 px band (a row) ...
                    self.assertGreaterEqual(c[1] - a[1], 48, (a, b, c))
                    # ... and the middle one is off the line through the outer two (no ladder).
                    t = (b[1] - a[1]) / (c[1] - a[1])
                    self.assertGreaterEqual(abs(a[0] + (c[0] - a[0]) * t - b[0]), 10, (a, b, c))

    def test_spread_over_whole_margin(self):
        for side, condition, stars in self._tiers():
            xs = [x for x, _ in stars]
            ys = sorted(y for _, y in stars)
            with self.subTest(side=side, condition=condition):
                self.assertLessEqual(min(xs), 10)
                self.assertGreaterEqual(max(xs), 90)
                gaps = [b - a for a, b in pairwise(ys)] + [ys[0] + TILE - ys[-1]]
                self.assertLessEqual(max(gaps), 400)
