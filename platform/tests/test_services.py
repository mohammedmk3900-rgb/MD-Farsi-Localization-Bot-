import tempfile
import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import ProjectSnapshot
from app.persistence.database import Database
from app.services.achievements import AchievementService
from app.services.analytics import AnalyticsService
from app.services.command_center import CommandCenter


class ServiceTests(unittest.TestCase):
    def test_delta(self):
        result = AnalyticsService().delta({"translated": 20, "reviewed": 5}, {"translated": 10, "reviewed": 2})
        self.assertEqual(result["delta_translated"], 10)
        self.assertEqual(result["delta_reviewed"], 3)

    def test_milestones(self):
        self.assertEqual(AnalyticsService().milestones(9, 26), [10, 25])

    def test_achievements(self):
        self.assertEqual([x["percent"] for x in AchievementService().crossed(9, 26)], [10, 25])

    def test_command_center_survives_discord_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/platform.db")
            db.initialize()
            settings = Settings(
                paratranz_token="test-token",
                discord_bot_token="test-discord-token",
                discord_guild_id="123",
                database_path=f"{directory}/platform.db",
            )
            fake = ProjectSnapshot(
                project_id=19621,
                captured_at="2026-09-24T00:00:00+00:00",
                words_total=100,
                strings_total=50,
                translated=10,
                reviewed=5,
                files=2,
                members=3,
            )
            with patch("app.services.command_center.ParaTranzClient.project_snapshot", return_value=fake):
                with patch("app.services.command_center.DiscordClient.snapshot", side_effect=RuntimeError("Discord down")):
                    result = CommandCenter(settings, db).collect()

            self.assertEqual(result.project.translated, 10)
            self.assertIsNone(result.discord)
            self.assertEqual(result.health.status, "degraded")
            self.assertTrue(result.health.paratranz)
            self.assertFalse(result.health.discord)
            self.assertTrue(result.health.database)


if __name__ == "__main__":
    unittest.main()
