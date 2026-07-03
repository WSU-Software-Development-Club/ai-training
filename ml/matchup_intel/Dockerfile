# Matchup Intelligence pipeline service (runs on troyster; reaches db:5432 and
# ollama:11434 over the compose network). Mirrors backend/Dockerfile's base.
FROM python:3.11-slim

WORKDIR /app

# Install pipeline deps first for layer caching.
COPY ml/matchup_intel/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# The package expects to import as `ml.matchup_intel.*` and to reuse
# ml/training_data/collect_data.py later, so copy the ml/ tree.
COPY ml/ /app/ml/

ENV PYTHONUNBUFFERED=1

# Default: run the pipeline once. In compose this is overridden to run a Prefect
# worker / scheduled deployment. `python -m` keeps the package import path intact.
CMD ["python", "-m", "ml.matchup_intel.flows"]
