import unittest

from app.services.achievements import AchievementService
from app.services.analytics import AnalyticsService
from app.services.migration import migration_contract


class ServiceTests(unittest.TestCase):
    def test_delta(self):
        result = AnalyticsService().delta({"translated": 20, "reviewed": 5}, {"translated": 10, "reviewed": 2})
        self.assertEqual(result["delta_translated"], 10)
        self.assertEqual(result["delta_reviewed"], 3)

    def test_milestones(self):
        self.assertEqual(AnalyticsService().milestones(9, 26), [10, 25])

    def test_achievements(self):
        self.assertEqual([x["percent"] for x in AchievementService().crossed(9, 26)], [10, 25])

    def test_webhooks_are_migration_only(self):
        contract = migration_contract()
        self.assertEqual(contract["replacement"], "MD news Bot API")
        self.assertIn("DISCORD_WEBHOOK_URL", contract["legacy_env_to_remove"])


if __name__ == "__main__":
    unittest.main()
