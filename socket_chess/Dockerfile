FROM python:3.12.6

RUN apt-get update && apt-get install -y redis-server supervisor && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN chmod +x docker_run_server.sh

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

ENTRYPOINT [ "./docker_run_server.sh" ]