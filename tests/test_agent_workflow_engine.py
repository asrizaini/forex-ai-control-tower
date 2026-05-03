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
            request_json={"request": "review risk"},
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
    assert task.result_json["risk_status"] == "review_complete_no_execution"
    assert len(messages) == 2

