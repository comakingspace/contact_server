#!/usr/bin/env python3
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import unquote_plus
import json
import re
from html import escape
from smtplib import SMTP, SMTP_SSL
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
        self.message['Subject'] = data.get('subject') or f"Contact from {data['name']}"
        self.message['Date'] = utils.formatdate(localtime=True)
        self.message['Message-ID'] = utils.make_msgid()

        content = "\n\n".join([f"{name}: \n{escape(data.get(key))}" for key, name in config.fields.items()])

        self.message.set_content(config.message_text
            .format_map({
            'name': data['name'],
            'content': content
            }))

    def _send_start_tls(self):
        smtp = SMTP(config.smtp_server, port=config.smtp_port)
        smtp.starttls()
        smtp.login(config.email_sender, config.email_password)
        smtp.send_message(self.message)
        smtp.close()

    def _send_ssl(self):
        smtp = SMTP_SSL(config.smtp_server, port=config.smtp_port)
        smtp.login(config.email_sender, config.email_password)
        smtp.send_message(self.message)
        smtp.close()

    def send(self):
        '''Sends an email'''
        if config.email_delivery == 'ssl':
            self._send_ssl()
        else:
            self._send_start_tls()



class ContactRequest(BaseHTTPRequestHandler):
    def _send_response(self, code, json_message='{}'):
        self.send_response(code)
        self._check_origin()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json_message.encode("utf-8"))

    def _check_origin(self, conf=config):
        origin = self.headers['Origin'] or 'Unknown'
        isAllowed = True in [bool(re.search(pattern, origin)) for pattern in conf.allowed_domains]
        if isAllowed:
            self.send_header('Access-Control-Allow-Origin', '*')

    def _handle_post(self, data):
        has_content = True in [field in data for field in config.fields]
        if not data.get('name') or not data.get('email') or not has_content:
            return FormResponse(400, "Cannot send empty message")

        if not re.search(email_regex, data.get('email')):
            return FormResponse(400, "Invalid Email")

        try:
            mail = Mail(data)
            mail.send()
            return FormResponse(200, "OK")
        except Exception as e:
            print(e)
            return FormResponse(400, "Could not send")

    def _body_to_object(self, content_type: str, body):
        if 'application/json' in content_type:
            obj = json.loads(body)
            return obj
        elif 'application/x-www-form-urlencoded' in content_type:
            return {key: unquote_plus(value) for key, value in [elem.split('=') for elem in body.split('&')]}
        else:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self._check_origin()
        self.send_header('Access-Control-Request-Method', 'POST')
        self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_type = self.headers['content-type']
        post_body = self.rfile.read(int(self.headers['content-length'])).decode('utf-8')
        parsed_body = self._body_to_object(content_type, post_body)
        res = self._handle_post(parsed_body)
        self._send_response(res.code, res.message)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Healthy')


class ContactRequestWithIpLimiter(ContactRequest):
    ips = {}
    min_diff = timedelta(minutes=5)

    def clear_ips(self):
        for key, time in self.ips.copy().items():
            if datetime.today() - time < self.min_diff:
                continue
            del self.ips[key]

    def get_ip(self, conf=config):
        source = conf.ip_source
        if source == 'default' or not source:
            return self.address_string()
        else:
            return self.headers[source]

    def do_POST(self):
        self.clear_ips()
        ip = self.get_ip()
        time: datetime = self.ips.get(ip)
        if time:
            return self._send_response(429, json.dumps({'message': 'Too many requests'}))
        else:
            self.ips[ip] = datetime.today()

        return super().do_POST()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Handle requests in a separate thread.
    Ref: https://pymotw.com/2/BaseHTTPServer/index.html#threading-and-forking
    """


def run(server_class=ThreadedHTTPServer, handler_class=BaseHTTPRequestHandler):
    server_address = ('', config.server_port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    if config.mode == 'default' or not config.mode:
        run(handler_class=ContactRequest)
    elif config.mode == 'ip':
        run(handler_class=ContactRequestWithIpLimiter)
