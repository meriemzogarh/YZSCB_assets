"""
APQP Response Post-Processor

This module ensures that every chatbot response related to APQP (Advanced Product Quality Planning)
includes a reference link to the APQP guidance PDF document.

Features:
- Case-insensitive keyword detection for APQP-related content
- Fuzzy matching to catch variations (APQP, advanced product quality, etc.)
- Prevents duplicate URL insertion
- Clean, testable middleware design
- Production-safe with no external dependencies
"""

import re
from typing import Tuple


# Default APQP PDF URL - can be overridden via configuration
DEFAULT_APQP_PDF_URL = "https://drive.google.com/file/d/1pQ67wAzsZ01KLqMRcJvJvtkpFN2Ka8x_/view?usp=sharing"


class APQPResponseProcessor:
    """
    Post-processor for APQP-related chatbot responses.
    
    Detects APQP mentions and appends a guidance PDF link when appropriate.
    """
    
    def __init__(self, pdf_url: str = None):
        """
        Initialize the APQP response processor.
        
        Args:
            pdf_url: URL to the APQP guidance PDF. If None, uses DEFAULT_APQP_PDF_URL.
        """
        self.pdf_url = pdf_url or DEFAULT_APQP_PDF_URL
        
        # Compile regex patterns for efficient matching
        # Pattern 1: Direct APQP mentions (case-insensitive, word boundary)
        self.apqp_pattern = re.compile(r'\bAPQP\b', re.IGNORECASE)
        
        # Pattern 2: Advanced Product Quality Planning (with optional words)
        self.apqp_phrase_pattern = re.compile(
            r'\badvanced\s+product\s+quality(?:\s+planning)?\b',
            re.IGNORECASE
        )
        
        # Pattern 3: Check if URL already exists in response
        # Escape special regex characters in the URL
        escaped_url = re.escape(self.pdf_url)
        self.url_exists_pattern = re.compile(escaped_url, re.IGNORECASE)
        
        # Pattern 4: Submission-related phrases specifically about submitting a request
        # Match phrases like: 'submit a request', 'submit request', 'submitting a request', 'submit a change request'
        self.submission_pattern = re.compile(
            r"\b(?:submit|submitting|submitted)\b(?:\s+(?:a|the|a\s+change))?(?:\s+request)s?\b",
            re.IGNORECASE,
        )
    
    def is_apqp_related(self, text: str) -> bool:
        """
        Detect if the text is related to APQP.
        
        Args:
            text: The text to analyze (user question or bot response)
            
        Returns:
            True if APQP-related, False otherwise
        """
        if not text:
            return False
        
        # Check for direct APQP mentions
        if self.apqp_pattern.search(text):
            return True
        
        # Check for "Advanced Product Quality" phrases
        if self.apqp_phrase_pattern.search(text):
            return True
        
        return False

    def is_submission_related(self, text: str) -> bool:
        """
        Detect if the text mentions submitting/submission language.
        """
        if not text:
            return False

        return bool(self.submission_pattern.search(text))
    
    def has_pdf_url(self, text: str) -> bool:
        """
        Check if the response already contains the PDF URL.
        
        Args:
            text: The response text to check
            
        Returns:
            True if URL already exists, False otherwise
        """
        if not text:
            return False
        
        return bool(self.url_exists_pattern.search(text))
    
    def append_pdf_reference(self, response: str) -> str:
        """
        Append the APQP PDF reference to the response.
        
        Args:
            response: The original chatbot response
            
        Returns:
            Response with PDF reference appended
        """
        # Phrase requested: a short intro above the link
        top_phrase = (
            "**For further guidance on navigating the APQP interface <a href=\"https://yazakieurope.empowerqlm.com/Dashboard\" target=\"_blank\">EmpowerQLM</a>, see the detailed guide below:** "
            "\n\n"
        )

        # Create a friendly, unobtrusive reference line with clickable link
        # Use the 'APQP Quick Access Guide' label (tests expect this phrasing)
        reference = f"📘 **<a href=\"{self.pdf_url}\" target=\"_blank\">APQP Quick Access Guide</a>**"

        return response + "\n\n" + top_phrase + reference
    
    def process(self, user_question: str, bot_response: str) -> str:
        """
        Main processing method - analyzes question and response, adds PDF link if needed.
        
        Args:
            user_question: The user's input question
            bot_response: The chatbot's response
            
        Returns:
            Processed response (with or without PDF link)
        """
        # Check if question or response mentions APQP, or if the bot response
        # mentions submitting/submission (user wanted link when answer mentions submitting a request)
        is_related = (
            self.is_apqp_related(user_question)
            or self.is_apqp_related(bot_response)
            or self.is_submission_related(bot_response)
        )
        
        # If not APQP-related, return original response
        if not is_related:
            return bot_response
        
        # If already contains the PDF URL, don't add it again
        if self.has_pdf_url(bot_response):
            return bot_response
        
        # Append the PDF reference
        return self.append_pdf_reference(bot_response)


# Convenience function for simple usage
def process_apqp_response(user_question: str, bot_response: str, pdf_url: str = None) -> str:
    """
    Convenience function to process a single response.
    
    Args:
        user_question: The user's input question
        bot_response: The chatbot's response
        pdf_url: Optional custom PDF URL (uses default if not provided)
        
    Returns:
        Processed response with PDF link if APQP-related
    
    Example:
        >>> response = process_apqp_response(
        ...     "What is APQP?",
        ...     "APQP is Advanced Product Quality Planning..."
        ... )
        >>> "APQP Quick Access Guide" in response
        True
    """
    processor = APQPResponseProcessor(pdf_url=pdf_url)
    return processor.process(user_question, bot_response)


# ============================================================================
# UNIT TESTS
# ============================================================================

def run_tests():
    """Run unit tests for the APQP response processor."""
    
    print("=" * 70)
    print("APQP Response Processor - Unit Tests")
    print("=" * 70)
    
    test_pdf_url = "https://drive.google.com/file/d/1pQ67wAzsZ01KLqMRcJvJvtkpFN2Ka8x_/view?usp=sharing"
    processor = APQPResponseProcessor(pdf_url=test_pdf_url)
    
    # Test 1: Detection - Direct APQP mention (case-insensitive)
    print("\n✓ Test 1: Detection - Direct APQP mention")
    assert processor.is_apqp_related("What is APQP?")
    assert processor.is_apqp_related("Tell me about apqp")
    assert processor.is_apqp_related("APQP requirements")
    assert processor.is_apqp_related("Can you explain Apqp?")
    print("  ✅ All APQP keyword variations detected")
    
    # Test 2: Detection - Advanced Product Quality Planning phrase
    print("\n✓ Test 2: Detection - Advanced Product Quality phrase")
    assert processor.is_apqp_related("What is Advanced Product Quality Planning?")
    assert processor.is_apqp_related("advanced product quality planning process")
    assert processor.is_apqp_related("Tell me about Advanced Product Quality")
    print("  ✅ All phrase variations detected")
    
    # Test 3: Detection - Non-APQP content
    print("\n✓ Test 3: Detection - Non-APQP content")
    assert not processor.is_apqp_related("What is PPAP?")
    assert not processor.is_apqp_related("Tell me about quality control")
    assert not processor.is_apqp_related("How do I submit a change request?")
    print("  ✅ Non-APQP content correctly ignored")
    
    # Test 4: Word boundary check (avoid false positives)
    print("\n✓ Test 4: Word boundary check")
    assert not processor.is_apqp_related("The company name is XAPQPY")
    assert processor.is_apqp_related("The APQP process")
    print("  ✅ Word boundaries respected")
    
    # Test 5: URL already exists check
    print("\n✓ Test 5: URL already exists check")
    response_with_url = f"Here's the info. See: {test_pdf_url}"
    assert processor.has_pdf_url(response_with_url)
    assert not processor.has_pdf_url("Here's the info without URL")
    print("  ✅ Duplicate URL detection working")
    
    # Test 6: Process - Add PDF link
    print("\n✓ Test 6: Process - Add PDF link to APQP response")
    result = processor.process(
        "What is APQP?",
        "APQP is a framework for product development."
    )
    assert test_pdf_url in result
    assert "APQP Quick Access Guide" in result
    assert "APQP is a framework" in result
    print("  ✅ PDF link correctly appended")
    
    # Test 7: Process - Don't add to non-APQP
    print("\n✓ Test 7: Process - Ignore non-APQP content")
    result = processor.process(
        "What is PPAP?",
        "PPAP is Production Part Approval Process."
    )
    assert test_pdf_url not in result
    assert result == "PPAP is Production Part Approval Process."
    print("  ✅ Non-APQP responses unchanged")
    
    # Test 8: Process - Don't duplicate existing URL
    print("\n✓ Test 8: Process - Prevent URL duplication")
    response_with_url = f"APQP info here. See: {test_pdf_url}"
    result = processor.process(
        "What is APQP?",
        response_with_url
    )
    # Count occurrences - should be exactly 1
    url_count = result.count(test_pdf_url)
    assert url_count == 1, f"Expected 1 URL occurrence, found {url_count}"
    print("  ✅ URL not duplicated")
    
    # Test 9: Convenience function
    print("\n✓ Test 9: Convenience function")
    result = process_apqp_response(
        "Explain APQP phases",
        "APQP has 5 phases...",
        pdf_url=test_pdf_url
    )
    assert test_pdf_url in result
    print("  ✅ Convenience function working")
    
    # Test 10: APQP detected in response (not just question)
    print("\n✓ Test 10: APQP detection in response")
    result = processor.process(
        "What planning processes do you recommend?",
        "I recommend using APQP for product development."
    )
    assert test_pdf_url in result
    print("  ✅ APQP detected in bot response")
    
    # Test 11: Case sensitivity edge cases
    print("\n✓ Test 11: Case sensitivity edge cases")
    assert processor.is_apqp_related("aPqP")
    assert processor.is_apqp_related("Advanced PRODUCT Quality PLANNING")
    print("  ✅ Case-insensitive matching works")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def show_examples():
    """Show practical usage examples."""
    
    print("\n" + "=" * 70)
    print("USAGE EXAMPLES")
    print("=" * 70)
    
    processor = APQPResponseProcessor(
        pdf_url="https://drive.google.com/file/d/1pQ67wAzsZ01KLqMRcJvJvtkpFN2Ka8x_/view?usp=sharing"
    )
    
    # Example 1: Basic usage
    print("\n📌 Example 1: Basic APQP question")
    print("-" * 70)
    question = "What are the APQP phases?"
    response = "APQP consists of 5 phases: Planning, Design, Process, Validation, and Feedback."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    
    # Example 2: Advanced Product Quality Planning
    print("\n📌 Example 2: Full phrase detection")
    print("-" * 70)
    question = "Can you explain Advanced Product Quality Planning?"
    response = "It's a structured framework used in automotive industry."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    
    # Example 3: Non-APQP question
    print("\n📌 Example 3: Non-APQP question (no modification)")
    print("-" * 70)
    question = "What is PPAP?"
    response = "PPAP is the Production Part Approval Process."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    print("(No changes - not APQP-related)")
    
    # Example 4: Using convenience function
    print("\n📌 Example 4: Convenience function")
    print("-" * 70)
    processed = process_apqp_response(
        "Tell me about APQP",
        "APQP is essential for quality planning.",
        pdf_url="https://drive.google.com/file/d/1pQ67wAzsZ01KLqMRcJvJvtkpFN2Ka8x_/view?usp=sharing"
    )
    print(processed)


if __name__ == "__main__":
    # Run tests
    run_tests()
    
    # Show examples
    show_examples()
