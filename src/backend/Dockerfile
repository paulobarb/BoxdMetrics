FROM python:3.12-slim

WORKDIR /app

RUN useradd -m appuser

COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]