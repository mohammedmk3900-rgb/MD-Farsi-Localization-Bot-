from pathlib import Path

from app.domain.models import TaskStatus
from app.integrations.discord import DiscordActor, DiscordCommandGateway, DiscordTransport
from app.persistence.store import Store
from app.services.application import GenesisApplication


def build(tmp_path: Path):
    app = GenesisApplication(Store(tmp_path / "genesis.db"))
    app.initialize()
    return app


def test_task_survives_application_restart(tmp_path):
    first = build(tmp_path)
    task = first.tasks.create(title="Review glossary", scope="terms")
    first.tasks.claim(task, "member-1")
    first.tasks.submit(task, "member-1")

    second = build(tmp_path)
    restored = second.tasks.get(task.id)
    assert restored.status == TaskStatus.REVIEW
    assert restored.owner == "member-1"


def test_review_survives_restart_until_decided(tmp_path):
    first = build(tmp_path)
    item = first.reviews.submit("member-1", first.translation.check("Hello", "سلام", []))
    second = build(tmp_path)
    assert [x.id for x in second.reviews.pending()] == [item.id]
    second.reviews.decide(item.id, "approve", "reviewer-1")

    third = build(tmp_path)
    assert third.reviews.pending() == []


def test_discord_transport_reads_command_center(tmp_path):
    app = build(tmp_path)
    transport = DiscordTransport(DiscordCommandGateway(app))
    result = transport.dispatch(DiscordActor("u1", ("manager",)), "status")
    assert "tasks" in result


def test_mission_and_notification_pipeline_survives_restart(tmp_path):
    first = build(tmp_path)
    mission = first.mission_engine.generate(["ترجمه هسته"], limit=1)[0]
    assert mission.status == "open"

    task = first.mission_engine.activate(mission.id)
    assert task.id == mission.task_id if mission.task_id is not None else task.id

    first.events.publish(
        "mission.assigned",
        "manager-1",
        {"mission_id": mission.id},
        notifications=[("member-1", "مأموریت جدید برای شما ایجاد شد.")],
    )

    second = build(tmp_path)
    restored = second.mission_engine.list()[0]
    assert restored.status == "active"
    assert restored.task_id == task.id

    notifications = second.events.pending_notifications("member-1")
    assert len(notifications) == 1
    assert notifications[0].event_type == "mission.assigned"

    second.events.acknowledge(notifications[0].id)
    third = build(tmp_path)
    assert third.events.pending_notifications("member-1") == []
