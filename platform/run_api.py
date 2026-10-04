from __future__ import annotations

import uvicorn

from app.application import application


if __name__ == "__main__":
    settings = application.context.settings
    settings.scheduler_embedded = True
