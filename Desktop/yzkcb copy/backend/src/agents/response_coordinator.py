"""
Response coordinator for post-processing links from multiple processors.

If more than one processor indicates that a guidance PDF should be appended,
this coordinator will append a combined block with a neutral phrase (e.g.
"Here are the documents") and include both links, avoiding duplicates.
"""

from typing import Optional, List


def _unique_urls(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def process_with_coordinator(user_question: Optional[str], bot_response: str, apqp_processor=None, sicr_processor=None, ppap_processor=None) -> str:
    """Coordinate APQP, SICR, and PPAP processors and handle multi-document cases.

    Rules:
    - If multiple processors are present and would append their PDFs, append a combined
      block with a neutral phrase and links to all relevant documents.
    - If only one processor wants to append, use that processor's .process() method
      (preserves its wording and behavior).
    - Prevent duplicate URLs.
    """
    # Quick exits
    if not apqp_processor and not sicr_processor and not ppap_processor:
        return bot_response

    # Determine whether each processor would want to append a link
    apqp_wants = False
    sicr_wants = False
    ppap_wants = False

    try:
        if apqp_processor:
            apqp_wants = (
                apqp_processor.is_apqp_related(user_question)
                or apqp_processor.is_apqp_related(bot_response)
                or apqp_processor.is_submission_related(bot_response)
            ) and not apqp_processor.has_pdf_url(bot_response)
    except Exception:
        apqp_wants = False

    try:
        if sicr_processor:
            sicr_wants = (
                sicr_processor.is_sicr_or_change_related(user_question)
                or sicr_processor.is_sicr_or_change_related(bot_response)
            ) and not sicr_processor.has_pdf_url(bot_response)
    except Exception:
        sicr_wants = False

    try:
        if ppap_processor:
            ppap_wants = (
                ppap_processor.is_ppap_related(user_question)
                or ppap_processor.is_ppap_related(bot_response)
                or ppap_processor.is_submission_related(bot_response)
            ) and not ppap_processor.has_pdf_urls(bot_response)
    except Exception:
        ppap_wants = False

    # Count how many processors want to append
    active_count = sum([apqp_wants, sicr_wants, ppap_wants])
    
    # If multiple want to append, build combined block (use labels from processors)
    if active_count > 1:
        pairs = []  # list of (label, url)
        try:
            if apqp_wants and apqp_processor:
                # Get the proper label - APQP processor doesn't have pdf_label, so use default
                apqp_label = "APQP Quick Access Guide"
                apqp_url = getattr(apqp_processor, 'pdf_url', None)
                pairs.append((apqp_label, apqp_url))
        except Exception:
            pass
        try:
            if sicr_wants and sicr_processor:
                # Get the proper label from SICR processor
                sicr_label = getattr(sicr_processor, 'pdf_label', 'SICR & Change Management Guide')
                sicr_url = getattr(sicr_processor, 'pdf_url', None)
                pairs.append((sicr_label, sicr_url))
        except Exception:
            pass
        try:
            if ppap_wants and ppap_processor:
                # Get the proper labels from PPAP processor (multiple PDFs)
                ppap_labels = getattr(ppap_processor, 'pdf_labels', ['PPAP Submission Guide', 'PPAP Documentation Guidelines'])
                ppap_urls = getattr(ppap_processor, 'pdf_urls', [])
                for i, (label, url) in enumerate(zip(ppap_labels, ppap_urls)):
                    if i < len(ppap_urls):  # Ensure we don't exceed available URLs
                        pairs.append((label, url))
        except Exception:
            pass

        # Remove any entries without urls and dedupe by url preserving first label
        seen = set()
        unique_pairs = []
        for label, url in pairs:
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            unique_pairs.append((label, url))

        if not unique_pairs:
            return bot_response

        # Neutral combined phrase - updated to cover all possible combinations
        top_phrase = "**For guidance on the processes mentioned above through the supplier portal <a href=\"https://yazakieurope.empowerqlm.com/Dashboard\" target=\"_blank\">EmpowerQLM</a>, please refer to the comprehensive guides below:**\n\n"
        links_block = "\n".join([f"  • **<a href=\"{url}\" target=\"_blank\">{label}</a>**" for label, url in unique_pairs])

        return bot_response + "\n\n" + top_phrase + links_block

    # If only APQP wants
    if apqp_wants and apqp_processor:
        try:
            return apqp_processor.process(user_question, bot_response)
        except Exception:
            return bot_response

    # If only SICR wants
    if sicr_wants and sicr_processor:
        try:
            return sicr_processor.process(user_question, bot_response)
        except Exception:
            return bot_response

    # If only PPAP wants
    if ppap_wants and ppap_processor:
        try:
            return ppap_processor.process(user_question, bot_response)
        except Exception:
            return bot_response

    # Nothing to do
    return bot_response
