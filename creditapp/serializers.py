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

