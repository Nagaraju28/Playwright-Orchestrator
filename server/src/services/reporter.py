from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..models.job import Job, JobStatus
from ..models.test_result import TestCaseResult, TestStatus

class PlaywrightReportParser:
    """Parses standard Playwright JSON test output and aggregates metrics into the database."""

    @classmethod
    def parse_and_persist(cls, db: Session, job_id: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job '{job_id}' not found")

        stats = report_data.get("stats", {})
        suites = report_data.get("suites", [])

        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        parsed_results: List[TestCaseResult] = []

        def process_suite(suite: Dict[str, Any], suite_name_prefix: str = ""):
            nonlocal total_tests, passed_tests, failed_tests, skipped_tests
            current_title = suite.get("title", "")
            full_suite_name = f"{suite_name_prefix}/{current_title}".strip("/") if suite_name_prefix else current_title

            # Process individual specs
            for spec in suite.get("specs", []):
                spec_title = spec.get("title", "Untitled Test")
                file_path = suite.get("file", full_suite_name)

                for test in spec.get("tests", []):
                    total_tests += 1
                    status_raw = test.get("status", "expected")
                    
                    # Extract last result
                    results = test.get("results", [])
                    last_result = results[-1] if results else {}
                    run_status_raw = last_result.get("status", "passed")
                    duration_ms = int(last_result.get("duration", 0))

                    if run_status_raw == "passed" and status_raw in ("expected", "flaky"):
                        status_enum = TestStatus.PASSED
                        passed_tests += 1
                    elif run_status_raw in ("timedOut", "timeout"):
                        status_enum = TestStatus.TIMED_OUT
                        failed_tests += 1
                    elif run_status_raw == "skipped":
                        status_enum = TestStatus.SKIPPED
                        skipped_tests += 1
                    else:
                        status_enum = TestStatus.FAILED
                        failed_tests += 1

                    # Extract error info
                    err_obj = last_result.get("error", {})
                    err_msg = err_obj.get("message") if isinstance(err_obj, dict) else str(err_obj) if err_obj else None
                    err_stack = err_obj.get("stack") if isinstance(err_obj, dict) else None

                    # Extract artifact attachments
                    screenshot_url = None
                    trace_url = None
                    video_url = None
                    extra_attachments = []

                    for att in last_result.get("attachments", []):
                        name = att.get("name", "").lower()
                        path = att.get("path")
                        if "screenshot" in name or (path and path.endswith(".png")):
                            screenshot_url = path
                        elif "trace" in name or (path and path.endswith(".zip")):
                            trace_url = path
                        elif "video" in name or (path and path.endswith(".webm")):
                            video_url = path
                        else:
                            extra_attachments.append(att)

                    test_case = TestCaseResult(
                        job_id=job.id,
                        suite_name=full_suite_name,
                        test_title=spec_title,
                        file_path=file_path,
                        status=status_enum,
                        duration_ms=duration_ms,
                        retry_count=test.get("retries", 0),
                        error_message=err_msg,
                        error_stacktrace=err_stack,
                        screenshot_url=screenshot_url,
                        trace_url=trace_url,
                        video_url=video_url,
                        extra_artifacts=extra_attachments if extra_attachments else None,
                    )
                    parsed_results.append(test_case)

            # Recurse into child suites
            for child in suite.get("suites", []):
                process_suite(child, full_suite_name)

        for s in suites:
            process_suite(s)

        # Bulk save test case records
        if parsed_results:
            db.bulk_save_objects(parsed_results)

        # Update Job summary metrics
        job.total_tests = total_tests
        job.passed_tests = passed_tests
        job.failed_tests = failed_tests
        job.skipped_tests = skipped_tests
        job.execution_duration_ms = int(stats.get("duration", job.execution_duration_ms or 0))

        if failed_tests > 0:
            job.status = JobStatus.FAILED
            job.error_summary = f"{failed_tests} out of {total_tests} tests failed."
        elif total_tests > 0 and failed_tests == 0:
            job.status = JobStatus.COMPLETED

        db.commit()

        return {
            "job_id": job.id,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "duration_ms": job.execution_duration_ms,
        }
