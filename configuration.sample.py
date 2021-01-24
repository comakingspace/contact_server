# start_tls or ssl
email_delivery = ""
email_sender = ""
email_password = ""
email_to = ""
smtp_server = ""
smtp_port = 587
server_port = 80

# Mode selects the modus the application starts in
# Possible Values would be 'default' or 'ip'
# where ip limit the mount of requests a single ip can make within a timeframe
mode = 'default'

# The ip source defines where the server takes the ip from
# default = address_string from python
# any other value defines the header where the ip could be found
ip_source = 'default'

# Allowed cors header domains
allowed_domains = ['.*']

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
