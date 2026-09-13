import logging
from typing import Tuple, Optional
from app.models.schemas import GeminiExtractionResult

logger = logging.getLogger(__name__)

def check_clickbait_and_scam(extraction: GeminiExtractionResult) -> Tuple[bool, Optional[str]]:
    """
    Evaluates extraction results against clickbait, deceptive scam, and empty drop-shipping gates.
    Returns (is_rejected, reason).
    """
    if extraction.is_clickbait_or_scam:
        reason = extraction.clickbait_reason or "Flagged as empty clickbait, deceptive scam, or predatory advertisement."
        logger.warning(f"Content failed fact-check gate: {reason}")
        return True, reason

    # Secondary heuristic check on notes substance
    if len(extraction.core_summary.strip()) < 10 and len(extraction.detailed_notes.strip()) < 10:
        return True, "Video has no actionable educational, technical, or entertainment substance."

    return False, None
