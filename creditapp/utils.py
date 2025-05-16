# utils.py
from django.core.mail import send_mail
from threading import Thread
from .models import EmailOTP
import re
from django.core.exceptions import ValidationError

def send_otp_email(email):
    otp = EmailOTP.generate_otp()
    EmailOTP.objects.create(email=email, otp=otp)

    def _send():
        send_mail(
            subject='Your OTP Verification Code',
            message=f'Your OTP is {otp}',
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            fail_silently=False,
        )

    Thread(target=_send).start()



def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain an uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain a lowercase letter.")
    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain a digit.")
    if not re.search(r'[!@#$%^&*]', password):
        raise ValidationError("Password must contain a special character (!@#$%^&*).")