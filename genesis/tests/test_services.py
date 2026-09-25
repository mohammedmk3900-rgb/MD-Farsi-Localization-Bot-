from app.domain.models import GlossaryTerm
from app.services.achievements import AchievementService
from app.services.glossary import GlossaryService
from app.services.missions import MissionService
from app.services.review import ReviewDecision, ReviewQueue
from app.services.translation import TranslationService


def test_glossary_source_of_truth_lookup():
    service = GlossaryService([GlossaryTerm("Faction", "اتحاد")])
    assert service.find("faction")[0].target == "اتحاد"


def test_missions_are_bounded():
    missions = MissionService().generate(["a", "b", "c"], limit=2)
    assert len(missions) == 2


def test_review_is_human_decision():
    queue = ReviewQueue()
    item = queue.submit("translator", TranslationService().check("hello", "سلام"))
    result = queue.decide(item.id, ReviewDecision.APPROVE, "reviewer")
    assert result["reviewer"] == "reviewer"


def test_achievements():
    earned = AchievementService().earned(10)
    assert {a.key for a in earned} == {"first_task", "ten_tasks"}
