"""ParaTranz collector with one API implementation for the whole Command Center."""
from __future__ import annotations
from typing import Any
from ..config import Config
from ..http_client import request_json
from ..models import ProjectStats

def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0

def collect_files(config: Config) -> list[dict[str, Any]]:
    if not config.paratranz_token:
        raise RuntimeError("PARATRANZ_TOKEN is not set.")
    data = request_json(
        config.api_url,
        headers={
            "Authorization": config.paratranz_token,
            "User-Agent": "MD-Farsi-Localization-Command-Center/7.0",
        },
        retries=4,
    )
    if not isinstance(data, list):
        raise RuntimeError("Unexpected ParaTranz files response.")
    return [item for item in data if isinstance(item, dict)]

def collect_stats(config: Config) -> tuple[ProjectStats, list[dict[str, Any]]]:
    files = collect_files(config)
    stats = ProjectStats(
        files=len(files),
        strings=sum(_number(x.get("total")) for x in files),
        translated=sum(_number(x.get("translated")) for x in files),
        reviewed=sum(_number(x.get("reviewed")) for x in files),
        words=sum(_number(x.get("words")) for x in files),
    )
    return stats, files
