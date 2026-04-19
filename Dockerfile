FROM python:3.11-slim

WORKDIR /app

# System deps for faiss / sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git git-lfs && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so runtime startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

EXPOSE 7860

# HF Spaces expects port 7860
CMD ["python", "-c", "import app; app.app.run(host='0.0.0.0', port=7860, debug=False)"]