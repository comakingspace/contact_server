#!/usr/bin/env python3
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
#         message_text = f"""
# Hello Space,
#
# a new contact message from {data['name']} has been received:
#
# -------------------------------------------------------
# {escape(data['message'])}
# -------------------------------------------------------
#
# Yours Truly,
# Contact Fomular on the Website
#         """
        self.message.set_content(config.message_text
            .format_map({
            'name'           : data['name'],
            'message_content': escape(data['message'])
            }))

    def send(self):
        '''Sends an email'''
        # sys.stdout.buffer.write(self.message.as_bytes())
        smtp = SMTP(config.smtp_server, port=config.smtp_port)
        smtp.starttls()
        smtp.login(config.email_sender, config.email_password)
        smtp.send_message(self.message)
        smtp.close()


class PostRequest(BaseHTTPRequestHandler):
    def _send_response(self, code, json_message='{}'):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json_message.encode("utf-8"))

    def do_POST(self):
        post_body = self.rfile.read(int(self.headers['content-length'])).decode('utf-8')
        res = handle_post({ key: unquote(value) for key, value in [elem.split('=') for elem in post_body.split('&')] })
        self._send_response(res.code, res.message)


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
    run(handler_class=PostRequest)
