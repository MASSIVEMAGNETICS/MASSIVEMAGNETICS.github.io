"""Regression checks for B Heard's non-authoritative Stripe return page."""

from __future__ import annotations

import unittest
from pathlib import Path

RETURN_PAGE = Path(__file__).resolve().parents[1] / "network" / "thanks" / "index.html"


class BHeardCheckoutReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = RETURN_PAGE.read_text(encoding="utf-8")

    def test_return_is_explicitly_unverified(self) -> None:
        self.assertIn("This page cannot confirm whether a payment succeeded.", self.page)
        self.assertIn("only after payment and required information are independently verified", self.page)
        self.assertNotIn("after completing checkout", self.page)

    def test_return_event_cannot_be_mistaken_for_payment(self) -> None:
        self.assertIn("event: 'checkout_return_unverified'", self.page)
        self.assertNotIn("event: 'checkout_return'", self.page)
        self.assertNotIn("event: 'payment_verified'", self.page)

    def test_support_and_noindex_are_preserved(self) -> None:
        self.assertIn('content="noindex,nofollow"', self.page)
        self.assertIn('href="/network/"', self.page)
        self.assertIn("mailto:bandobandz440@gmail.com", self.page)


if __name__ == "__main__":
    unittest.main()
