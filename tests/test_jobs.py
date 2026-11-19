import logging
import time

import pytest

from app.drive.errors import FileTooLargeError, FolderNotAccessibleError
from app.extraction.errors import ExtractionError
from app.extraction.models import Method
from app.jobs.manager import JobManager
from app.jobs.models import FileStatus, JobStatus
from tests.fakes import DeferredExecutor, FakeDrive, SynchronousExecutor, image, make_extractor, pdf

MAX_BYTES = 1024


def make_manager(drive=None, extractor=None, executor=None, **options):
    return JobManager(
        drive or FakeDrive(),
        MAX_BYTES,
        extractor=extractor or make_extractor(),
        executor=executor or SynchronousExecutor(),
        **options,
    )


def statuses(job):
    return {r.file.id: r.status for r in job.results}


def test_every_file_is_processed_and_the_job_completes():
    manager = make_manager()
    job_id = manager.create_job([pdf("a"), image("b")], "eng")

    job = manager.get_job(job_id)

    assert job.status is JobStatus.COMPLETED
    assert statuses(job) == {"a": FileStatus.DONE, "b": FileStatus.DONE}
    first, second = job.results
    assert (first.text, first.method) == ("text of a", Method.PDF_PARSER)
    assert (second.text, second.method) == ("text of b", Method.OCR)
    assert first.duration_ms is not None and first.error is None


def test_a_failing_file_does_not_stop_the_batch():
    errors = {"b": ExtractionError("This file is not a valid PDF or is corrupted.")}
    manager = make_manager(extractor=make_extractor(errors))

    job_id = manager.create_job([pdf("a"), pdf("b"), pdf("c")], "eng")
    job = manager.get_job(job_id)

    assert job.status is JobStatus.COMPLETED
    assert statuses(job) == {
        "a": FileStatus.DONE,
        "b": FileStatus.FAILED,
        "c": FileStatus.DONE,
    }
    failed = job.results[1]
    assert failed.error == "This file is not a valid PDF or is corrupted."
    assert failed.text is None and failed.method is None
    assert failed.duration_ms is not None
    assert job.results[2].text == "text of c"  # the file after the failure still ran


def test_a_download_failure_only_fails_that_file():
    drive = FakeDrive(
        download_errors={
            "big": FileTooLargeError("File is larger than the 25 MB limit."),
            "gone": FolderNotAccessibleError("This file cannot be downloaded."),
        }
    )
    manager = make_manager(drive=drive)

    job = manager.get_job(manager.create_job([pdf("big"), pdf("ok"), pdf("gone")], "eng"))

    assert statuses(job) == {
        "big": FileStatus.FAILED,
        "ok": FileStatus.DONE,
        "gone": FileStatus.FAILED,
    }
    assert job.results[0].error == "File is larger than the 25 MB limit."


def test_an_unexpected_crash_is_contained_and_not_leaked_to_the_user(caplog):
    errors = {"b": RuntimeError("secret internal detail /etc/passwd")}
    manager = make_manager(extractor=make_extractor(errors))

    with caplog.at_level(logging.ERROR):
        job = manager.get_job(manager.create_job([pdf("a"), pdf("b"), pdf("c")], "eng"))

    assert statuses(job) == {
        "a": FileStatus.DONE,
        "b": FileStatus.FAILED,
        "c": FileStatus.DONE,
    }
    assert job.results[1].error == "Unexpected error while processing this file."
    assert "secret internal detail" not in job.results[1].error
    assert "secret internal detail" in caplog.text  # but it is logged for the developer


def test_job_is_running_until_every_file_is_finished():
    executor = DeferredExecutor()
    manager = make_manager(executor=executor)

    job_id = manager.create_job([pdf("a"), pdf("b")], "eng")
    job = manager.get_job(job_id)
    assert job.status is JobStatus.RUNNING
    assert job.count(FileStatus.PENDING) == 2

    executor.run_all()
    job = manager.get_job(job_id)
    assert job.status is JobStatus.COMPLETED
    assert job.count(FileStatus.DONE) == 2


def test_results_keep_the_order_of_the_selection():
    manager = make_manager()
    job = manager.get_job(manager.create_job([pdf("z"), pdf("a"), image("m")], "eng"))
    assert [r.file.id for r in job.results] == ["z", "a", "m"]


def test_language_is_normalised_and_given_to_the_extractor():
    calls = []
    manager = make_manager(extractor=make_extractor(calls=calls))

    job = manager.get_job(manager.create_job([image("a")], "FRA+eng"))

    assert job.language == "fra+eng"
    assert calls == [("a", "image", "fra+eng")]


def test_invalid_language_is_rejected_before_anything_runs():
    calls = []
    manager = make_manager(extractor=make_extractor(calls=calls))

    with pytest.raises(ExtractionError, match="Unsupported OCR language"):
        manager.create_job([pdf("a")], "klingon")
    assert calls == []


def test_a_batch_needs_at_least_one_file():
    with pytest.raises(ValueError, match="at least one file"):
        make_manager().create_job([], "eng")


def test_unknown_job_returns_none():
    assert make_manager().get_job("missing") is None


def test_get_job_returns_a_copy_that_cannot_corrupt_the_state():
    manager = make_manager()
    job_id = manager.create_job([pdf("a")], "eng")

    copy = manager.get_job(job_id)
    copy.results[0].status = FileStatus.FAILED
    copy.results[0].text = "tampered"

    original = manager.get_job(job_id)
    assert original.results[0].status is FileStatus.DONE
    assert original.results[0].text == "text of a"


def test_oldest_jobs_are_forgotten_beyond_the_limit():
    manager = make_manager(max_jobs=2)
    first = manager.create_job([pdf("a")], "eng")
    second = manager.create_job([pdf("b")], "eng")
    third = manager.create_job([pdf("c")], "eng")

    assert manager.get_job(first) is None
    assert manager.get_job(second) is not None
    assert manager.get_job(third) is not None


def test_close_releases_the_drive_client():
    drive = FakeDrive()
    make_manager(drive=drive).close()
    assert drive.closed


def test_real_worker_threads_process_a_large_batch_with_failures():
    errors = {f"f{i}": ExtractionError("bad file") for i in range(0, 40, 4)}
    manager = JobManager(
        FakeDrive(),
        MAX_BYTES,
        extractor=make_extractor(errors),
        max_workers=4,
    )
    job_id = manager.create_job([pdf(f"f{i}") for i in range(40)], "eng")

    deadline = time.time() + 10
    while manager.get_job(job_id).status is not JobStatus.COMPLETED:
        assert time.time() < deadline, "the batch did not finish in time"
        time.sleep(0.02)

    job = manager.get_job(job_id)
    assert job.count(FileStatus.DONE) == 30
    assert job.count(FileStatus.FAILED) == 10
    manager.close()
