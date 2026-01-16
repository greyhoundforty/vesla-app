FROM python:3.11-slim

WORKDIR /app

# No need to install Docker - we'll mount the binary from host
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5002

CMD ["python", "app.py"]
