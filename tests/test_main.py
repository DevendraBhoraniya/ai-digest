from datetime import datetime, timezone

import app.scheduler as scheduler
import main as main_module
from app.runner import CycleResult


def _result(status="success", videos=3, transcripts=1, sent=True, error=None):
    return CycleResult(
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        status=status,
        videos_scraped=videos,
        transcripts_fetched=transcripts,
        digest_sent=sent,
        error=error,
    )


def test_run_once_prints_actual_video_count(monkeypatch, capsys):
    monkeypatch.setattr(main_module, "run_cycle", lambda: _result(videos=7))

    result = main_module.run_once()

    output = capsys.readouterr().out
    assert "scraped 7 videos" in output
    assert result.videos_scraped == 7


def test_main_run_once_success_exits_zero(monkeypatch):
    monkeypatch.setattr(main_module, "run_cycle", lambda: _result())

    assert main_module.main(["--run-once"]) == 0


def test_main_run_once_failure_exits_nonzero(monkeypatch):
    monkeypatch.setattr(
        main_module, "run_cycle", lambda: _result(status="failed", sent=False, error="boom")
    )

    assert main_module.main(["--run-once"]) == 1


def test_main_partial_run_exits_zero(monkeypatch):
    monkeypatch.setattr(main_module, "run_cycle", lambda: _result(status="partial"))

    assert main_module.main(["--run-once"]) == 0


def test_main_serve_delegates_to_scheduler(monkeypatch):
    called = []
    monkeypatch.setattr(scheduler, "start_scheduler", lambda: called.append(True))

    assert main_module.main(["--serve"]) == 0
    assert called == [True]
