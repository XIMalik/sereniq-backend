from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_welcome_email(user):
        logger.info(f"Attempting to send welcome email to {user.email}")
        
        subject = 'Welcome to Sereniq!'
        html_message = f"""
            <div style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto; border: 1px solid #dee2e6;">
                <h2 style="color: #0d6efd; text-align: center;">Welcome to <span style="color: #0a58ca;">Sereniq</span>, {user.name}!</h2>
                
                <p style="font-size: 16px; color: #444; text-align: center;">
                    Thank you for joining Sereniq! We're excited to have you on board.
                </p>
                
                <div style="background-color: #e7f1ff; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <p style="font-size: 15px; color: #555; text-align: center;">
                        ✨ Start creating <strong>dynamic forms</strong>, collecting <strong>responses</strong>, and managing <strong>service bookings</strong> with ease.
                    </p>
                </div>
                
                <div style="background-color: #fff; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #0d6efd;">
                    <h3 style="color: #0a58ca; margin-top: 0;">Your Account Details:</h3>
                    <p style="margin: 5px 0; color: #444;"><strong>Email:</strong> {user.email}</p>
                    <p style="margin: 5px 0; color: #444;"><strong>Role:</strong> {user.get_role_display()}</p>
                </div>
                
                <p style="font-size: 15px; color: #444; text-align: center; margin-top: 20px;">
                    Get started by logging in and exploring all the features Sereniq has to offer. 🚀
                </p>
                
                <p style="text-align: center; font-size: 15px; color: #555; margin-top: 20px;">
                    Best regards,<br>
                    <strong style="color: #0d6efd;">The Sereniq Team</strong>
                </p>
            </div>
            """

        plain_message = strip_tags(html_message)
        
        try:
            logger.info(f"Email settings - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}")
            logger.info(f"From email: {settings.EMAIL_HOST_USER}")
            logger.info(f"To email: {user.email}")
            
            result = send_mail(
                subject,
                plain_message,
                settings.EMAIL_HOST_USER,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Welcome email sent successfully to {user.email}. Result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            raise e

def send_acknowledgement_email(pilot):
    logger.info(f"Attempting to send acknowledgement email to {pilot.email}")
    
    subject = 'What to expect from your Pilot Session – Sereniq Global Limited'
    html_message = f"""
        <div style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 30px;">
            <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #dcdfe3;">
                
                <h2 style="color: #0b1f3a; text-align: center; font-weight: 600; margin-bottom: 10px;">
                    Thank you for your submission
                </h2>
                
                <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
                    We acknowledge receipt of your request and appreciate your interest in working with us.
                </p>
                
                <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
                    <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0; line-height: 1.6;">
                        A member of our team is currently reviewing your information and will reach out to you shortly to continue the discussion.
                    </p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; margin-top: 0; font-size: 18px; text-align: center;">About Sereniq</h3>
                    <p style="font-size: 15px; color: #333; line-height: 1.6; margin-bottom: 15px;">
                        Sereniq is a leading business consulting firm dedicated to enhancing day-to-day business operations through data-driven insights. We specialize in collecting and analyzing staff performance submissions to identify key areas for improvement.
                    </p>
                    <p style="font-size: 15px; color: #333; line-height: 1.6;">
                        By leveraging advanced analytics, we transform raw performance data into actionable recommendations that drive operational efficiency, boost employee engagement, and ultimately improve your company's bottom line.
                    </p>
                </div>
                
                <div style="background-color: #e7f1ff; padding: 20px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #0b1f3a; margin-top: 0; font-size: 18px; text-align: center;">Benefits of Our Services</h3>
                    <ul style="font-size: 15px; color: #333; line-height: 1.8; padding-left: 20px;">
                        <li><strong>Enhanced Performance:</strong> Identify strengths and weaknesses across your workforce to optimize productivity.</li>
                        <li><strong>Data-Driven Decisions:</strong> Make informed choices backed by comprehensive performance analytics.</li>
                        <li><strong>Operational Improvements:</strong> Receive tailored recommendations to streamline processes and reduce inefficiencies.</li>
                        <li><strong>Employee Development:</strong> Foster a culture of continuous improvement with targeted training and support.</li>
                        <li><strong>Measurable Results:</strong> Track progress with clear metrics and see tangible improvements in your business operations.</li>
                    </ul>
                </div>
                
                <div style="background-color: #ffffff; padding: 15px; border-radius: 6px; margin-top: 20px; border-left: 3px solid #b8962e;">
                    <h3 style="color: #0b1f3a; margin-top: 0; font-size: 16px;">Submission Details</h3>
                    <p style="margin: 5px 0; color: #333;"><strong>Email:</strong> {pilot.email}</p>
                </div>
                
                <p style="font-size: 14px; color: #444; text-align: center; margin-top: 20px; line-height: 1.6;">
                    Should we require any additional information, we will be in touch.
                </p>
                
                <p style="text-align: center; font-size: 14px; color: #555; margin-top: 25px;">
                    Kind regards,<br>
                    <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
                </p>
                
            </div>
        </div>
        """

    plain_message = strip_tags(html_message)
    
    try:
        logger.info(f"Email settings - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}")
        logger.info(f"From email: {settings.EMAIL_HOST_USER}")
        logger.info(f"To email: {pilot.email}")
        
        result = send_mail(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [pilot.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Acknowledgement email sent successfully to {pilot.email}. Result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to send acknowledgement email to {pilot.email}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise e
    


import smtplib
import ssl
from email.message import EmailMessage

def send_ack_email(instance):
    port = 587
    smtp_server = "smtp.zeptomail.com"
    username="emailapikey"
    password = "wSsVR611qUOiD/h4zTP4IOxpnQ4EDw/xE015ilSouif5HvvL/Mc5wUbKVAXxGfVKFWJoRWMa9rIvmhsD0TRb2Yl5y1ACWSiF9mqRe1U4J3x17qnvhDzMWGpYkhCMK44PwgxqnmJpEoU="

    message = "Thank you for your submission. A member of our team will contact you shortly."

    msg = EmailMessage()
    msg['Subject'] = "The first step in transforming your workforce – Sereniq Global Limited"
    msg['From'] = "noreply@sereniqglobal.com"
    msg['To'] = instance.email

    # Plain text
    msg.set_content(message)

    # HTML message
    html_message = f"""
    <div style="font-family: Arial, sans-serif; background-color: #f4f6f9;">
    <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #dcdfe3;">
        
        <h2 style="color: #0b1f3a; text-align: center;">
            The first step in transforming your workforce
        </h2>
        
        <p style="font-size: 15px; color: #333; text-align: center; line-height: 1.6;">
            We acknowledge receipt of your request and sincerely appreciate your interest in working with us.
        </p>
        
        <div style="background-color: #0b1f3a; padding: 18px; border-radius: 6px; margin-top: 20px;">
            <p style="font-size: 14px; color: #e6d3a3; text-align: center; margin: 0;">
                A member of our team is currently reviewing your information and will be in touch with you shortly to continue the conversation.
            </p>
        </div>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin-top: 20px;">
            <h3 style="color: #0b1f3a; text-align: center;">About Sereniq</h3>
            
            <p style="font-size: 15px; color: #333; line-height: 1.6; margin-bottom: 15px;">
                Sereniq is a forward-thinking business consulting firm dedicated to helping organizations improve their day-to-day operations through the power of data. We work closely with businesses to understand their unique challenges and uncover opportunities for growth, efficiency, and long-term success.
            </p>
            
            <p style="font-size: 15px; color: #333; line-height: 1.6;">
                By collecting and analyzing staff performance data, we provide actionable insights that enable better decision-making, enhance productivity, and strengthen overall organizational performance. Our goal is to transform complex data into clear, practical strategies that deliver measurable results.
            </p>
        </div>
        
        <div style="background-color: #e7f1ff; padding: 20px; border-radius: 6px; margin-top: 20px;">
            <h3 style="color: #0b1f3a; text-align: center;">Benefits</h3>
            <ul style="font-size: 15px; color: #333; line-height: 1.8;">
                <li><strong>Enhanced Performance:</strong> Identify strengths and areas for improvement across your workforce.</li>
                <li><strong>Data-Driven Decisions:</strong> Make informed choices backed by reliable insights.</li>
                <li><strong>Operational Efficiency:</strong> Streamline processes and reduce inefficiencies.</li>
                <li><strong>Employee Development:</strong> Support continuous growth with targeted recommendations.</li>
                <li><strong>Measurable Results:</strong> Track progress and see tangible business improvements.</li>
            </ul>
        </div>
                
        <p style="font-size: 14px; color: #444; text-align: center; margin-top: 20px; line-height: 1.6;">
            Should we require any additional information, we will reach out to you.
        </p>
        
        <p style="text-align: center; margin-top: 20px;">
            Kind regards,<br>
            <strong style="color: #0b1f3a;">Sereniq Global Limited</strong>
        </p>
        
    </div>
</div>
    """

    msg.add_alternative(html_message, subtype="html")

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