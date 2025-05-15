# utils.py
from django.core.mail import send_mail
from threading import Thread
from .models import EmailOTP

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
