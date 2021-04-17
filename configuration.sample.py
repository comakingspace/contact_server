# start_tls or ssl
email_delivery = ""
# email address that sends the emails
email_sender = ""
# password for sending email
email_password = ""
# Target email
email_to = ""
smtp_server = ""
smtp_port = 587
server_port = 80

# IP Limiter time i.e. the time a single ip is stopped from resubmitting any data to the server
blocked_for_minutes = 5

# Mode selects the modus the application starts in
# Possible Values would be 'default' or 'ip'
# where ip limit the mount of requests a single ip can make within a timeframe
mode = 'default'

# The ip source defines where the server takes the ip from
# default = address_string from python
# any other value defines the header where the ip could be found
ip_source = 'default'

# If this field is filled then no email is sent
# If this field is not sent to the server no email is sent
# To disable set to none
spam_filter_field = 'filter'

# Allowed cors header domains
allowed_domains = ['.*']

# Fields that define content i.e. allowed fields in the form
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
