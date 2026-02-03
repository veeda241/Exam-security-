FROM python:3.9-slim

WORKDIR /app

COPY ./server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 tesseract-ocr

COPY ./server /app/server
COPY ./frontend /app/frontend

WORKDIR /app/server

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
