email_sender = ""
email_password = ""
email_to = ""
smtp_server = ""
smtp_port = 587
server_port = 80
mode = 'default'
allowed_domains = ['.*']
ip_source = 'default'
fields = {
    'message': 'Message',
    }

message_text = """
Hello Space,

a new contact message from {name} has been received:

-------------------------------------------------------
{message}
-------------------------------------------------------

Yours Truly,
Contact Fomular on the Website
"""
