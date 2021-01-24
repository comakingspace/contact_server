FROM python:3.9-alpine

WORKDIR /app

COPY contact_server.py .
COPY configuration.sample.py ./configuaration.py

CMD ["python", "-u", "contact_server.py"]
