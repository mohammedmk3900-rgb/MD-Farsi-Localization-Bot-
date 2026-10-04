from __future__ import annotations

import uvicorn

from app.config import Settings

settings = Settings()


if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
