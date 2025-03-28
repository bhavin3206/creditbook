from rest_framework import serializers
from  datetime import datetime
from datetime import timedelta
from .models import User, Customer, Transaction, PaymentReminder
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
import re
from datetime import date
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

# ---------------------------- User Edit Serializer ----------------------------
class UserSerializer(serializers.ModelSerializer):
    mobile_number = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'email', 'address', 'category', 'first_name', 'last_name', 
            'mobile_number', 'profile_picture'
        ]

        read_only_fields = ['password', 'is_approved', 'is_verified', 'is_active', 'is_owner', 'is_staff']

    


# ---------------------------- Customer Serializer ----------------------------
class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = ['id','name', 'contact_number', 'email', 'address', 'account_balance', 'created_at', 'updated_at']  # Define the fields you want to allow
        extra_kwargs = {
            "email": {"required": False},
            "address": {"required": False},
        }

    def validate(self, attrs):
        """
        Ensure that the customer being created or updated belongs to the authenticated user.
        """
        request_user = self.context['request'].user

        # If updating an existing customer, ensure they belong to the user
        if self.instance and self.instance.user != request_user:
            raise serializers.ValidationError("Not Found.")

        # If creating a new customer, ensure they belong to the user
        if 'user' in attrs and attrs['user'] != request_user:
            raise serializers.ValidationError("Not Found.")

        return attrs

# ---------------------------- Transaction Serializer ----------------------------
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        # exclude = ('updated_at',)  # Excludes these fields

    def create(self, validated_data):
        """
        Add ownership validation for creating a transaction.
        Ensure that the transaction is linked to a customer that belongs to the authenticated user.
        """
        customer = validated_data.get('customer')
        user = self.context['request'].user
        
        if customer.user != user:  # Ensure the customer belongs to the authenticated user
            raise serializers.ValidationError("You cannot create a transaction for another user's customer.")
        
        transaction = super().create(validated_data)  # Save the transaction
        return transaction

    def validate(self, attrs):
        """
        Add ownership validation for updating an existing transaction.
        Ensures that the transaction's customer belongs to the authenticated user.
        """
        if 'customer' in attrs:
            customer = attrs['customer']
            user = self.context['request'].user
            if customer.user != user:  # Ensure the customer belongs to the authenticated user
                raise serializers.ValidationError("Not Found.")
        return attrs


# ---------------------------- Payment Reminder Serializer ----------------------------
class PaymentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReminder
        exclude = ('updated_at',)  # Excludes these fields
        extra_kwargs = {
            "status": {"required": False},  
            "customer": {"required": False, "allow_null": True},  
            "transaction": {"required": False, "allow_null": True}  
        }

    def validate(self, attrs):
        """
        Ensure at least one of customer or transaction is provided.
        Validate that the transaction belongs to the given customer if both are provided.
        Validate that the customer/transaction belongs to the authenticated user.
        """
        request_user = self.context['request'].user
        customer = attrs.get("customer")
        transaction = attrs.get("transaction")
        reminder_date = attrs.get("reminder_date")

        # Ensure at least one is provided
        if not customer and not transaction:
            raise serializers.ValidationError("Either 'customer' or 'transaction' must be provided.")

        # Ensure customer belongs to authenticated user
        if customer and customer.user != request_user:
            raise serializers.ValidationError("Customer Not Found.")

        # Ensure transaction belongs to authenticated user
        if transaction and transaction.customer.user != request_user:
            raise serializers.ValidationError("Transaction Not Found.")
        
        # Ensure the transaction belongs to the given customer if both are provided
        if transaction and customer and transaction.customer != customer:
            raise serializers.ValidationError("The transaction must belong to the given customer.")

        if reminder_date and reminder_date == date.today():
            raise serializers.ValidationError("Reminder date cannot be today.")

        return attrs
