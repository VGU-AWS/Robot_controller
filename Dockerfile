FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ARG DB_HOST
ARG DB_NAME
ARG DB_USER
ARG DB_PASSWORD
ARG DB_URL
ARG APP_PORT=8080

ENV DB_HOST=${DB_HOST} \
    DB_NAME=${DB_NAME} \
    DB_USER=${DB_USER} \
    DB_PASSWORD=${DB_PASSWORD} \
    DB_URL=${DB_URL} \
    APP_PORT=${APP_PORT} \
    PORT=${APP_PORT}

EXPOSE ${APP_PORT}

ENTRYPOINT ["python","app.py"]
