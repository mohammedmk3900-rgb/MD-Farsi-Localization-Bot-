from datetime import datetime, timezone

from app.domain.models import ProjectSnapshot


def test_progress_percentages():
    snapshot = ProjectSnapshot(
        project_id=19621,
        captured_at=datetime.now(timezone.utc),
        words_total=1000,
        strings_total=200,
        translated=50,
        reviewed=20,
        files=10,
        members=8,
    )
    assert snapshot.translation_percent == 25
    assert snapshot.review_percent == 10
