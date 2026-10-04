import uvicorn

from app.application import application


if __name__ == "__main__":
    settings = application.context.settings
    uvicorn.run("app.api.main:app", host=settings.api_host, port=settings.api_port, reload=False)
