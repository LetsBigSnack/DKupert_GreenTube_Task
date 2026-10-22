FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

# Pass explicit paths so the script never has to guess the Data/ location.
CMD ["sh", "-c", \
  "python process.py --stakes /app/Data/stakes_delivery.csv --promos /app/Data/promos.csv && \
   uvicorn api:app --host 0.0.0.0 --port 8000"]
