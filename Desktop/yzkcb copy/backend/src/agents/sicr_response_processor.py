"""
SICR / Change Response Post-Processor

This module ensures that every chatbot response related to SICR / Change Management
includes a reference link to the provided Change Management guidance PDF document.

Behavior mirrors the APQP processor: case-insensitive keyword detection, prevent
duplicate URL insertion, and include a friendly short intro plus a labeled link.
"""

import re
from typing import Optional


# Default SICR / Change PDF URL provided by the user
DEFAULT_SICR_PDF_URL = (
    "https://drive.google.com/file/d/10xr2UwKx4aXm6NWrOzER7Zv899uq_5zD/view?usp=sharing"
)


class SICRResponseProcessor:
    """
    Post-processor for SICR / Change-related chatbot responses.
    """

    def __init__(self, pdf_url: Optional[str] = None):
        self.pdf_url = pdf_url or DEFAULT_SICR_PDF_URL
        # Friendly label used when linking the PDF
        self.pdf_label = "SICR & Change Management Guide"

        # Patterns for detection
        self.sicr_pattern = re.compile(r"\bSICR\b", re.IGNORECASE)
        self.change_request_pattern = re.compile(r"\bchange\s+request\b", re.IGNORECASE)
        self.change_management_pattern = re.compile(r"\bchange\s+management\b", re.IGNORECASE)

        # A submission-related pattern to catch phrases like 'submit a change',
        # 'submit a change request', 'submitting a change', etc.
        self.submission_pattern = re.compile(
            r"\b(?:submit|submitting|submitted)\b(?:\s+(?:a|the))?(?:\s+change)?(?:\s+request)?\b",
            re.IGNORECASE,
        )

        # Check if PDF URL already present (escape URL for regex)
        escaped_url = re.escape(self.pdf_url)
        self.url_exists_pattern = re.compile(escaped_url, re.IGNORECASE)

    def is_sicr_or_change_related(self, text: Optional[str]) -> bool:
        """Return True if text mentions SICR or change-related phrases."""
        if not text:
            return False

        if self.sicr_pattern.search(text):
            return True

        if self.change_request_pattern.search(text):
            return True

        if self.change_management_pattern.search(text):
            return True

        # Also treat 'change' in submission context as related
        if self.submission_pattern.search(text):
            return True

        return False

    def has_pdf_url(self, text: Optional[str]) -> bool:
        if not text:
            return False
        return bool(self.url_exists_pattern.search(text))

    def append_pdf_reference(self, response: str) -> str:
        """Append the Change Management PDF reference to the response."""
        top_phrase = (
            "**For guidance on SICR and Change Management processes through the supplier portal <a href=\"https://yazakieurope.empowerqlm.com/Dashboard\" target=\"_blank\">EmpowerQLM</a>, see the guide below:**"
            "\n\n"
        )

        reference = f"📘 **<a href=\"{self.pdf_url}\" target=\"_blank\">{self.pdf_label}</a>**"

        return response + "\n\n" + top_phrase + reference

    def process(self, user_question: Optional[str], bot_response: str) -> str:
        """Analyze inputs and append PDF link when relevant."""
        is_related = (
            self.is_sicr_or_change_related(user_question)
            or self.is_sicr_or_change_related(bot_response)
        )

        if not is_related:
            return bot_response

        if self.has_pdf_url(bot_response):
            return bot_response

        return self.append_pdf_reference(bot_response)


def process_sicr_response(user_question: Optional[str], bot_response: str, pdf_url: Optional[str] = None) -> str:
    """Convenience function to process a single response."""
    processor = SICRResponseProcessor(pdf_url=pdf_url)
    return processor.process(user_question, bot_response)


# --------------------
# Unit tests
# --------------------
def run_tests():
    print("=" * 70)
    print("SICR Response Processor - Unit Tests")
    print("=" * 70)

    test_pdf_url = DEFAULT_SICR_PDF_URL
    processor = SICRResponseProcessor(pdf_url=test_pdf_url)

    # Test 1: SICR detection
    print("\n✓ Test 1: SICR detection")
    assert processor.is_sicr_or_change_related("What is SICR?"), "SICR should be detected"
    assert processor.is_sicr_or_change_related("Tell me about sicr"), "case-insensitive SICR"
    print("  ✅ SICR detected")

    # Test 2: Change Request phrase
    print("\n✓ Test 2: Change Request detection")
    assert processor.is_sicr_or_change_related("How do I submit a change request?"), "change request"
    assert processor.is_sicr_or_change_related("Change Request process"), "direct phrase"
    print("  ✅ Change request detected")

    # Test 3: Change Management phrase
    print("\n✓ Test 3: Change Management detection")
    assert processor.is_sicr_or_change_related("What is Change Management?"), "change management"
    assert processor.is_sicr_or_change_related("change management policies"), "phrase"
    print("  ✅ Change management detected")

    # Test 4: Submission context with 'change'
    print("\n✓ Test 4: Submission context detection")
    assert processor.is_sicr_or_change_related("I want to submit a change"), "submission with change"
    assert processor.is_sicr_or_change_related("Submitting a change request now"), "submitting phrase"
    print("  ✅ Submission context detected")

    # Test 5: Avoid false positives for unrelated 'change' mentions
    print("\n✓ Test 5: Avoid unrelated 'change' false positives")
    assert not processor.is_sicr_or_change_related("It would be nice to change the color of my avatar"), "not a change request"
    print("  ✅ Unrelated 'change' ignored")

    # Test 6: URL append
    print("\n✓ Test 6: Append PDF link")
    resp = processor.process("How do I submit a change request?", "You can submit via the portal.")
    assert test_pdf_url in resp
    print("  ✅ PDF link appended")

    # Test 7: No append for unrelated responses
    print("\n✓ Test 7: No append for unrelated responses")
    resp = processor.process("What is PPAP?", "PPAP is Production Part Approval Process.")
    assert test_pdf_url not in resp
    print("  ✅ Unrelated responses unchanged")

    # Test 8: Don't duplicate URL
    print("\n✓ Test 8: Prevent duplicate URL")
    response_with_url = f"See docs: {test_pdf_url}"
    resp = processor.process("What is SICR?", response_with_url)
    assert resp.count(test_pdf_url) == 1
    print("  ✅ Duplicate prevented")

    print("\n" + "=" * 70)
    print("✅ ALL SICR TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
