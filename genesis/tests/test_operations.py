from app.domain.models import Task, TaskStatus
from app.services.progress import ProgressService
from app.services.scheduling import ReminderService


def test_member_progress_is_non_negative():
    result = ProgressService().member("42", -1, 2, 3)
    assert result.completed == 0


def test_overdue_reminder():
    task = Task(1, "Translate", owner="42", status=TaskStatus.IN_PROGRESS, due_at="2026-09-24T00:00:00+00:00")
    reminders = ReminderService().overdue([task], "2026-09-25T00:00:00+00:00")
    assert reminders[0].member_id == "42"
