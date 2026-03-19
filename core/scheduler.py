"""
TikTok Clipper — Job Scheduler
Uses APScheduler for scheduled/recurring clip generation jobs.
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

JOBS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.json")


class JobScheduler:
    """Simple job scheduler with persistence."""

    def __init__(self):
        self.jobs = self._load_jobs()

    def _load_jobs(self) -> list[dict]:
        """Load jobs from file."""
        if os.path.exists(JOBS_FILE):
            try:
                with open(JOBS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_jobs(self):
        """Save jobs to file."""
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, indent=2, ensure_ascii=False, default=str)

    def add_job(
        self,
        url: str,
        schedule_time: Optional[str] = None,
        repeat_interval: Optional[str] = None,
        max_clips: int = 5,
    ) -> dict:
        """
        Add a new scheduled job.

        Args:
            url: YouTube URL to process
            schedule_time: ISO format datetime for when to run (None = immediately)
            repeat_interval: "daily", "hourly", or None for one-time
            max_clips: number of clips to generate
        """
        job = {
            "id": str(uuid.uuid4())[:8],
            "url": url,
            "schedule_time": schedule_time,
            "repeat_interval": repeat_interval,
            "max_clips": max_clips,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "results": [],
            "error": None,
        }
        self.jobs.append(job)
        self._save_jobs()
        logger.info(f"Job added: {job['id']} - {url}")
        return job

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a job by ID."""
        for job in self.jobs:
            if job["id"] == job_id:
                return job
        return None

    def update_job(self, job_id: str, **kwargs):
        """Update job fields."""
        for job in self.jobs:
            if job["id"] == job_id:
                job.update(kwargs)
                self._save_jobs()
                return job
        return None

    def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        initial_len = len(self.jobs)
        self.jobs = [j for j in self.jobs if j["id"] != job_id]
        if len(self.jobs) < initial_len:
            self._save_jobs()
            return True
        return False

    def get_all_jobs(self) -> list[dict]:
        """Get all jobs."""
        return self.jobs

    def get_pending_jobs(self) -> list[dict]:
        """Get jobs that are ready to run."""
        now = datetime.now()
        pending = []
        for job in self.jobs:
            if job["status"] == "pending":
                if job["schedule_time"]:
                    scheduled = datetime.fromisoformat(job["schedule_time"])
                    if scheduled <= now:
                        pending.append(job)
                else:
                    pending.append(job)
        return pending

    def mark_completed(self, job_id: str, results: list[dict]):
        """Mark a job as completed."""
        self.update_job(
            job_id,
            status="completed",
            last_run=datetime.now().isoformat(),
            results=results,
            error=None,
        )

    def mark_failed(self, job_id: str, error: str):
        """Mark a job as failed."""
        self.update_job(
            job_id,
            status="failed",
            last_run=datetime.now().isoformat(),
            error=error,
        )
