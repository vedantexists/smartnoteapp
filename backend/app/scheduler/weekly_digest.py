import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.database import get_notes_in_range, save_weekly_digest, get_latest_weekly_digest
from app.services.gemini_service import gemini_service
from app.models.schemas import WeeklyDigestResponse

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def run_weekly_digest_job() -> WeeklyDigestResponse:
    """
    Aggregates notes from the last 7 days and synthesizes a high-level summary.
    Runs every Sunday at 00:00 UTC.
    """
    logger.info("Executing scheduled weekly digest job...")
    now = datetime.datetime.now(datetime.timezone.utc)
    seven_days_ago = now - datetime.timedelta(days=7)

    start_iso = seven_days_ago.isoformat()
    end_iso = now.isoformat()

    notes = get_notes_in_range(start_iso, end_iso)
    logger.info(f"Found {len(notes)} notes in the past 7 days for weekly digest.")

    notes_data = [
        {
            "id": n.id,
            "title": n.title,
            "domain": n.domain.value,
            "summary": n.summary,
            "detailed_notes": n.detailed_notes,
            "github_repos": n.github_repos,
            "web_resources": [r.model_dump() for r in n.web_resources],
            "entertainment_recommendations": [r.model_dump() for r in n.entertainment_recommendations],
            "flashcards": [f.model_dump() for f in n.flashcards]
        }
        for n in notes
    ]

    digest = gemini_service.generate_weekly_digest(notes_data, start_iso, end_iso)
    save_weekly_digest(digest)
    logger.info("Successfully generated and persisted weekly digest.")
    return digest

def init_scheduler():
    """Initializes APScheduler for Sunday 00:00 UTC cron trigger."""
    if not scheduler.running:
        trigger = CronTrigger(day_of_week="sun", hour=0, minute=0, timezone="UTC")
        scheduler.add_job(
            run_weekly_digest_job,
            trigger=trigger,
            id="sunday_weekly_digest",
            name="Sunday Weekly Digest Summary",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler initialized with Sunday 00:00 UTC weekly digest trigger.")
