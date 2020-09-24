#!/usr/bin/env python3
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
import json
import re
from html import escape
from smtplib import SMTP
from email.message import EmailMessage
from email import utils
import configuration as config

email_regex = r"\A[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"


class FormResponse:
    def __init__(self, code, message):
        self.code = code
        data = {
            'status': message
            }
        self.message = json.dumps(data)


class Mail:
    def __init__(self, data):
        self.message = EmailMessage()
        self.message['To'] = config.email_to
        self.message['From'] = config.email_sender
        self.message['Reply-To'] = data['email']
        self.message['Subject'] = f"Contact from {data['name']}"
        self.message['Date'] = utils.formatdate(localtime=True)
        self.message['Message-ID'] = utils.make_msgid()
        self.message.set_content(config.message_text
            .format_map({
            'name': data['name'],
            'message_content': escape(data['message'])
            }))

    def send(self):
        '''Sends an email'''
        smtp = SMTP(config.smtp_server, port=config.smtp_port)
        smtp.starttls()
        smtp.login(config.email_sender, config.email_password)
        smtp.send_message(self.message)
        smtp.close()


class ContactRequest(BaseHTTPRequestHandler):
    def _send_response(self, code, json_message='{}'):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json_message.encode("utf-8"))

    def do_POST(self):
        content_type = self.headers['content-type']
        post_body = self.rfile.read(int(self.headers['content-length'])).decode('utf-8')
        pared_body = body_to_object(content_type, post_body)
        res = handle_post(pared_body)
        self._send_response(res.code, res.message)


class ContactRequestWithIpLimiter(ContactRequest):
    ips = {}
    min_diff = timedelta(minutes=5)

    def clear_ips(self):
        for key, time in self.ips.copy().items():
            if datetime.today() - time < self.min_diff:
                continue
            del self.ips[key]

    def do_POST(self):
        self.clear_ips()
        ip = self.address_string()
        time: datetime = self.ips.get(ip)
        if time:
            return self._send_response(429, json.dumps({'message': 'Too many requests'}))
        else:
            self.ips[ip] = datetime.today()

        return super().do_POST()


def body_to_object(content_type: str, body):
    if 'application/json' in content_type:
        obj = json.loads(body)
        return obj
    elif 'application/x-www-form-urlencoded' in content_type:
        return {key: unquote(value) for key, value in [elem.split('=') for elem in body.split('&')]}
    else:
        return {}


def handle_post(data):
    if "name" not in data or "email" not in data or "message" not in data:
        return FormResponse(400, "Form Incomplete")
    if not re.search(email_regex, data['email']):
        return FormResponse(400, "Invalid Email")
    if not data['name'] or not data['email'] or not data['message']:
        return FormResponse(400, "Cannot send empty message")

    try:
        mail = Mail(data)
        mail.send()
        return FormResponse(200, "OK")
    except Exception as e:
        print(e)
        return FormResponse(400, "Could not send")


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
    server_address = ('', config.server_port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    if config.mode == 'default' or not config.mode:
        run(handler_class=ContactRequest)
    elif config.mode == 'ip':
        run(handler_class=ContactRequestWithIpLimiter)

