FROM python:3.12.0
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install -r requirements.txt
COPY . ./
RUN chmod +x docker_run_server.sh
EXPOSE 80
ENTRYPOINT [ "./docker_run_server.sh" ]