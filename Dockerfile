FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY client/ ./client/
COPY server/ ./server/
COPY gen/ ./gen/

CMD ["python", "-m",  "server.server"]
