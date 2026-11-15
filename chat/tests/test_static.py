"""Static analysis tests for chat.js."""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ChatJsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.js = (Path(settings.BASE_DIR) / "static/js/chat.js").read_text()

    def test_no_forbidden_apis(self):
        forbidden = (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "document.write",
            "eval(",
            "new Function",
            "setInterval",
        )
        for token in forbidden:
            self.assertNotIn(token, self.js)

    def test_uses_required_apis(self):
        required = (
            "DOMParser",
            "visibilitychange",
            "X-Chat-Fragment",
            "importNode",
            "data-chat-poll-url",
            "chatPollUrl",
            "textContent",
        )
        for token in required:
            self.assertIn(token, self.js)

    def test_strict_iife(self):
        self.assertTrue(self.js.startswith("(function () {"))
        self.assertIn('"use strict"', self.js)

    def test_single_loop_guard(self):
        self.assertIn("var inFlight = false;", self.js)
        self.assertIn("if (inFlight || stopped)", self.js)
        self.assertIn("!inFlight", self.js)
