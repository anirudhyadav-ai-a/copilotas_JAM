# copilotas_JAM — multi-stage production Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/wheels -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=builder /wheels /usr/local/lib/python3.12/site-packages
COPY . .
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
CMD ["python", "-m", "copilotas_JAM.examples.ci_cd_governance.webhook_handler.main"]
