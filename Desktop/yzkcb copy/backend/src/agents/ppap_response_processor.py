"""
PPAP Response Post-Processor

This module ensures that every chatbot response related to PPAP (Production Part Approval Process)
includes reference links to the PPAP submission guidance documents.

Features:
- Case-insensitive keyword detection for PPAP-related content
- Fuzzy matching to catch variations (PPAP, production part approval, etc.)
- Prevents duplicate URL insertion
- Clean, testable middleware design
- Production-safe with no external dependencies
- Supports multiple PDF links
"""

import re
from typing import Optional, List, Tuple


# Default PPAP PDF URLs - can be overridden via configuration
DEFAULT_PPAP_PDF_URLS = [
    "https://drive.google.com/file/d/1E37XSeoCt7KLKKpxfasswV0KJHRo0y7A/view?usp=sharing",
    "https://drive.google.com/file/d/1AgvARD0ClNiu3-u0Juqm8NylYqEkqjyt/view?usp=sharing"
]


class PPAPResponseProcessor:
    """
    Post-processor for PPAP-related chatbot responses.
    
    Detects PPAP mentions and appends guidance PDF links when appropriate.
    """
    
    def __init__(self, pdf_urls: Optional[List[str]] = None):
        """
        Initialize the PPAP response processor.
        
        Args:
            pdf_urls: List of URLs to PPAP guidance PDFs. If None, uses DEFAULT_PPAP_PDF_URLS.
        """
        self.pdf_urls = pdf_urls or DEFAULT_PPAP_PDF_URLS.copy()
        
        # PDF labels for display
        self.pdf_labels = [
            "PPAP Submission Guide",
            "PPAP Documentation Guidelines"
        ]
        
        # Compile regex patterns for efficient matching
        # Pattern 1: Direct PPAP mentions (case-insensitive, word boundary)
        self.ppap_pattern = re.compile(r'\bPPAP\b', re.IGNORECASE)
        
        # Pattern 2: Production Part Approval Process (with optional words)
        self.ppap_phrase_pattern = re.compile(
            r'\bproduction\s+part\s+approval(?:\s+process)?\b',
            re.IGNORECASE
        )
        
        # Pattern 3: Part approval (more general)
        self.part_approval_pattern = re.compile(
            r'\bpart\s+approval\b',
            re.IGNORECASE
        )
        
        # Pattern 4: PPAP submission specific phrases
        self.ppap_submission_pattern = re.compile(
            r'\bppap\s+submission\b',
            re.IGNORECASE
        )
        
        # Pattern 5: Submission-related phrases specifically about submitting PPAP or parts
        self.submission_pattern = re.compile(
            r"\b(?:submit|submitting|submitted)\b(?:\s+(?:a|the|ppap|part))?(?:\s+(?:ppap|part|approval|submission))?\b",
            re.IGNORECASE,
        )
        
        # Patterns to check if URLs already exist in response
        self.url_exists_patterns = []
        for url in self.pdf_urls:
            escaped_url = re.escape(url)
            self.url_exists_patterns.append(re.compile(escaped_url, re.IGNORECASE))
    
    def is_ppap_related(self, text: Optional[str]) -> bool:
        """
        Detect if the text is related to PPAP.
        
        Args:
            text: The text to analyze (user question or bot response)
            
        Returns:
            True if PPAP-related, False otherwise
        """
        if not text:
            return False
        
        # Check for direct PPAP mentions
        if self.ppap_pattern.search(text):
            return True
        
        # Check for "Production Part Approval" phrases
        if self.ppap_phrase_pattern.search(text):
            return True
        
        # Check for "part approval" phrases
        if self.part_approval_pattern.search(text):
            return True
        
        # Check for PPAP submission specific mentions
        if self.ppap_submission_pattern.search(text):
            return True
        
        return False

    def is_submission_related(self, text: Optional[str]) -> bool:
        """
        Detect if the text mentions submitting/submission language related to PPAP or parts.
        """
        if not text:
            return False

        return bool(self.submission_pattern.search(text))
    
    def has_pdf_urls(self, text: Optional[str]) -> bool:
        """
        Check if the response already contains any of the PDF URLs.
        
        Args:
            text: The response text to check
            
        Returns:
            True if any URL already exists, False otherwise
        """
        if not text:
            return False
        
        for pattern in self.url_exists_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def append_pdf_references(self, response: str) -> str:
        """
        Append the PPAP PDF references to the response.
        
        Args:
            response: The original chatbot response
            
        Returns:
            Response with PDF references appended
        """
        # Short intro above the links
        top_phrase = (
            "**For guidance on PPAP submission processes through the supplier portal <a href=\"https://yazakieurope.empowerqlm.com/Dashboard\" target=\"_blank\">EmpowerQLM</a>, see the detailed guides below:**"
            "\n\n"
        )

        # Create friendly, unobtrusive reference lines with clickable links
        references = []
        for i, (label, url) in enumerate(zip(self.pdf_labels, self.pdf_urls)):
            if i < len(self.pdf_urls):  # Ensure we don't exceed available URLs
                references.append(f"📘 **<a href=\"{url}\" target=\"_blank\">{label}</a>**")
        
        reference_block = "\n".join(references)
        
        return response + "\n\n" + top_phrase + reference_block
    
    def process(self, user_question: Optional[str], bot_response: str) -> str:
        """
        Main processing method - analyzes question and response, adds PDF links if needed.
        
        Args:
            user_question: The user's input question
            bot_response: The chatbot's response
            
        Returns:
            Processed response (with or without PDF links)
        """
        # Check if question or response mentions PPAP, or if the bot response
        # mentions submitting/submission related to PPAP or parts
        is_related = (
            self.is_ppap_related(user_question)
            or self.is_ppap_related(bot_response)
            or self.is_submission_related(bot_response)
        )
        
        # If not PPAP-related, return original response
        if not is_related:
            return bot_response
        
        # If already contains any of the PDF URLs, don't add them again
        if self.has_pdf_urls(bot_response):
            return bot_response
        
        # Append the PDF references
        return self.append_pdf_references(bot_response)


# Convenience function for simple usage
def process_ppap_response(user_question: Optional[str], bot_response: str, pdf_urls: Optional[List[str]] = None) -> str:
    """
    Convenience function to process a single response.
    
    Args:
        user_question: The user's input question
        bot_response: The chatbot's response
        pdf_urls: Optional list of custom PDF URLs (uses default if not provided)
        
    Returns:
        Processed response with PDF links if PPAP-related
    
    Example:
        >>> response = process_ppap_response(
        ...     "What is PPAP?",
        ...     "PPAP is Production Part Approval Process..."
        ... )
        >>> "PPAP Submission Guide" in response
        True
    """
    processor = PPAPResponseProcessor(pdf_urls=pdf_urls)
    return processor.process(user_question, bot_response)


# ============================================================================
# UNIT TESTS
# ============================================================================

def run_tests():
    """Run unit tests for the PPAP response processor."""
    
    print("=" * 70)
    print("PPAP Response Processor - Unit Tests")
    print("=" * 70)
    
    test_pdf_urls = DEFAULT_PPAP_PDF_URLS.copy()
    processor = PPAPResponseProcessor(pdf_urls=test_pdf_urls)
    
    # Test 1: Detection - Direct PPAP mention (case-insensitive)
    print("\n✓ Test 1: Detection - Direct PPAP mention")
    assert processor.is_ppap_related("What is PPAP?")
    assert processor.is_ppap_related("Tell me about ppap")
    assert processor.is_ppap_related("PPAP requirements")
    assert processor.is_ppap_related("Can you explain Ppap?")
    print("  ✅ All PPAP keyword variations detected")
    
    # Test 2: Detection - Production Part Approval Process phrase
    print("\n✓ Test 2: Detection - Production Part Approval phrase")
    assert processor.is_ppap_related("What is Production Part Approval Process?")
    assert processor.is_ppap_related("production part approval process requirements")
    assert processor.is_ppap_related("Tell me about Production Part Approval")
    print("  ✅ All phrase variations detected")
    
    # Test 3: Detection - Part approval (more general)
    print("\n✓ Test 3: Detection - Part approval phrases")
    assert processor.is_ppap_related("How do I get part approval?")
    assert processor.is_ppap_related("Part approval process")
    print("  ✅ Part approval phrases detected")
    
    # Test 4: Detection - PPAP submission specific
    print("\n✓ Test 4: Detection - PPAP submission specific")
    assert processor.is_ppap_related("PPAP submission requirements")
    assert processor.is_ppap_related("How to do ppap submission?")
    print("  ✅ PPAP submission phrases detected")
    
    # Test 5: Detection - Non-PPAP content
    print("\n✓ Test 5: Detection - Non-PPAP content")
    assert not processor.is_ppap_related("What is APQP?")
    assert not processor.is_ppap_related("Tell me about quality control")
    assert not processor.is_ppap_related("How do I change my password?")
    print("  ✅ Non-PPAP content correctly ignored")
    
    # Test 6: Word boundary check (avoid false positives)
    print("\n✓ Test 6: Word boundary check")
    assert not processor.is_ppap_related("The company name is XPPAPX")
    assert processor.is_ppap_related("The PPAP process")
    print("  ✅ Word boundaries respected")
    
    # Test 7: Submission detection
    print("\n✓ Test 7: Submission detection")
    assert processor.is_submission_related("I want to submit a part for approval")
    assert processor.is_submission_related("Submitting PPAP documentation")
    assert processor.is_submission_related("How to submit part approval?")
    print("  ✅ Submission phrases detected")
    
    # Test 8: URLs already exist check
    print("\n✓ Test 8: URLs already exist check")
    response_with_url = f"Here's the info. See: {test_pdf_urls[0]}"
    assert processor.has_pdf_urls(response_with_url)
    assert not processor.has_pdf_urls("Here's the info without URL")
    print("  ✅ Duplicate URL detection working")
    
    # Test 9: Process - Add PDF links
    print("\n✓ Test 9: Process - Add PDF links to PPAP response")
    result = processor.process(
        "What is PPAP?",
        "PPAP is a framework for part approval."
    )
    assert test_pdf_urls[0] in result
    assert test_pdf_urls[1] in result
    assert "PPAP Submission Guide" in result
    assert "PPAP Documentation Guidelines" in result
    assert "PPAP is a framework" in result
    print("  ✅ PDF links correctly appended")
    
    # Test 10: Process - Don't add to non-PPAP
    print("\n✓ Test 10: Process - Ignore non-PPAP content")
    result = processor.process(
        "What is APQP?",
        "APQP is Advanced Product Quality Planning."
    )
    assert test_pdf_urls[0] not in result
    assert test_pdf_urls[1] not in result
    assert result == "APQP is Advanced Product Quality Planning."
    print("  ✅ Non-PPAP responses unchanged")
    
    # Test 11: Process - Don't duplicate existing URL
    print("\n✓ Test 11: Process - Prevent URL duplication")
    response_with_url = f"PPAP info here. See: {test_pdf_urls[0]}"
    result = processor.process(
        "What is PPAP?",
        response_with_url
    )
    # Count occurrences - should be exactly 1 for first URL
    url_count = result.count(test_pdf_urls[0])
    assert url_count == 1, f"Expected 1 URL occurrence, found {url_count}"
    print("  ✅ URL not duplicated")
    
    # Test 12: Convenience function
    print("\n✓ Test 12: Convenience function")
    result = process_ppap_response(
        "Explain PPAP process",
        "PPAP has several steps...",
        pdf_urls=test_pdf_urls
    )
    assert test_pdf_urls[0] in result
    assert test_pdf_urls[1] in result
    print("  ✅ Convenience function working")
    
    # Test 13: PPAP detected in response (not just question)
    print("\n✓ Test 13: PPAP detection in response")
    result = processor.process(
        "What approval processes do you recommend?",
        "I recommend using PPAP for part approval."
    )
    assert test_pdf_urls[0] in result
    print("  ✅ PPAP detected in bot response")
    
    # Test 14: Case sensitivity edge cases
    print("\n✓ Test 14: Case sensitivity edge cases")
    assert processor.is_ppap_related("pPaP")
    assert processor.is_ppap_related("Production PART Approval PROCESS")
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
    
    processor = PPAPResponseProcessor(pdf_urls=DEFAULT_PPAP_PDF_URLS)
    
    # Example 1: Basic usage
    print("\n📌 Example 1: Basic PPAP question")
    print("-" * 70)
    question = "What is PPAP?"
    response = "PPAP is the Production Part Approval Process used in automotive manufacturing."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    
    # Example 2: Production Part Approval Process
    print("\n📌 Example 2: Full phrase detection")
    print("-" * 70)
    question = "Can you explain Production Part Approval Process?"
    response = "It's a quality assurance framework used in manufacturing."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    
    # Example 3: Non-PPAP question
    print("\n📌 Example 3: Non-PPAP question (no modification)")
    print("-" * 70)
    question = "What is APQP?"
    response = "APQP is Advanced Product Quality Planning."
    
    processed = processor.process(question, response)
    print(f"Question: {question}")
    print(f"Original Response:\n{response}")
    print(f"\nProcessed Response:\n{processed}")
    print("(No changes - not PPAP-related)")
    
    # Example 4: Using convenience function
    print("\n📌 Example 4: Convenience function")
    print("-" * 70)
    processed = process_ppap_response(
        "Tell me about PPAP submission",
        "PPAP submission requires proper documentation.",
        pdf_urls=DEFAULT_PPAP_PDF_URLS
    )
    print(processed)


if __name__ == "__main__":
    # Run tests
    run_tests()
    
    # Show examples
    show_examples()