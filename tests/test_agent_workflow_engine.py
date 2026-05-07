from control.api.db import configure_database, init_db, SessionLocal
from control.api.models import AgentMessage, AgentTask
from agents.workflow_engine import process_one_task


def test_workflow_engine_processes_queued_task(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(tmp_path / "events.jsonl"))
    configure_database(f"sqlite:///{tmp_path / 'workflow.db'}")
    init_db()
    db = SessionLocal()
    db.add(
        AgentTask(
            task_id="task_test",
            requested_by="test",
            assigned_agent="Risk Manager",
            task_type="risk_review",
            request_json={
                "request": "review risk",
                "trading_mode": "monitor_only",
                "daily_loss_pct": 0.0,
                "weekly_loss_pct": 0.0,
                "open_trades": 0,
            },
        )
    )
    db.commit()
    db.close()

    processed = process_one_task()

    db = SessionLocal()
    task = db.query(AgentTask).filter_by(task_id="task_test").one()
    messages = db.query(AgentMessage).filter_by(task_id="task_test").all()
    db.close()
    assert processed == "task_test"
    assert task.status == "completed"
    # With monitor_only mode, RiskManagerAgent correctly blocks execution
    assert task.result_json["risk_status"] == "risk_blocked"
    assert len(messages) == 2

