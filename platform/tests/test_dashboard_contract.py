import unittest

from app.services.dashboard import DashboardService


class DashboardContractTests(unittest.TestCase):
    def test_contract_is_secret_free(self):
        result = DashboardService().public_contract({
            "project": {"project_id": 19621, "translated": 10, "reviewed": 5},
            "health": {"status": "healthy"},
            "discord": {"guild_name": "MD", "channels": [], "roles": []},
            "token": "should-not-be-public",
        })
        self.assertEqual(result["project"]["project_id"], 19621)
        self.assertNotIn("token", result)
        self.assertEqual(result["discord"]["channels"], 0)


if __name__ == "__main__":
    unittest.main()
