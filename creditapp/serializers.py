from rest_framework import serializers
from  datetime import datetime
from datetime import timedelta
from .models import User, Customer, Transaction, PaymentReminder
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
import re

# ---------------------------- Signup Serializer ----------------------------
class SignupSerializer(serializers.ModelSerializer):
    mobile_number = serializers.CharField(required=True)  # Required mobile number
    email = serializers.EmailField(required=False)  # Email is optional
    # password = serializers.CharField(write_only=True, required=True)  # Password is required

    password = serializers.CharField(max_length=100, required=True, style={'input_type': 'password'}, write_only=True)
    # address = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile_number', 'email', 'password', 'address']

    def validate(self, attrs):
        errors = {}

        mobile_number = attrs.get('mobile_number', '')
        email = attrs.get('email', '')
        password = attrs.get('password', '')
        if User.objects.filter(mobile_number__iexact=mobile_number).exists():
            raise serializers.ValidationError('Mobile number already exists! Please try another one.')
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email already exists! Please try another one.')
        if "@gmail.com" not in email:
            raise serializers.ValidationError('Please enter a valid Gmail email address.')
        if len(password) < 8:  
            raise serializers.ValidationError({"password":"Password must be at least 8 characters long."})
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError({"password":"Password must contain at least one uppercase letter."})
        if not re.search(r'[a-z]', password):
            raise serializers.ValidationError({"password":"Password must contain at least one lowercase letter."})
        if not re.search(r'[0-9]', password):
            raise serializers.ValidationError({"password":"Password must contain at least one digit."})
        if not re.search(r'[!@#$%^&*]', password):
            raise serializers.ValidationError({"password":"Password must contain at least one special character: !@#$%^&*"})

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            mobile_number=validated_data['mobile_number'],
            email=validated_data.get('email', None),
            address=validated_data.get('address', None),
            is_verified=True,
            is_active=True,
            is_approved=True,
        )
        user.set_password(validated_data['password'])
        user.save()

        return user


# ---------------------------- Signin Serializer ----------------------------
class SigninSerializer(serializers.ModelSerializer):
    mobile_number = serializers.CharField(max_length=15, required=True)
    password = serializers.CharField(max_length=100, required=True, write_only=True, style={'input_type': 'password'})
    access_token = serializers.CharField(max_length=200, min_length=5, read_only=True)
    refresh_token = serializers.CharField(max_length=200, min_length=5, read_only=True)

    class Meta:
        model = User
        fields = ['mobile_number', 'password', 'access_token', 'refresh_token']
        read_only_fields = ['access_token', 'refresh_token']

    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number')
        password = attrs.get('password')

        try:
            user = User.objects.get(mobile_number__iexact=mobile_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid mobile number or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password.")

        token, _ = Token.objects.get_or_create(user=user)
        
        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'mobile_number': user.mobile_number,
            'email': user.email,
            'address': user.address,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh)
        }


# ---------------------------- Logout Serializer ----------------------------
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs.get("refresh_token")
        return attrs

    def save(self, **kwargs):
        try:
            # breakpoint()
            RefreshToken(self.token).blacklist()
            # request = self.context["request"]

            # auth_header = request.headers.get("Authorization", "")
            # if auth_header.startswith("Bearer "):
            #     token_str = auth_header.split(" ")[1]  # Extract token
            #     access_token = AccessToken(token_str)  # Convert to AccessToken
            #     access_deleted, _ = OutstandingToken.objects.filter(token=access_token).delete()
                
            #     if access_deleted:
            #         return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
            #     else:
            #         return Response({"message": "Token already expired or invalid"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            raise serializers.ValidationError("Invalid or expired token.")


# ---------------------------- Customer Serializer ----------------------------
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        exclude = ('created_at', 'updated_at')  # Excludes these fields
        

# ---------------------------- Transaction Serializer ----------------------------
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        exclude = ('created_at', 'updated_at')  # Excludes these fields

    def create(self, validated_data):
        transaction = super().create(validated_data)

        # customer.save()
        return transaction


# ---------------------------- Payment Reminder Serializer ----------------------------
class PaymentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReminder
        exclude = ('created_at', 'updated_at')  # Excludes these fields

