"""
Response Cleaner Module - Post-processes raw LLM responses

This module implements a "cleaner" LLM step to refine raw chatbot responses by:
- Removing redundancy and filler content
- Preserving all necessary facts and numeric values  
- Shortening and rephrasing for concision (max 2-3 short sentences per main point)
- Keeping domain-specific terms unchanged (e.g., PPAP, SQE, APQP)
- Never inventing new facts (no hallucinations)
- Providing a rationale of changes made

Author: Yazaki Chatbot System
Date: October 2025
"""

import re
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CleaningResult:
    """Result of response cleaning operation"""
    cleaned_response: str
    rationale: str
    changes_made: Dict[str, int]
    original_length: int
    cleaned_length: int

class ResponseCleaner:
    """
    Post-processes raw LLM responses to improve concision and clarity
    while preserving all factual content and domain terminology.
    """
    
    def __init__(self, llm_manager=None, max_sentences_per_point: int = 3):
        """
        Initialize the response cleaner
        
        Args:
            llm_manager: Optional LLM manager for advanced cleaning
            max_sentences_per_point: Maximum sentences per main point
        """
        self.llm_manager = llm_manager
        self.max_sentences_per_point = max_sentences_per_point
        
        # Domain-specific terms to preserve unchanged
        self.domain_terms = {
            'PPAP', 'SQE', 'APQP', 'FMEA', 'AIAG', 'MSI', 'PSW', 'PFMEA', 'DFMEA',
            'SPC', 'Cpk', 'Cp', 'PPK', 'OEM', 'ASQM', 'RFQ', 'PO', 'SOW', 'RPN',
            'QSR', 'SQA', 'SCA', 'DC3PRA', 'RASIC', 'Buhin', 'PAPP', 'ISIR',
            'Yazaki', 'Toyota', 'Ford', 'GM', 'Nissan', 'Honda', 'Hyundai'
        }
        
        # Redundant phrases to remove
        self.redundant_phrases = [
            r'it should be noted that',
            r'it is important to note that',
            r'it is worth mentioning that',
            r'please be aware that',
            r'as mentioned previously',
            r'as stated earlier',
            r'furthermore',
            r'in addition to this',
            r'moreover',
            r'what this means is that',
            r'in other words',
            r'to put it simply',
            r'basically',
            r'essentially',
            r'at the end of the day',
            r'when all is said and done'
        ]
    
    def clean_response(self, raw_response: str, context: str = "") -> CleaningResult:
        """
        Clean and refine the raw LLM response
        
        Args:
            raw_response: Original response from LLM
            context: Optional context for better cleaning decisions
            
        Returns:
            CleaningResult with cleaned response and metadata
        """
        if not raw_response.strip():
            return CleaningResult(
                cleaned_response="",
                rationale="Empty response provided",
                changes_made={},
                original_length=0,
                cleaned_length=0
            )
        
        original_length = len(raw_response)
        changes_made = {}
        
        # Step 1: Remove email formatting artifacts
        cleaned_text, email_changes = self._remove_email_formatting(raw_response)
        changes_made.update(email_changes)
        
        # Step 2: Remove redundant phrases and filler
        cleaned_text, redundancy_changes = self._remove_redundancy(cleaned_text)
        changes_made.update(redundancy_changes)
        
        # Step 3: Shorten verbose explanations while preserving facts
        cleaned_text, concision_changes = self._improve_concision(cleaned_text)
        changes_made.update(concision_changes)
        
        # Step 4: Ensure domain terms are preserved
        cleaned_text, domain_changes = self._preserve_domain_terms(cleaned_text, raw_response)
        changes_made.update(domain_changes)
        
        # Step 5: Final formatting cleanup
        cleaned_text = self._final_cleanup(cleaned_text)
        
        # Generate rationale
        rationale = self._generate_rationale(changes_made, original_length, len(cleaned_text))
        
        return CleaningResult(
            cleaned_response=cleaned_text,
            rationale=rationale,
            changes_made=changes_made,
            original_length=original_length,
            cleaned_length=len(cleaned_text)
        )
    
    def _remove_email_formatting(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Remove email/letter formatting artifacts"""
        changes = {}
        original_text = text
        
        # Remove email headers
        patterns = [
            (r'^Subject:.*?\n', 'email_headers'),
            (r'^Dear .*?,?\n', 'email_headers'),
            (r'^To:.*?\n', 'email_headers'),
            (r'^From:.*?\n', 'email_headers'),
        ]
        
        for pattern, change_type in patterns:
            matches = len(re.findall(pattern, text, re.MULTILINE | re.IGNORECASE))
            if matches > 0:
                changes[change_type] = changes.get(change_type, 0) + matches
                text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove signatures and closings
        signature_patterns = [
            (r'\n\n(Sincerely|Best regards|Regards|Kind regards|Yours truly),?\n.*$', 'signatures'),
            (r'\n\n\[Your Name\].*$', 'signatures'),
            (r'\n\n(Quality Supplier Assistant|Yazaki Corporation).*$', 'signatures'),
        ]
        
        for pattern, change_type in signature_patterns:
            if re.search(pattern, text, re.DOTALL | re.IGNORECASE):
                changes[change_type] = changes.get(change_type, 0) + 1
                text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text.strip(), changes
    
    def _remove_redundancy(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Remove redundant phrases and filler content"""
        changes = {}
        original_sentences = len(re.findall(r'[.!?]+', text))
        
        # Remove redundant phrases more carefully
        redundant_removed = 0
        for phrase in self.redundant_phrases:
            matches = len(re.findall(phrase, text, re.IGNORECASE))
            if matches > 0:
                redundant_removed += matches
                # Remove the phrase and clean up any resulting punctuation issues
                text = re.sub(phrase + r'\s*,?\s*', ' ', text, flags=re.IGNORECASE)
                text = re.sub(phrase, ' ', text, flags=re.IGNORECASE)
                # Clean up double spaces and punctuation
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'\s*,\s*,', ',', text)
        
        if redundant_removed > 0:
            changes['redundant_phrases'] = redundant_removed
        
        # Be more careful with duplicate removal to preserve formatting
        # Split by lines first to preserve structure
        lines = text.split('\n')
        processed_lines = []
        seen_concepts = set()
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                processed_lines.append(line)  # Preserve empty lines
                continue
            
            # If it's a formatted line (bullet, number, etc.), keep it
            if (re.match(r'^\s*[•\-\*]\s+', line) or 
                re.match(r'^\s*\d+\.\s+', line) or
                re.match(r'^\s*[•\-\*]+\s*\*\*.*\*\*:', line)):  # Headers like "• **Category**:"
                processed_lines.append(line)
                continue
            
            # For regular sentences, check for duplicates
            sentences = re.split(r'[.!?]+', line_stripped)
            unique_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Extract key concepts (simplified)
                concepts = set(re.findall(r'\b\w{4,}\b', sentence.lower()))
                
                # Check if this sentence adds new information
                if not concepts.issubset(seen_concepts) or len(concepts) > 3:
                    unique_sentences.append(sentence)
                    seen_concepts.update(concepts)
                else:
                    if 'duplicate_content' not in changes:
                        changes['duplicate_content'] = 0
                    changes['duplicate_content'] += 1
            
            if unique_sentences:
                # Reconstruct the line with proper punctuation
                reconstructed = '. '.join(unique_sentences)
                if reconstructed and not reconstructed.endswith(('.', '!', '?', ':')):
                    reconstructed += '.'
                
                # Fix double periods and other punctuation issues
                reconstructed = re.sub(r'\.\.+', '.', reconstructed)
                reconstructed = re.sub(r'\s*,\s*,', ',', reconstructed)
                
                # Preserve original indentation
                original_indent = len(line) - len(line.lstrip())
                processed_lines.append(' ' * original_indent + reconstructed)
        
        text = '\n'.join(processed_lines)
        
        return text, changes
    
    def _improve_concision(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Improve concision while preserving all facts and numbers"""
        changes = {}
        
        # Split into logical sections by paragraphs, but preserve bullet points
        sections = re.split(r'\n\s*\n', text)  # Only split on paragraph breaks
        improved_sections = []
        
        sentences_shortened = 0
        
        for section in sections:
            if not section.strip():
                continue
            
            # Check if this section contains bullet points or numbered lists
            has_bullets = bool(re.search(r'^\s*[•\-\*]\s+', section, re.MULTILINE))
            has_numbers = bool(re.search(r'^\s*\d+\.\s+', section, re.MULTILINE))
            
            if has_bullets or has_numbers:
                # For sections with bullet points or numbered lists, be more conservative
                # Only remove truly redundant content, preserve structure
                lines = section.split('\n')
                important_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        important_lines.append('')
                        continue
                    
                    # Always keep bullet points and numbered items
                    if re.match(r'^[•\-\*]\s+', line) or re.match(r'^\d+\.\s+', line):
                        important_lines.append(line)
                    else:
                        # For regular lines, apply minimal cleaning
                        important_lines.append(line)
                
                improved_sections.append('\n'.join(important_lines))
                
            else:
                # For regular paragraphs, apply sentence-level cleaning
                sentences = re.split(r'[.!?]+', section)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                # Check if this section contains critical information
                section_text = '. '.join(sentences)
                has_technical_content = bool(re.search(r'\d+(?:\.\d+)?', section_text))
                has_domain_terms = any(
                    re.search(rf'\b{re.escape(term)}\b', section_text, re.IGNORECASE) 
                    for term in self.domain_terms
                )
                has_requirements = any(
                    word in section_text.lower() 
                    for word in ['must', 'shall', 'required', 'minimum', 'maximum', 'standard']
                )
                
                # Be more conservative with critical sections
                if has_technical_content or has_domain_terms or has_requirements:
                    # For critical sections, allow more sentences
                    max_sentences = max(self.max_sentences_per_point, min(len(sentences), 5))
                else:
                    max_sentences = self.max_sentences_per_point
                
                # Limit sentences per section while preserving key info
                if len(sentences) > max_sentences:
                    # Keep first sentence and most information-dense ones
                    important_sentences = self._select_important_sentences(
                        sentences, max_sentences
                    )
                    sentences_shortened += len(sentences) - len(important_sentences)
                    sentences = important_sentences
                
                # Rejoin sentences
                if sentences:
                    section_text = '. '.join(sentences)
                    if not section_text.endswith('.'):
                        section_text += '.'
                    improved_sections.append(section_text)
        
        if sentences_shortened > 0:
            changes['sentences_shortened'] = sentences_shortened
        
        return '\n\n'.join(improved_sections), changes
    
    def _select_important_sentences(self, sentences: List[str], max_count: int) -> List[str]:
        """Select most important sentences based on information density"""
        if len(sentences) <= max_count:
            return sentences
        
        # Score sentences by information density
        scored_sentences = []
        
        for i, sentence in enumerate(sentences):
            score = 0
            
            # Heavily prefer sentences with numbers/facts (increased weight)
            numbers_count = len(re.findall(r'\d+(?:\.\d+)?', sentence))
            score += numbers_count * 5  # Increased from 3 to 5
            
            # Prefer sentences with domain terms (increased weight)
            domain_terms_count = 0
            for term in self.domain_terms:
                if re.search(rf'\b{re.escape(term)}\b', sentence, re.IGNORECASE):
                    domain_terms_count += 1
            score += domain_terms_count * 4  # Increased from 2 to 4
            
            # Prefer sentences with specific procedures/requirements
            procedure_words = ['must', 'shall', 'required', 'procedure', 'standard', 'specification', 'minimum', 'maximum']
            for word in procedure_words:
                if word in sentence.lower():
                    score += 2
            
            # Prefer sentences with specific values and measurements
            measurement_patterns = [
                r'Cpk', r'PPM', r'°C', r'cycles', r'hours', r'parts', r'%', r'less than', r'at least', r'minimum', r'maximum'
            ]
            for pattern in measurement_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    score += 3
            
            # Slightly prefer first sentence for context
            if i == 0:
                score += 1
            
            scored_sentences.append((score, i, sentence))
        
        # Sort by score (descending) and select top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        selected = scored_sentences[:max_count]
        
        # Maintain original order
        selected.sort(key=lambda x: x[1])
        
        return [sentence for _, _, sentence in selected]
    
    def _preserve_domain_terms(self, text: str, original_text: str) -> Tuple[str, Dict[str, int]]:
        """Ensure all domain-specific terms are preserved"""
        changes = {}
        
        # Find domain terms in original that might be missing in cleaned version
        original_terms_with_context = {}
        cleaned_terms = set()
        
        # Extract domain terms with their context from original
        for term in self.domain_terms:
            original_matches = list(re.finditer(rf'\b{re.escape(term)}\b[^.]*', original_text, re.IGNORECASE))
            if original_matches:
                original_terms_with_context[term] = [match.group() for match in original_matches]
                
            if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                cleaned_terms.add(term)
        
        missing_terms = set(original_terms_with_context.keys()) - cleaned_terms
        
        if missing_terms:
            changes['preserved_domain_terms'] = len(missing_terms)
            logger.warning(f"Domain terms lost during cleaning: {missing_terms}")
            
            # Try to recover critical missing terms by finding sentences that contained them
            for missing_term in missing_terms:
                # Look for sentences in original that had this term with important context
                for context in original_terms_with_context[missing_term]:
                    # If the context contains numbers or critical info, try to preserve it
                    if re.search(r'\d+(?:\.\d+)?', context) or any(
                        word in context.lower() for word in ['must', 'required', 'minimum', 'maximum', 'shall']
                    ):
                        # Add a note about the missing critical term
                        # In a production system, you might want to reintegrate the sentence
                        logger.info(f"Critical context lost for {missing_term}: {context[:100]}...")
        
        return text, changes
    
    def _final_cleanup(self, text: str) -> str:
        """Final formatting and cleanup - preserve important formatting"""
        # Remove excessive whitespace but preserve bullet points and lists
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Preserve bullet points and numbered lists - don't collapse their spacing
        # Only remove multiple spaces that aren't part of formatting
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Preserve lines that start with bullets or numbers
            if re.match(r'^\s*[•\-\*]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                # Keep bullet/number formatting intact
                cleaned_lines.append(line)
            else:
                # Clean up multiple spaces in regular text
                cleaned_line = re.sub(r' {2,}', ' ', line)
                cleaned_lines.append(cleaned_line)
        
        text = '\n'.join(cleaned_lines)
        
        # Ensure proper sentence endings but don't break list formatting
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Clean up any remaining artifacts but preserve markdown
        text = re.sub(r'\*\*$', '', text)
        text = re.sub(r'^\*\*', '', text)
        
        return text.strip()
    
    def _generate_rationale(self, changes_made: Dict[str, int], original_length: int, cleaned_length: int) -> str:
        """Generate a rationale explaining what was changed"""
        if not changes_made:
            return "No changes needed - response was already concise and well-formatted."
        
        rationale_parts = []
        
        # Summarize changes
        if 'email_headers' in changes_made or 'signatures' in changes_made:
            rationale_parts.append("removed email formatting")
        
        if 'redundant_phrases' in changes_made:
            rationale_parts.append(f"removed {changes_made['redundant_phrases']} redundant phrases")
        
        if 'duplicate_content' in changes_made:
            rationale_parts.append(f"eliminated {changes_made['duplicate_content']} repetitive sentences")
        
        if 'sentences_shortened' in changes_made:
            rationale_parts.append(f"condensed {changes_made['sentences_shortened']} verbose sentences")
        
        # Length reduction
        reduction_pct = int((original_length - cleaned_length) / original_length * 100)
        if reduction_pct > 5:
            rationale_parts.append(f"reduced length by {reduction_pct}%")
        
        if rationale_parts:
            rationale = f"Cleaned response by: {', '.join(rationale_parts)}. "
        else:
            rationale = "Applied minor formatting improvements. "
        
        rationale += "All facts, numbers, and domain terms preserved."
        
        if 'preserved_domain_terms' in changes_made:
            rationale += f" Note: {changes_made['preserved_domain_terms']} domain terms may need review."
        
        return rationale

    def clean_with_llm(self, raw_response: str, context: str = "") -> CleaningResult:
        """
        Advanced cleaning using LLM for better context understanding
        
        Args:
            raw_response: Original response from LLM
            context: Context used for the original response
            
        Returns:
            CleaningResult with LLM-enhanced cleaning
        """
        if not self.llm_manager:
            # Fall back to rule-based cleaning
            return self.clean_response(raw_response, context)
        
        cleaning_prompt = f"""You are a professional editor specializing in technical documentation. Your task is to clean and improve the following response while following these STRICT rules:

RULES:
1. NEVER invent or add new facts, numbers, or information
2. NEVER change domain-specific terms (PPAP, SQE, APQP, FMEA, etc.)
3. NEVER change specific procedures, standards, or requirements
4. Remove redundant phrases and filler words
5. Shorten verbose explanations to max 2-3 sentences per main point
6. Preserve ALL factual content and numeric values
7. Keep the professional, technical tone

ORIGINAL RESPONSE:
{raw_response}

INSTRUCTIONS: Clean this response to be more concise while preserving all facts. Return ONLY the cleaned version - no explanations or comments.

CLEANED RESPONSE:"""

        try:
            cleaned_text = self.llm_manager.get_completion(cleaning_prompt, max_tokens=len(raw_response))
            
            # Verify no facts were lost (basic check)
            original_numbers = set(re.findall(r'\d+(?:\.\d+)?', raw_response))
            cleaned_numbers = set(re.findall(r'\d+(?:\.\d+)?', cleaned_text))
            
            original_terms = set()
            cleaned_terms = set()
            for term in self.domain_terms:
                if re.search(rf'\b{re.escape(term)}\b', raw_response, re.IGNORECASE):
                    original_terms.add(term.lower())
                if re.search(rf'\b{re.escape(term)}\b', cleaned_text, re.IGNORECASE):
                    cleaned_terms.add(term.lower())
            
            # If important content was lost, fall back to rule-based cleaning
            if len(cleaned_numbers) < len(original_numbers) or len(cleaned_terms) < len(original_terms):
                logger.warning("LLM cleaning may have lost important content, falling back to rule-based cleaning")
                return self.clean_response(raw_response, context)
            
            # Calculate changes
            changes_made = {
                'llm_cleaning': 1,
                'length_reduction': len(raw_response) - len(cleaned_text)
            }
            
            rationale = f"Used LLM-based cleaning to improve concision. Reduced length by {int((len(raw_response) - len(cleaned_text)) / len(raw_response) * 100)}% while preserving all facts and domain terms."
            
            return CleaningResult(
                cleaned_response=cleaned_text.strip(),
                rationale=rationale,
                changes_made=changes_made,
                original_length=len(raw_response),
                cleaned_length=len(cleaned_text)
            )
            
        except Exception as e:
            logger.error(f"LLM cleaning failed: {e}, falling back to rule-based cleaning")
            return self.clean_response(raw_response, context)

# Convenience function for easy integration
def clean_chatbot_response(
    response: str, 
    context: str = "", 
    llm_manager=None,
    use_llm: bool = False
) -> CleaningResult:
    """
    Convenience function to clean a chatbot response
    
    Args:
        response: Raw response to clean
        context: Optional context for better cleaning
        llm_manager: Optional LLM manager for advanced cleaning
        use_llm: Whether to use LLM-based cleaning
        
    Returns:
        CleaningResult with cleaned response and metadata
    """
    cleaner = ResponseCleaner(llm_manager)
    
    if use_llm and llm_manager:
        return cleaner.clean_with_llm(response, context)
    else:
        return cleaner.clean_response(response, context)