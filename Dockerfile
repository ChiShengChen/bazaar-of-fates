# Bazaar of Fates — API + static page in one container (Hugging Face Space / any Docker host).
# Mock reader by default (no API key). Set LLM_BACKEND=anthropic + ANTHROPIC_API_KEY for real readings.
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=7860 CORS_ORIGINS=* LLM_BACKEND=mock
COPY pyproject.toml README.md LICENSE ./
COPY fortune ./fortune
COPY web/index.html ./web/index.html
RUN pip install --no-cache-dir -e ".[oracles]" 2>/dev/null || pip install --no-cache-dir -e .
EXPOSE 7860
CMD ["sh", "-c", "uvicorn fortune.api.main:app --host 0.0.0.0 --port ${PORT}"]
