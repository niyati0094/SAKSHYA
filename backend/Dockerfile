# SAKSHYA backend image.
# NOTE: This image is the documented deployment target. It has NOT been built
# or executed in the prototype development environment, which has no Docker
# installed. Treat it as unverified until built.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
