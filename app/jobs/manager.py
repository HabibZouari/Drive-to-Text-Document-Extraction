"""Batch runner: processes the selected files in the background and tracks each one."""

import copy
import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path

from app.drive.client import DriveClient, DriveFile
from app.drive.errors import DriveError
from app.extraction.errors import ExtractionError
from app.extraction.languages import normalize_language
from app.extraction.models import ExtractionResult
from app.extraction.router import extract_text
from app.jobs.models import FileResult, FileStatus, Job

logger = logging.getLogger(__name__)

Extractor = Callable[[Path, str, str], ExtractionResult]


class JobManager:
    """Keeps jobs in memory and runs their files on a small worker pool.

    Every file is processed on its own, so a failing file is recorded as
    ``failed`` and never prevents the others from running.
    """

    def __init__(
        self,
        drive: DriveClient,
        max_file_bytes: int,
        *,
        extractor: Extractor = extract_text,
        executor: Executor | None = None,
        max_workers: int = 2,
        max_jobs: int = 50,
    ):
        self._drive = drive
        self._max_file_bytes = max_file_bytes
        self._extractor = extractor
        self._executor = executor or ThreadPoolExecutor(max_workers, thread_name_prefix="extract")
        self._max_jobs = max_jobs
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()

    def create_job(self, files: list[DriveFile], language: str) -> str:
        """Register a batch and start processing it. Returns the job id."""
        if not files:
            raise ValueError("A batch needs at least one file.")
        job = Job(
            id=uuid.uuid4().hex,
            language=normalize_language(language),
            results=[FileResult(file=file) for file in files],
        )
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > self._max_jobs:
                self._jobs.popitem(last=False)  # forget the oldest job

        for result in job.results:
            self._executor.submit(self._process, job, result)
        return job.id

    def get_job(self, job_id: str) -> Job | None:
        """Return a consistent copy of the job, safe to read while workers keep running."""
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._drive.close()

    def _process(self, job: Job, result: FileResult) -> None:
        self._update(result, status=FileStatus.PROCESSING)
        started = time.perf_counter()
        try:
            with self._drive.temporary_download(result.file, self._max_file_bytes) as path:
                extraction = self._extractor(path, result.file.kind, job.language)
            outcome = {
                "status": FileStatus.DONE,
                "text": extraction.text,
                "method": extraction.method,
            }
        except (DriveError, ExtractionError) as exc:
            outcome = {"status": FileStatus.FAILED, "error": str(exc)}
        except Exception:
            logger.exception("Unexpected error while processing %s", result.file.id)
            outcome = {
                "status": FileStatus.FAILED,
                "error": "Unexpected error while processing this file.",
            }
        outcome["duration_ms"] = round((time.perf_counter() - started) * 1000)
        self._update(result, **outcome)

    def _update(self, result: FileResult, **fields) -> None:
        with self._lock:
            for name, value in fields.items():
                setattr(result, name, value)
