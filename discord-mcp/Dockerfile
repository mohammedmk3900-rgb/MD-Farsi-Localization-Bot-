FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py indexer.py bot.py run.py ./
VOLUME ["/app/data"]
ENV DISCORD_DB_PATH=/app/data/discord.db
EXPOSE 8000
CMD ["python","run.py"]
