import tempfile
import unittest

from app.persistence.database import Database
from app.services.permissions import allowed
from app.services.tasks import TaskService
from app.services.translation_assistant import TranslationAssistant


class V10Tests(unittest.TestCase):
    def test_translation_assistant_preserves_tokens(self):
        result = TranslationAssistant().check(
            "Faction $COUNTRY|Y$ £fuel_texticon",
            "اتحاد $COUNTRY|Y$ £fuel_texticon",
            [{"term": "Faction", "translation": "اتحاد"}],
        )
        self.assertTrue(result["approved"])
        self.assertFalse(result["publish"])

    def test_translation_assistant_detects_missing_token(self):
        result = TranslationAssistant().check(
            "Faction $COUNTRY|Y$",
            "اتحاد",
            [{"term": "Faction", "translation": "اتحاد"}],
        )
        self.assertFalse(result["approved"])
        self.assertEqual(result["findings"][0]["kind"], "broken_placeholder")

    def test_task_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/platform.db")
            db.initialize()
            service = TaskService(db)
            task = service.create("Translate decisions", scope="100 strings")
            claimed = service.claim(task["id"], "mk")
            self.assertEqual(claimed["status"], "in_progress")
            submitted = service.submit(task["id"], "mk")
            self.assertEqual(submitted["status"], "review")
            done = service.complete(task["id"], "reviewer")
            self.assertEqual(done["status"], "done")

    def test_permissions(self):
        self.assertTrue(allowed("owner", "anything"))
        self.assertTrue(allowed("translator", "translation.check"))
        self.assertFalse(allowed("translator", "tasks.manage"))


if __name__ == "__main__":
    unittest.main()
