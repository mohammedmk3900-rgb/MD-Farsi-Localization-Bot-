from app.domain.models import GlossaryTerm, Priority, TaskStatus
from app.domain.permissions import allowed
from app.services.tasks import TaskService
from app.services.translation import TranslationService, tokens


def test_tokens_preserve_hoi4_contract():
    text = "$NAME|H$ [ROOT.GetName] §Y £fuel_texticon"
    assert tokens(text) == {"$NAME|H$", "[ROOT.GetName]", "§Y", "£fuel_texticon"}


def test_translation_detects_missing_and_extra_tokens():
    result = TranslationService().check(
        "$NAME|H$ [ROOT.GetName]",
        "نام [ROOT.GetName] £fuel_texticon",
    )
    kinds = {item["kind"] for item in result.findings}
    assert "missing_token" in kinds
    assert "unexpected_token" in kinds
    assert result.publish_allowed is False


def test_glossary_is_conceptual_contract():
    result = TranslationService().check(
        "Faction leadership",
        "رهبری ائتلاف",
        [GlossaryTerm("Faction", "اتحاد")],
    )
    assert any(item["kind"] == "glossary_consistency" for item in result.findings)


def test_task_lifecycle():
    service = TaskService()
    task = service.create(1, "Translate file A", "common/file_a.yml", Priority.HIGH)
    service.claim(task, "42")
    assert task.status == TaskStatus.IN_PROGRESS
    service.submit(task, "42")
    assert task.status == TaskStatus.REVIEW
    service.complete(task, "reviewer")
    assert task.status == TaskStatus.DONE


def test_permissions_are_role_based():
    assert allowed("translator", "translation.check")
    assert not allowed("translator", "tasks.manage")
    assert allowed("owner", "anything")
