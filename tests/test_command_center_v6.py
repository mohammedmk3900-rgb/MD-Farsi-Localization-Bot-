import unittest
from datetime import datetime, timezone

from scripts.command_center.models import ProjectStats
from scripts.command_center.services.progress import crossed, delta
from scripts.command_center.services.versioning import bump_patch, canonical_hash, compare_month


class ProgressTests(unittest.TestCase):
    def test_delta(self):
        current = ProjectStats(10, 1000, 250, 100, 5000)
        previous = {"translated": 200, "reviewed": 90, "translation_percent": 20.0, "review_percent": 9.0}
        result = delta(current, previous)
        self.assertEqual(result.translated, 50)
        self.assertEqual(result.reviewed, 10)
        self.assertEqual(result.translation_percent, 5.0)
        self.assertEqual(result.review_percent, 1.0)

    def test_milestones(self):
        self.assertEqual(crossed(9.5, 25.0), [10, 25])
        self.assertEqual(crossed(25.0, 25.0), [])


class VersioningTests(unittest.TestCase):
    def test_patch_bump(self):
        self.assertEqual(bump_patch("1.0.9"), "1.0.10")
        self.assertEqual(bump_patch("broken"), "1.0.1")

    def test_hash_is_deterministic(self):
        self.assertEqual(canonical_hash({"b": 2, "a": 1}), canonical_hash({"a": 1, "b": 2}))

    def test_month_boundary(self):
        current = datetime(2026, 9, 21, tzinfo=timezone.utc)
        self.assertTrue(compare_month("2026-08-31T00:00:00+00:00", current))
        self.assertFalse(compare_month("2026-09-01T00:00:00+00:00", current))


if __name__ == "__main__":
    unittest.main()
