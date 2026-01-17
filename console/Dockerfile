FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 vesla && \
    chown -R vesla:vesla /app

USER vesla

EXPOSE 5003

CMD ["gunicorn", "--bind", "0.0.0.0:5003", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
