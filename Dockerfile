# REST API služby. Obraz obsahuje jen kód služby a data, ze kterých hledá (úseky + uložené vektory a odpovědi).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
WORKDIR /app

COPY requirements-service.txt .
RUN pip install --no-cache-dir -r requirements-service.txt

COPY tools/rag.py tools/service.py tools/api.py tools/answer_checks.py tools/
COPY data/chunks.json data/emb_cache.npz data/llm_cache.json data/

# bez roota; složka data musí být zapisovatelná, nové odpovědi modelu se ukládají do cache
RUN useradd --create-home app && chown -R app /app/data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "api:app", "--app-dir", "tools", "--host", "0.0.0.0", "--port", "8000"]
