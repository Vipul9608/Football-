# Pitchside: container image for Render, Hugging Face Spaces (Docker SDK) or any container host.
#   docker build -t pitchside .
#   docker run -p 8501:8501 -e API_FOOTBALL_KEY=your-key pitchside      # key is optional
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Secrets can come from environment variables instead of secrets.toml (see README).
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8501\")}/_stcore/health')"
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
