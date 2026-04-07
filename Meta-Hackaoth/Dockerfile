FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONPATH=/app
# Hugging Face Spaces set PORT=7860 for the public listener.
ENV PORT=7860

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

RUN chmod +x /app/scripts/run_hf_space.sh /app/scripts/run_api_only.sh

# Default: Space UI (Streamlit on $PORT) + API on 8000 inside the container.
CMD ["/app/scripts/run_hf_space.sh"]
