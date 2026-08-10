FROM python:3.12-slim

# Keep Python output unbuffered and skip .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Bring in example configs and sample data.
COPY configs ./configs
COPY data/sample ./data/sample

# Drop root: the pipeline only reads its config and writes its own output, so
# nothing here needs privileges. A container escape then lands on an unprivileged
# account rather than root on the host.
RUN useradd --create-home --uid 10001 edp \
    && chown -R edp:edp /app
USER edp

ENTRYPOINT ["edp"]
CMD ["run", "--config", "configs/pipeline.example.yaml"]
