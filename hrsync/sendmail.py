#! /usr/local/bin/python

import json
import sys

# this invokes the secure SMTP protocol (port 465, uses SSL)
from smtplib import SMTP_SSL as SMTP

# use this for standard SMTP protocol   (port 25, no encryption)
#from smtplib import SMTP

# old version
from email.mime.multipart import MIMEMultipart
# from email.MIMEText import MIMEText
from email.mime.text import MIMEText


def sendmail(config, destination, subject, content, json_str=None):
    SMTPserver = config.smtp_host
    sender = config.smtp_sender
    USERNAME = config.smtp_username
    PASSWORD = config.smtp_password

    # typical values for text_subtype are plain, html, xml
    text_subtype = 'plain'

    msg = MIMEMultipart()
    msg['Subject'] = subject
    # some SMTP servers will do this automatically, not all
    msg['From'] = sender
    body = MIMEText(content, 'plain')
    msg.attach(body)

    if json_str:
        attachment = MIMEText(json_str)
        attachment.add_header('Content-Disposition', 'attachment',
                            filename="pipedrive.json")
        msg.attach(attachment)

    conn = SMTP(SMTPserver)
    #conn.set_debuglevel(True)
    if USERNAME and PASSWORD:
        conn.login(USERNAME, PASSWORD)
    try:
        if "," in destination:
            destination = [d.strip() for d in destination.split(",")]
        conn.sendmail(sender, destination, msg.as_string())
    finally:
        conn.quit()


if __name__ == "__main__":
    from hrsync.config import Config
    args = sys.argv
    config = Config.from_file(args[1])
    destination, subject, content = sys.argv[2:]
    sendmail(config, destination, subject, content)
