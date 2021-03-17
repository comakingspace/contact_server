#!/usr/bin/env python3
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import unquote_plus, parse_qs, urlencode, urlparse
import json
import re
from html import escape
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage
from email import utils

import configuration as config

email_regex = r"\A[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?"


class FormResponse:
    def __init__(self, code, message):
        self.code = code
        data = {
            'status': message
            }
        self.message = json.dumps(data)

    def is_valid(self):
        return 400 > self.code >= 200


class Mail:
    def __init__(self, data):
        self.message = EmailMessage()
        self.message['To'] = config.email_to
        self.message['From'] = config.email_sender
        self.message['Reply-To'] = data.get('email')
        self.message['Subject'] = data.get('subject', f"Contact from {data['name']}").format_map(data)
        self.message['Date'] = utils.formatdate(localtime=True)
        self.message['Message-ID'] = utils.make_msgid()

        content = "\n\n".join([f"{name}: \n{escape(data.get(key))}" for key, name in config.fields.items() if key in data])

        self.message.set_content(config.message_text.format_map({
            'content': content,
            **data
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
    response_headers = dict()

    def set_header(self, key, value):
        self.response_headers[key] = value

    def complete_response(self, code: int, message: Optional[str] = None):
        self.send_response(code, message)
        for key, value in self.response_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.response_headers.clear()

    def redirect_to(self, response: FormResponse):
        origin = self.headers.get('Origin')
        if not origin:
            return False

        query = parse_qs(urlparse(self.path).query)

        success_path, = query.get('success', [None])
        failure_path, = query.get('failure', [None])

        if not success_path or not failure_path:
            print('RedirectTo: Either success or failure are undefined')
            return False

        if response.is_valid():
            self.set_header('Location', f"{origin}{success_path}")
        else:
            self.set_header('Location', f"{origin}{failure_path}?{urlencode({'reason': response.message})}")

        self.complete_response(303)
        return True

    def _send_response(self, response: FormResponse):
        if not self.redirect_to(response):
            self.set_header('Content-type', 'application/json')
            self.set_header('Content-type', 'application/json')
            self.complete_response(response.code, response.message)
            self.wfile.write(response.message.encode("utf-8"))

    def _check_origin(self, conf=config):
        origin = self.headers.get('Origin', 'Unknown')
        isAllowed = True in [bool(re.search(pattern, origin)) for pattern in conf.allowed_domains]
        if isAllowed:
            self.set_header('Access-Control-Allow-Origin', '*')

        return isAllowed

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
        try:
            if 'application/json' in content_type:
                obj = json.loads(body)
                return obj
            elif 'application/x-www-form-urlencoded' in content_type:
                return {key: unquote_plus(value) for key, value in [elem.split('=') for elem in body.split('&')]}
            else:
                return {}
        except Exception as e:
            print(e)
            return {}

    def do_OPTIONS(self):
        self._check_origin()
        self.set_header('Access-Control-Request-Method', 'POST')
        self.set_header('Access-Control-Max-Age', '86400')
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.complete_response(200)

    def do_POST(self):
        content_type = self.headers.get('content-type')
        post_body = self.rfile.read(int(self.headers.get('content-length'))).decode('utf-8')
        parsed_body = self._body_to_object(content_type, post_body)
        if self._check_origin():
            res = self._handle_post(parsed_body)
        else:
            res = FormResponse(400, "Origin Check Failed")
        self._send_response(res)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Healthy')


class ContactRequestWithIpLimiter(ContactRequest):
    ips = {}
    min_diff = timedelta(minutes=config.blocked_for_minutes)

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
            return self._send_response(FormResponse(429, 'Too many requests'))
        else:
            self.ips[ip] = datetime.today()

        return super().do_POST()


def run(server_class=ThreadingHTTPServer, handler_class=BaseHTTPRequestHandler):
    server_address = ('', config.server_port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    if config.mode == 'default' or not config.mode:
        run(handler_class=ContactRequest)
    elif config.mode == 'ip':
        run(handler_class=ContactRequestWithIpLimiter)
