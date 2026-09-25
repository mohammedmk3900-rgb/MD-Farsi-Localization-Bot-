import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.persistence.database import Database
from app.services.automation import Automation


class FakeDiscord:
    def __init__(self):
        self.embeds = []

    def embed(self, channel, title, description):
        self.embeds.append((channel, title, description))
        return {"id": str(len(self.embeds))}


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "platform.db")
        self.db.initialize()

        self.settings = SimpleNamespace(
            channel_progress="progress",
            channel_stats="stats",
            channel_achievements="achievements",
            channel_glossary="glossary",
            discord_bot_token="test",
            discord_intelligence_path="data/discord_intelligence.json",
        )
        self.application = SimpleNamespace(
            context=SimpleNamespace(settings=self.settings, database=self.db),
            events=[],
        )
        self.application.record = lambda event_type, payload: self.application.events.append((event_type, payload))

    def tearDown(self):
        self.temp.cleanup()

    def _snapshot(self, translated, reviewed, percent):
        return {
            "project": {
                "translated": translated,
                "reviewed": reviewed,
                "strings_total": 100,
                "words_total": 1000,
                "files": 10,
                "members": 5,
                "translation_percent": percent,
                "review_percent": reviewed,
            }
        }

    def test_project_publication_is_idempotent(self):
        self.db.save_snapshot("2026-09-25T00:00:00+00:00", 1, self._snapshot(10, 5, 10))
        self.db.save_snapshot("2026-09-25T01:00:00+00:00", 1, self._snapshot(11, 6, 11))

        automation = Automation(self.application)
        fake = FakeDiscord()
        automation.discord = fake

        first = automation.publish_project()
        second = automation.publish_project()

        self.assertTrue(first["progress"])
        self.assertTrue(first["stats"])
        self.assertEqual(second["achievements"], 0)
        self.assertEqual(len(fake.embeds), 3)
        self.assertEqual(len([x for x in fake.embeds if x[0] == "progress"]), 1)

    def test_project_quality_alerts_detect_bad_state(self):
        automation = Automation(self.application)
        alerts = automation._project_quality_alerts(
            {"translation_percent": 10, "review_percent": 12, "translated": 101, "strings_total": 100},
            {"translation_percent": 11},
        )
        self.assertEqual(len(alerts), 3)

    def test_glossary_qa_detects_conflicts_and_duplicates(self):
        automation = Automation(self.application)
        qa = automation._glossary_qa([
            {"source": "Faction", "target": "اتحاد", "description": ""},
            {"source": "Faction", "target": "ائتلاف", "description": ""},
            {"source": "Faction", "target": "اتحاد", "description": ""},
            {"source": "", "target": "", "description": ""},
        ])
        self.assertEqual(qa["conflicting_sources"], 1)
        self.assertEqual(qa["duplicates"], 1)
        self.assertEqual(qa["empty_or_incomplete"], 1)

    def test_glossary_is_published_only_when_changed(self):
        automation = Automation(self.application)
        fake = FakeDiscord()
        automation.discord = fake
        terms = [{"source": "Faction", "target": "اتحاد"}]

        first = automation.publish_glossary(terms)
        second = automation.publish_glossary(terms)

        self.assertTrue(first["published"])
        self.assertFalse(second["published"])
        self.assertEqual(len(fake.embeds), 1)


if __name__ == "__main__":
    unittest.main()
