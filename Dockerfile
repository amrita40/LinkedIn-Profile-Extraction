FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# LI_AT / JSESSIONID / API_KEY are injected at runtime as env vars —
# never baked into the image. See README "Setup" and "Deployment".
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
