# Use the official Python image from the Docker Hub
FROM python:3.11-slim
EXPOSE 8000

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install fastapi[standard]

COPY ./ .


CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]