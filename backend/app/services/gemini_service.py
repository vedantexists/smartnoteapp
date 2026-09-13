import os
import json
import time
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from app.models.schemas import (
    GeminiExtractionResult, Flashcard, WebResource, EntertainmentRec, 
    DomainCategory, WeeklyDigestResponse
)

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
You are an expert AI multimodal analyst specialized in short-form social video content (Instagram Reels, YouTube Shorts).
Your job is to inspect both visual keyframes (on-screen text, demonstrations, OCR, code) and spoken audio (transcripts, speech tone, sound).

You must perform:
1. CLICKBAIT & FACT-CHECK GATE:
   Evaluate factual accuracy, substance, and promotional depth.
   If the video is a deceptive scam, get-rich-quick scheme, pure drop-shipping advertisement, or completely empty clickbait with no genuine informational substance, set is_clickbait_or_scam=true with a clear clickbait_reason.

2. DOMAIN CLASSIFICATION:
   Classify the content into one of:
   - "TECH_EDUCATION" (programming, engineering, AI, tutorials, design tools)
   - "ENTERTAINMENT_REC" (movie recommendations, TV series, songs, games, books)
   - "EVENT" (hackathons, conferences, webinars, deadlines, release dates)
   - "OTHER" (productivity, life hacks, general science, news)

3. DEEP CONTENT EXTRACTION:
   - title: Clear, concise topic title.
   - core_summary: 2-3 sentence distillation of the main concept or takeaway.
   - detailed_notes: Clean Markdown format with bullet points, code snippets or step-by-step instructions if applicable.
   - flashcards: 2-3 active recall Q&A flashcards for educational/tech content with concise answers and key takeaways.
   - github_repos: Any GitHub repositories mentioned or visible on screen, strictly formatted as "owner/repo" (e.g. "facebook/react", "shadcn/ui"). Never include full URL, just owner/repo.
   - web_resources: List of tools, websites, or apps mentioned: [{"name": "...", "url": "...", "purpose": "..."}].
   - entertainment_recommendations: Any movies, series, or songs mentioned: [{"title": "...", "type": "Movie"|"Series"|"Song", "creator": "...", "reason": "..."}].
   - event_ics: If specific dates, deadlines, or hackathons are mentioned, output a standard VCALENDAR string in raw .ics format starting with BEGIN:VCALENDAR and ending with END:VCALENDAR. Otherwise null.

Respond ONLY with a valid JSON object matching the schema. Do not enclose in markdown code fences unless standard ```json.
"""

class GeminiService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model or "gemini-2.5-flash"
        self.embedding_model = settings.gemini_embedding_model or "gemini-embedding-001"
        self._client = None
        self._legacy_genai = None

    def _get_client(self):
        """Initializes client lazily using google-genai or google-generativeai."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Service running in dummy/test mode.")
            return None

        if self._client is None and self._legacy_genai is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google GenAI SDK client successfully.")
            except ImportError:
                try:
                    import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=self.api_key)
                    self._legacy_genai = genai_legacy
                    logger.info("Initialized legacy google.generativeai client successfully.")
                except ImportError:
                    logger.error("Neither google-genai nor google-generativeai is installed.")
        return self._client or self._legacy_genai

    def extract_from_video(self, video_path: Path) -> GeminiExtractionResult:
        """
        Uploads low-res .mp4 via Gemini File API, waits until ACTIVE, prompts for structured JSON,
        and deletes file from Google servers.
        """
        client = self._get_client()
        if not client:
            return self._mock_extraction(video_path)

        file_ref = None
        try:
            # 1. Upload via File API
            logger.info(f"Uploading {video_path} to Gemini File API...")
            if hasattr(client, "files"):
                # google-genai SDK
                file_ref = client.files.upload(file=str(video_path))
                # Wait until active
                while file_ref.state and file_ref.state.name == "PROCESSING":
                    logger.info("Video is processing on Gemini File API...")
                    time.sleep(3)
                    file_ref = client.files.get(name=file_ref.name)

                if file_ref.state and file_ref.state.name == "FAILED":
                    raise RuntimeError("Gemini file processing failed on Google servers.")

                logger.info(f"File active on Gemini: {file_ref.name}")

                prompt = (
                    f"{SYSTEM_INSTRUCTION}\n\n"
                    "Analyze this video carefully. Extract all notes, resources, repos, and flashcards. "
                    "Output pure JSON only."
                )

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=[file_ref, prompt]
                )
                raw_text = response.text
            else:
                # google.generativeai legacy SDK
                file_ref = self._legacy_genai.upload_file(str(video_path))
                while file_ref.state.name == "PROCESSING":
                    time.sleep(3)
                    file_ref = self._legacy_genai.get_file(file_ref.name)

                if file_ref.state.name == "FAILED":
                    raise RuntimeError("Gemini file processing failed on Google servers.")

                model = self._legacy_genai.GenerativeModel(self.model_name)
                prompt = (
                    f"{SYSTEM_INSTRUCTION}\n\n"
                    "Analyze this video carefully. Extract all notes, resources, repos, and flashcards. "
                    "Output pure JSON only."
                )
                response = model.generate_content([file_ref, prompt])
                raw_text = response.text

            return self._parse_json_result(raw_text)

        finally:
            # 2. Guarantee deletion of file from Google's servers
            if file_ref:
                try:
                    if hasattr(client, "files"):
                        client.files.delete(name=file_ref.name)
                    elif self._legacy_genai:
                        self._legacy_genai.delete_file(file_ref.name)
                    logger.info(f"Successfully deleted remote Gemini file: {file_ref.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete remote Gemini file {file_ref.name}: {e}")

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding vector for semantic deduplication and search."""
        client = self._get_client()
        if not client:
            # Deterministic mock 768-dim vector for testing
            import hashlib
            h = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16)
            import random
            rng = random.Random(h)
            return [rng.uniform(-1.0, 1.0) for _ in range(768)]

        try:
            if hasattr(client, "models") and hasattr(client.models, "embed_content"):
                resp = client.models.embed_content(
                    model=self.embedding_model,
                    contents=text
                )
                if hasattr(resp, "embedding") and resp.embedding:
                    return resp.embedding.values
                elif hasattr(resp, "embeddings") and resp.embeddings:
                    return resp.embeddings[0].values
            elif self._legacy_genai:
                resp = self._legacy_genai.embed_content(
                    model=f"models/{self.embedding_model}",
                    content=text,
                    task_type="retrieval_document"
                )
                return resp['embedding']
        except Exception as e:
            logger.error(f"Error computing Gemini embedding: {e}")

        # Fallback pseudo embedding
        import hashlib, random
        h = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16)
        rng = random.Random(h)
        return [rng.uniform(-1.0, 1.0) for _ in range(768)]

    def merge_notes(self, existing_json: Dict[str, Any], new_json: Dict[str, Any]) -> GeminiExtractionResult:
        """
        Calls Gemini to cleanly merge existing and new JSON on the same topic,
        strictly dropping duplicates and consolidating notes.
        """
        client = self._get_client()
        if not client:
            return self._mock_merge(existing_json, new_json)

        prompt = f"""
        You are an intelligent knowledge consolidation system.
        We have an EXISTING note and a NEW extracted note from another video on the same topic.
        
        EXISTING NOTE:
        {json.dumps(existing_json, indent=2)}

        NEW EXTRACTED NOTE:
        {json.dumps(new_json, indent=2)}

        TASK:
        Cleanly merge both notes into one cohesive, deduplicated note:
        - Update title to best capture the combined scope.
        - Combine core_summary and detailed_notes to eliminate redundancy while preserving new insights, tips, and examples.
        - Combine web_resources, strictly dropping duplicates (by name or URL).
        - Combine github_repos, strictly dropping duplicates (format strictly owner/repo).
        - Combine flashcards, keeping distinct active recall questions and dropping near-duplicates.
        - Combine entertainment_recommendations, dropping duplicates.
        - Merge event_ics if new dates or deadlines are found.
        - Set is_clickbait_or_scam to false unless both are scam.

        Respond ONLY with a valid JSON object matching the GeminiExtractionResult schema.
        """

        try:
            if hasattr(client, "models"):
                resp = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                raw_text = resp.text
            else:
                model = self._legacy_genai.GenerativeModel(self.model_name)
                resp = model.generate_content(prompt)
                raw_text = resp.text

            return self._parse_json_result(raw_text)
        except Exception as e:
            logger.error(f"Failed to merge notes with Gemini: {e}")
            return self._mock_merge(existing_json, new_json)

    def generate_weekly_digest(self, notes: List[Dict[str, Any]], start_date: str, end_date: str) -> WeeklyDigestResponse:
        """Synthesizes the last 7 days of entries into a high-level summary."""
        client = self._get_client()
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not notes:
            return WeeklyDigestResponse(
                start_date=start_date,
                end_date=end_date,
                total_notes_processed=0,
                digest_summary="No notes were saved during this period.",
                top_topics=[],
                notable_tools=[],
                highlight_flashcards=[],
                generated_at=now
            )

        if not client:
            return WeeklyDigestResponse(
                start_date=start_date,
                end_date=end_date,
                total_notes_processed=len(notes),
                digest_summary=f"Weekly digest aggregating {len(notes)} captured knowledge items across engineering and productivity.",
                top_topics=[n.get("title", "") for n in notes[:5]],
                notable_tools=[],
                highlight_flashcards=[],
                generated_at=now
            )

        prompt = f"""
        You are a chief knowledge synthesizer.
        Here are the notes collected over the past week ({start_date} to {end_date}):
        {json.dumps(notes, indent=2)}

        Generate an engaging, structured weekly digest:
        1. digest_summary: A 2-3 paragraph synthesis of key learnings, industry trends, and practical takeaways.
        2. top_topics: List of top 3-5 high-level themes.
        3. notable_tools: Up to 5 of the best web resources or libraries discovered.
        4. highlight_flashcards: 3 of the best active recall flashcards from the notes for weekly spaced repetition review.

        Respond with valid JSON matching:
        {{
            "digest_summary": str,
            "top_topics": [str],
            "notable_tools": [{{"name": str, "url": str, "purpose": str}}],
            "highlight_flashcards": [{{"question": str, "answer": str, "key_takeaway": str}}]
        }}
        """

        try:
            if hasattr(client, "models"):
                resp = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                raw_text = resp.text
            else:
                model = self._legacy_genai.GenerativeModel(self.model_name)
                resp = model.generate_content(prompt)
                raw_text = resp.text

            clean_text = self._clean_json_str(raw_text)
            data = json.loads(clean_text)

            tools = [WebResource(**t) for t in data.get("notable_tools", [])]
            cards = [Flashcard(**c) for c in data.get("highlight_flashcards", [])]

            return WeeklyDigestResponse(
                start_date=start_date,
                end_date=end_date,
                total_notes_processed=len(notes),
                digest_summary=data.get("digest_summary", ""),
                top_topics=data.get("top_topics", []),
                notable_tools=tools,
                highlight_flashcards=cards,
                generated_at=now
            )
        except Exception as e:
            logger.error(f"Error creating weekly digest with Gemini: {e}")
            return WeeklyDigestResponse(
                start_date=start_date,
                end_date=end_date,
                total_notes_processed=len(notes),
                digest_summary=f"Weekly digest of {len(notes)} items.",
                top_topics=[n.get("title", "") for n in notes[:5]],
                notable_tools=[],
                highlight_flashcards=[],
                generated_at=now
            )

    def _parse_json_result(self, raw_text: str) -> GeminiExtractionResult:
        clean = self._clean_json_str(raw_text)
        data = json.loads(clean)
        return GeminiExtractionResult(**data)

    def _clean_json_str(self, text: str) -> str:
        """Strips markdown code blocks and whitespace."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    def _mock_extraction(self, video_path: Path) -> GeminiExtractionResult:
        """Deterministic mock for test environments without an active API key."""
        filename = video_path.stem
        return GeminiExtractionResult(
            is_clickbait_or_scam=False,
            domain=DomainCategory.TECH_EDUCATION,
            title=f"Extracted Knowledge from {filename}",
            core_summary="Comprehensive architectural guide covering modern web development, state management, and API design.",
            detailed_notes="### Core Insights\n- Automated pipeline using multimodal AI.\n- Vector deduplication using ChromaDB.\n- Free tier containerization on Hugging Face Spaces.",
            flashcards=[
                Flashcard(
                    question="What is the primary benefit of WorkManager on ColorOS devices?",
                    answer="It guarantees deferred background task execution respecting device battery management constraints.",
                    key_takeaway="Survives OEM aggressive task killers."
                ),
                Flashcard(
                    question="What vector similarity metric is used for deduplication?",
                    answer="Cosine similarity with a 0.85 threshold.",
                    key_takeaway="Prevents duplicate notes on identical topics."
                )
            ],
            github_repos=["facebook/react", "tiangolo/fastapi"],
            web_resources=[
                WebResource(name="FastAPI Docs", url="https://fastapi.tiangolo.com", purpose="Modern web framework documentation"),
                WebResource(name="Hugging Face Spaces", url="https://huggingface.co/spaces", purpose="Free container deployment platform")
            ],
            entertainment_recommendations=[
                EntertainmentRec(title="The Social Network", type="Movie", creator="David Fincher", reason="Classic film on startup development")
            ],
            event_ics=None
        )

    def _mock_merge(self, existing: Dict[str, Any], new: Dict[str, Any]) -> GeminiExtractionResult:
        """Merges two note dictionaries cleanly without API key."""
        repos = list(dict.fromkeys(existing.get("github_repos", []) + new.get("github_repos", [])))

        # Merge web resources
        existing_res = {r.get("url"): r for r in existing.get("web_resources", [])}
        for r in new.get("web_resources", []):
            existing_res[r.get("url")] = r
        merged_res = [WebResource(**r) for r in existing_res.values()]

        # Merge flashcards
        existing_cards = {c.get("question").lower().strip(): c for c in existing.get("flashcards", [])}
        for c in new.get("flashcards", []):
            existing_cards[c.get("question").lower().strip()] = c
        merged_cards = [Flashcard(**c) for c in existing_cards.values()]

        # Merge entertainment recs
        existing_recs = {r.get("title").lower().strip(): r for r in existing.get("entertainment_recommendations", [])}
        for r in new.get("entertainment_recommendations", []):
            existing_recs[r.get("title").lower().strip()] = r
        merged_recs = [EntertainmentRec(**r) for r in existing_recs.values()]

        return GeminiExtractionResult(
            is_clickbait_or_scam=False,
            domain=DomainCategory(new.get("domain", "TECH_EDUCATION")),
            title=existing.get("title") or new.get("title", "Consolidated Note"),
            core_summary=f"{existing.get('summary', '')} Additionally: {new.get('core_summary', '')}".strip(),
            detailed_notes=f"{existing.get('detailed_notes', '')}\n\n### Additional Updates\n{new.get('detailed_notes', '')}".strip(),
            flashcards=merged_cards,
            github_repos=repos,
            web_resources=merged_res,
            entertainment_recommendations=merged_recs,
            event_ics=new.get("event_ics") or existing.get("event_ics")
        )

gemini_service = GeminiService()
