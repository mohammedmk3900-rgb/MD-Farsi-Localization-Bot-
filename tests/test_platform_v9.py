import json
import subprocess
import unittest
from pathlib import Path

from scripts.command_center.models import ProjectStats
from scripts.command_center.services.progress import crossed, delta


class V9ContractTests(unittest.TestCase):
    def test_progress_delta(self):
        current = ProjectStats(2, 100, 25, 10, 500)
        result = delta(current, {"translated": 20, "reviewed": 8, "translation_percent": 20, "review_percent": 8})
        self.assertEqual(result.translated, 5)
        self.assertEqual(result.reviewed, 2)
        self.assertEqual(result.translation_percent, 5)
        self.assertEqual(result.review_percent, 2)

    def test_crossed_milestones(self):
        self.assertEqual(crossed(9.9, 25), [10, 25])

    def test_public_contract_fixture_has_no_secrets(self):
        fixture = Path("dashboard/public/data/dashboard.json")
        if not fixture.exists():
            self.skipTest("generated dashboard contract is not committed")
        raw = fixture.read_text(encoding="utf-8")
        self.assertNotIn("PARATRANZ_TOKEN", raw)
        self.assertNotIn("DISCORD_", raw)
        payload = json.loads(raw)
        self.assertEqual(payload.get("schema"), 9)

    def test_rust_contract_files_exist(self):
        self.assertTrue(Path("rust/Cargo.toml").exists())
        self.assertTrue(Path("rust/src/main.rs").exists())


if __name__ == "__main__":
    unittest.main()
