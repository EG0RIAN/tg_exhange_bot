FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
COPY ./locales ./locales
COPY ./migrations ./migrations

CMD ["python", "-m", "src"] 