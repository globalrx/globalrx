FROM python:3.10.10-slim-buster as python-build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update --fix-missing
RUN apt-get install -y nginx python-psycopg2 postgresql libpq-dev gcc g++

# TODO Chrome setup for Selenium

# Nginx setup 
RUN addgroup --system nginx
RUN adduser --system nginx
RUN usermod -a -G nginx nginx
RUN mkdir -p /run/nginx

RUN mkdir -p /var/log/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stdout /var/log/nginx/error.log
COPY nginx.conf /etc/nginx/nginx.conf

# Python requirements
COPY requirements.txt /app
RUN pip install -r requirements.txt

# Setup
COPY . /app

EXPOSE 8000 5000
CMD /app/entrypoint