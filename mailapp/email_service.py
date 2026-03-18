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
