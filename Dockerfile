ARG PYTHON_VERSION=3.11.3
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user 'appuser' with a home directory.
ARG UID=10001
RUN useradd --uid "${UID}" --create-home --home-dir /home/appuser --shell /bin/bash appuser

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Adjust permissions to allow 'appuser' to write to the /app directory
RUN chown -R appuser:appuser /app

USER appuser

COPY . .

EXPOSE 8000

CMD ["python", "./app.py"]
