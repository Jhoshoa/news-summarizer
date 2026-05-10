from datetime import date, datetime

from src.db.repository import Database


def test_normalize_payload_serializes_datetime_values_recursively():
    db = object.__new__(Database)

    payload = db._normalize_payload(
        {
            "published_at": datetime(2026, 5, 10, 12, 30),
            "content_collected_at": datetime(2026, 5, 10, 12, 31),
            "metadata": {
                "seen_on": date(2026, 5, 10),
                "snapshots": [datetime(2026, 5, 10, 12, 32)],
            },
        }
    )

    assert payload == {
        "published_at": "2026-05-10T12:30:00",
        "content_collected_at": "2026-05-10T12:31:00",
        "metadata": {
            "seen_on": "2026-05-10",
            "snapshots": ["2026-05-10T12:32:00"],
        },
    }
