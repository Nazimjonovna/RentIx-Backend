FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

RUN addgroup --system app && adduser --system --ingroup app appuser \
    && chown -R appuser:app /app

USER appuser

EXPOSE 8000

#CMD ["gunicorn", "RentIx.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
CMD python3 manage.py makemigrations && python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8000
