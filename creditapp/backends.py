import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

class EmailOrMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        print(f"[DEBUG] Trying to authenticate with username: {username}")
        logger.debug(f"Trying to authenticate with username: {username}")
        
        if not username:
            return None

        try:
            user = User.objects.get(email=username)
            print(f"[DEBUG] Found user by email: {user}")
        except User.DoesNotExist:
            try:
                user = User.objects.get(mobile_number=username)
                print(f"[DEBUG] Found user by mobile number: {user}")
            except User.DoesNotExist:
                print("[DEBUG] No user found with email or mobile")
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            print("[DEBUG] Authentication successful")
            return user
        print("[DEBUG] Password check failed or user not active")
        return None
