FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/data \
    && chown -R app:app /app

COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app server.py indexer.py bot.py run.py news.py http_app.py healthcheck.py ./

VOLUME ["/app/data"]

ENV DISCORD_DB_PATH=/app/data/discord.db

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "healthcheck.py"]

STOPSIGNAL SIGTERM

CMD ["python", "run.py"]
