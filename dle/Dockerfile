FROM python:3.11-slim-bullseye as python-build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Include PSQL 14 so we can use pg_restore
# g++ for Pillow
RUN apt-get update --fix-missing \
    && apt-get install -y wget ca-certificates gnupg \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ bullseye-pgdg main" \
    > /etc/apt/sources.list.d/postgresql.list' \
    && apt-get update --fix-missing \
    && apt-get install -y nginx postgresql-14 \
    libpq-dev gcc g++ firefox-esr unzip curl \
    libxml2-dev libxslt1-dev

# Install geckodriver for Firefox Selenium
# Compatibility chart: https://firefox-source-docs.mozilla.org/testing/geckodriver/Support.html
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.32.2/geckodriver-v0.32.2-linux64.tar.gz | tar xz -C /usr/local/bin
RUN chmod +x /usr/bin/firefox
# set display port to avoid Selenium crash
ENV DISPLAY=:99

# Nginx setup 
RUN addgroup --system nginx
RUN adduser --system nginx
RUN usermod -a -G nginx nginx
RUN mkdir -p /run/nginx

RUN mkdir -p /var/log/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stdout /var/log/nginx/error.log
COPY nginx.conf /etc/nginx/nginx.conf

# Python requirements - requirements.dev shouldn't be needed
COPY requirements.txt /app
RUN pip install -r requirements.txt

# Setup
COPY . /app

EXPOSE 8000 5000
CMD /app/entrypoint