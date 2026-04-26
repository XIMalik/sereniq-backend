# import ssl

# from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
# from django.utils.functional import cached_property

# class EmailBackend(SMTPBackend):
#     @cached_property
#     def ssl_context(self):
#         if self.ssl_certfile or self.ssl_keyfile:
#             ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
#             ssl_context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
#             return ssl_context
#         else:
#             ssl_context = ssl.create_default_context()
#             ssl_context.check_hostname = False
#             ssl_context.verify_mode = ssl.CERT_NONE
#             return ssl_context
        

import ssl
import certifi
import smtplib

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


class EmailBackend(SMTPBackend):
    def open(self):
        if self.connection:
            return False

        connection_params = {
            'host': self.host,
            'port': self.port,
            'timeout': self.timeout,
        }

        try:
            self.connection = smtplib.SMTP(**connection_params)
            self.connection.ehlo()

            if self.use_tls:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                self.connection.starttls(context=ssl_context)
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True

        except Exception:
            if not self.fail_silently:
                raise


import smtplib, ssl
from email.message import EmailMessage

def send_test_email():
    port = 587
    smtp_server = "smtp.zeptomail.com"
    username="emailapikey"
    password = "wSsVR611qUOiD/h4zTP4IOxpnQ4EDw/xE015ilSouif5HvvL/Mc5wUbKVAXxGfVKFWJoRWMa9rIvmhsD0TRb2Yl5y1ACWSiF9mqRe1U4J3x17qnvhDzMWGpYkhCMK44PwgxqnmJpEoU="
    message = "Test email sent successfully."
    msg = EmailMessage()
    msg['Subject'] = "Test Email"
    msg['From'] = "noreply@sereniqglobal.com"
    msg['To'] = "abdulmalikawesu@gmail.com"
    msg.set_content(message)
    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(username, password)
                server.send_message(msg)
        elif port == 587:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
        else:
            print ("use 465 / 587 as port value")
            exit()
        print ("successfully sent")
    except Exception as e:
        print (e)