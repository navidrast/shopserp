"""Background scheduler for periodic monitor checks.

Uses APScheduler's :class:`AsyncIOScheduler` to run a job every 10 minutes
that finds all monitors that are due for a check and dispatches scrape
tasks with a concurrency semaphore.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.config import settings
from backend.database import async_session_factory
from backend.models import Monitor
from backend.services.monitor import MonitorService

logger = logging.getLogger(__name__)

_monitor_service = MonitorService()
_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)

# Module-level scheduler reference.  Initialised by :func:`start_scheduler`.
scheduler: object | None = None


async def check_due_monitors() -> None:
    """Find and run all monitors that are due for checking.

    A monitor is considered "due" when:
    - ``enabled`` is True, **and**
    - ``last_checked`` is ``None`` (never checked), **or**
    - ``last_checked + interval_minutes`` is in the past.
    """
    logger.info("Scheduler: checking for due monitors...")
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        try:
            stmt = select(Monitor).where(Monitor.enabled.is_(True))
            result = await db.execute(stmt)
            monitors = list(result.scalars().all())

            due: list[Monitor] = []
            for m in monitors:
                if m.last_checked is None:
                    due.append(m)
                else:
                    next_check = m.last_checked + timedelta(
                        minutes=m.interval_minutes
                    )
                    if next_check <= now:
                        due.append(m)

            if not due:
                logger.info("Scheduler: no monitors are due.")
                return

            logger.info(
                "Scheduler: %d monitor(s) due for checking.", len(due),
            )

            tasks = [_run_with_semaphore(m.id) for m in due]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for monitor, result in zip(due, results):
                if isinstance(result, BaseException):
                    logger.error(
                        "Scheduler: monitor id=%d failed: %s",
                        monitor.id,
                        result,
                    )

        except Exception:
            logger.exception("Scheduler: unexpected error in check_due_monitors")


async def _run_with_semaphore(monitor_id: int) -> None:
    """Run a single monitor check within the concurrency semaphore."""
    async with _semaphore:
        async with async_session_factory() as db:
            try:
                await _monitor_service.run_monitor_check(db, monitor_id)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception(
                    "Scheduler: error running monitor id=%d", monitor_id,
                )
                raise


def start_scheduler() -> None:
    """Start the APScheduler background scheduler.

    Adds a single interval job that runs :func:`check_due_monitors` every
    10 minutes.  Safe to call multiple times; subsequent calls are no-ops.
    """
    global scheduler

    if scheduler is not None:
        logger.debug("Scheduler already running; skipping start.")
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        sched = AsyncIOScheduler()
        sched.add_job(
            check_due_monitors,
            "interval",
            minutes=10,
            id="monitor_check",
            replace_existing=True,
        )
        sched.start()
        scheduler = sched
        logger.info("Background scheduler started (interval=10min).")
    except ImportError:
        logger.warning(
            "apscheduler is not installed; background scheduling disabled."
        )
    except Exception:
        logger.exception("Failed to start background scheduler.")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler if running."""
    global scheduler

    if scheduler is None:
        return

    try:
        scheduler.shutdown(wait=False)  # type: ignore[union-attr]
        logger.info("Background scheduler stopped.")
    except Exception:
        logger.exception("Error stopping scheduler.")
    finally:
        scheduler = None
