from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
import logging
import smtplib
import ssl
from dotenv import load_dotenv
import os
logger = logging.getLogger(__name__)

load_dotenv()

import os
import smtplib
import ssl
from email.message import EmailMessage

# import os
# from django.conf import settings
# from django.http import JsonResponse
# from django.core.mail import EmailMessage, get_connection

class EmailService:
    def __init__(self):
        self.port = int(os.getenv('RESEND_SMTP_PORT', 587))
        self.smtp_server = os.getenv('RESEND_SMTP_HOST')
        self.username = os.getenv('RESEND_SMTP_USERNAME')
        self.password = os.getenv('RESEND_API_KEY')
        self.sender = os.getenv('FROM_EMAIL')

    def send_email(self, data):
        msg = EmailMessage()
        logger.info(f"Preparing to send email with data: {data}")

        msg['Subject'] = data.get('subject')
        msg['From'] = self.sender
        msg['To'] = data.get('recipient')

        if data.get('html_message'):
            msg.add_alternative(data.get('html_message'), subtype='html')

        for attachment in data.get('attachments', []):
            content = attachment.get('content')
            maintype = attachment.get('maintype', 'application')
            subtype = attachment.get('subtype', 'octet-stream')
            filename = attachment.get('filename')

            if isinstance(content, str):
                content = content.encode('utf-8')

            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

        try:
            if self.port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg)

            elif self.port == 587:
                with smtplib.SMTP(self.smtp_server, self.port) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(msg)

            else:
                raise ValueError('Use 465 or 587 as SMTP port')

            print(f"Email successfully sent to {data.get('recipient')}")

        except Exception as e:
            print(f"Error sending email: {e}")

    def send_submissions_csv_report(self, csv_text, filename='all_submissions.csv'):
        """Send a submissions CSV report to abdulmalikawesu@gmail.com."""
        data = {
            'subject': 'All Submissions CSV Report',
            'recipient': 'abdulmalikawesu@gmail.com',
            'html_message': (
                '<p>Please find the attached CSV report containing all form submissions, '
                'including form names, questions, answers, submission dates, and submission IDs.</p>'
            ),
            'attachments': [
                {
                    'filename': filename,
                    'content': csv_text,
                    'maintype': 'text',
                    'subtype': 'csv'
                }
            ]
        }

        self.send_email(data)

    def pilot_acknowledgment(self, instance):
        html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center;">
                    The first step in transforming your workforce
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    We acknowledge receipt of your request and sincerely appreciate your interest in working with us.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                        A member of our team is currently reviewing your information and will be in touch with you shortly.
                    </p>
                </div>

                <!-- About Section -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">About Our Approach</h3>
                    <p style="font-size: 15px; color: #333; line-height: 1.6;">
                        At Sereniq Global Limited, we focus on helping organizations unlock their full potential by leveraging data-driven insights. 
                        Our solutions are designed to provide clarity into workforce performance, enabling smarter decisions that drive sustainable growth.
                    </p>
                </div>

                <!-- Benefits Section -->
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; text-align: center;">What You Can Expect</h3>
                    <ul style="font-size: 15px; color: #333; line-height: 1.8; padding-left: 20px;">
                        <li><strong>Clear Performance Insights:</strong> Gain visibility into team productivity and performance trends.</li>
                        <li><strong>Better Decision-Making:</strong> Make informed, data-backed strategic choices.</li>
                        <li><strong>Improved Efficiency:</strong> Identify and eliminate operational bottlenecks.</li>
                        <li><strong>Employee Growth:</strong> Support development with targeted, actionable recommendations.</li>
                        <li><strong>Measurable Results:</strong> Track improvements with real, quantifiable outcomes.</li>
                    </ul>
                </div>

                <!-- Closing -->
                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 25px; line-height: 1.6;">
                    Should we require any additional information, we will reach out to you. We look forward to helping you build a more efficient and high-performing organization.
                </p>
                
                <p style="text-align: center; margin-top: 20px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>

            </div>
        </div>
        """

        data = {
            'subject': "The first step in transforming your workforce – Sereniq Global Limited",
            'recipient': instance.email,
            'html_message': html_message
        }

        self.send_email(data)

    def individual_booking_acknowledgment(self, instance):
        html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center;">
                    Your Individual Training Booking Confirmation
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    Thank you for booking our {instance.service.name}. We acknowledge receipt of your booking and appreciate your interest in our training services.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                        Our team is currently processing your booking and will be in touch with you shortly to confirm the details and schedule.
                    </p>
                </div>

                <!-- Booking Details -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">Booking Details</h3>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px;">
                        <p style="font-size: 15px; color: #333; line-height: 1.6;">
                            <strong>Service:</strong> {instance.service.name}<br>
                            <strong>Name:</strong> {instance.name}<br>
                            <strong>Email:</strong> {instance.email}<br>
                            <strong>Phone:</strong> {instance.phone}<br>
                            <strong>Subscription Type:</strong> {instance.subscription_type.title()}<br>
                            <strong>Status:</strong> {instance.status.title()}
                        </p>
                    </div>
                </div>

                <!-- About Section -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">About Our Training</h3>
                    <p style="font-size: 15px; color: #333; line-height: 1.6;">
                        At Sereniq Global Limited, we focus on helping individuals unlock their full potential by leveraging data-driven insights. 
                        Our training programs are designed to provide clarity into personal performance, enabling smarter decisions that drive sustainable growth.
                    </p>
                </div>

                <!-- Benefits Section -->
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; text-align: center;">What You Can Expect</h3>
                    <ul style="font-size: 15px; color: #333; line-height: 1.8; padding-left: 20px;">
                        <li><strong>Personal Performance Insights:</strong> Gain visibility into your productivity and performance trends.</li>
                        <li><strong>Better Decision-Making:</strong> Make informed, data-backed personal choices.</li>
                        <li><strong>Improved Efficiency:</strong> Identify and eliminate personal bottlenecks.</li>
                        <li><strong>Professional Growth:</strong> Support development with targeted, actionable recommendations.</li>
                        <li><strong>Measurable Results:</strong> Track improvements with real, quantifiable outcomes.</li>
                    </ul>
                </div>

                <!-- Closing -->
                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 25px; line-height: 1.6;">
                    Should we require any additional information, we will reach out to you. We look forward to helping you achieve your professional goals.
                </p>
                
                <p style="text-align: center; margin-top: 20px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>

            </div>
        </div>
        """

        data = {
            'subject': "Your Individual Training Booking Confirmation – Sereniq Global Limited",
            'recipient': instance.email,
            'html_message': html_message
        }

        self.send_email(data)

    def employee_booking_acknowledgment(self, instance):
        html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center;">
                    Your Employee Assessment Booking Confirmation
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    Thank you for booking our {instance.service.name}. We acknowledge receipt of your booking and appreciate your interest in our employee assessment services.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                        Our team is currently processing your booking and will be in touch with you shortly to confirm the details and schedule.
                    </p>
                </div>

                <!-- Booking Details -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">Booking Details</h3>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px;">
                        <p style="font-size: 15px; color: #333; line-height: 1.6;">
                            <strong>Service:</strong> {instance.service.name}<br>
                            <strong>Company:</strong> {instance.company_name}<br>
                            <strong>Contact Person:</strong> {instance.contact_person}<br>
                            <strong>Email:</strong> {instance.email}<br>
                            <strong>Number of Employees:</strong> {instance.number_of_employees}<br>
                            <strong>Duration:</strong> {instance.duration} minutes<br>
                            <strong>Subscription Type:</strong> {instance.subscription_type.title()}<br>
                            <strong>Status:</strong> {instance.status.title()}
                        </p>
                    </div>
                </div>

                <!-- About Section -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">About Our Employee Assessments</h3>
                    <p style="font-size: 15px; color: #333; line-height: 1.6;">
                        At Sereniq Global Limited, we focus on helping organizations unlock their full potential by leveraging data-driven insights into employee performance. 
                        Our assessments are designed to provide clarity into workforce performance, enabling smarter decisions that drive sustainable growth.
                    </p>
                </div>

                <!-- Benefits Section -->
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; text-align: center;">What You Can Expect</h3>
                    <ul style="font-size: 15px; color: #333; line-height: 1.8; padding-left: 20px;">
                        <li><strong>Employee Performance Insights:</strong> Gain visibility into team productivity and performance trends.</li>
                        <li><strong>Data-Driven Decisions:</strong> Make informed, data-backed strategic choices.</li>
                        <li><strong>Improved Efficiency:</strong> Identify and eliminate operational bottlenecks.</li>
                        <li><strong>Employee Development:</strong> Support growth with targeted, actionable recommendations.</li>
                        <li><strong>Measurable Results:</strong> Track improvements with real, quantifiable outcomes.</li>
                    </ul>
                </div>

                <!-- Closing -->
                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 25px; line-height: 1.6;">
                    Should we require any additional information, we will reach out to you. We look forward to helping you build a more efficient and high-performing organization.
                </p>
                
                <p style="text-align: center; margin-top: 20px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>

            </div>
        </div>
        """

        data = {
            'subject': "Your Employee Assessment Booking Confirmation – Sereniq Global Limited",
            'recipient': instance.email,
            'html_message': html_message
        }

        self.send_email(data)

    def workplace_governance_booking_acknowledgment(self, instance):
        html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center;">
                    Your Workplace Governance Assessment Booking Confirmation
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    Thank you for booking our {instance.service.name}. We acknowledge receipt of your booking and appreciate your interest in our workplace governance services.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                        Our team is currently processing your booking and will be in touch with you shortly to confirm the details and schedule.
                    </p>
                </div>

                <!-- Booking Details -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">Booking Details</h3>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px;">
                        <p style="font-size: 15px; color: #333; line-height: 1.6;">
                            <strong>Service:</strong> {instance.service.name}<br>
                            <strong>Company:</strong> {instance.company_name}<br>
                            <strong>Contact Person:</strong> {instance.contact_person}<br>
                            <strong>Email:</strong> {instance.email}<br>
                            <strong>Phone:</strong> {instance.phone_number}<br>
                            <strong>Number of Employees:</strong> {instance.number_of_employees}<br>
                            <strong>Subscription Type:</strong> {instance.subscription_type.title()}<br>
                            <strong>Status:</strong> {instance.status.title()}
                        </p>
                    </div>
                </div>

                <!-- About Section -->
                <div style="margin-top: 25px;">
                    <h3 style="color: #0b1f3a; text-align: center;">About Our Workplace Governance Services</h3>
                    <p style="font-size: 15px; color: #333; line-height: 1.6;">
                        At Sereniq Global Limited, we focus on helping organizations establish effective workplace governance through data-driven insights. 
                        Our solutions are designed to provide clarity into governance performance, enabling smarter decisions that drive sustainable organizational growth.
                    </p>
                </div>

                <!-- Benefits Section -->
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; text-align: center;">What You Can Expect</h3>
                    <ul style="font-size: 15px; color: #333; line-height: 1.8; padding-left: 20px;">
                        <li><strong>Governance Performance Insights:</strong> Gain visibility into governance effectiveness and compliance trends.</li>
                        <li><strong>Regulatory Compliance:</strong> Ensure your governance practices meet industry standards.</li>
                        <li><strong>Risk Management:</strong> Identify and mitigate governance-related risks.</li>
                        <li><strong>Stakeholder Alignment:</strong> Improve communication and alignment across your organization.</li>
                        <li><strong>Measurable Results:</strong> Track improvements with real, quantifiable outcomes.</li>
                    </ul>
                </div>

                <!-- Closing -->
                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 25px; line-height: 1.6;">
                    Should we require any additional information, we will reach out to you. We look forward to helping you establish effective workplace governance.
                </p>
                
                <p style="text-align: center; margin-top: 20px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>

            </div>
        </div>
        """

        data = {
            'subject': "Your Workplace Governance Assessment Booking Confirmation – Sereniq Global Limited",
            'recipient': instance.email,
            'html_message': html_message
        }

        self.send_email(data)

    def contact_form_acknowledgment(self, instance):
        html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center;">
                    We've Received Your Message
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    Thank you for contacting Sereniq Global Limited.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                        Your message has been successfully received. A member of our team will review your inquiry and respond within 24 hours.
                    </p>
                </div>

                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 25px; line-height: 1.6;">
                    We appreciate your interest and look forward to speaking with you.
                </p>
                
                <p style="text-align: center; margin-top: 20px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>

            </div>
        </div>
        """

        data = {
            "subject": "We've received your message – Sereniq Global Limited",
            "recipient": instance.email,
            "html_message": html_message
        }

        self.send_email(data)