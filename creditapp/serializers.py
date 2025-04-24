from rest_framework import serializers
from datetime import  date
from .models import User, Customer, Transaction, PaymentReminder
import re

# ---------------------------- Signup Serializer ----------------------------
class SignupSerializer(serializers.ModelSerializer):
    mobile_number = serializers.CharField(required=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(max_length=100, required=True, style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile_number', 'email', 'password', 'address']

    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number', '')
        email = attrs.get('email', '')
        password = attrs.get('password', '')
        
        if User.objects.filter(mobile_number__iexact=mobile_number).exists():
            raise serializers.ValidationError('Mobile number already exists! Please try another one.')
        
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email already exists! Please try another one.')
        
        if email and "@gmail.com" not in email:
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
    category = serializers.CharField(required=False)

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
        fields = ['id', 'name', 'contact_number', 'email', 'address', 'account_balance', 'created_at', 'updated_at']
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

# ---------------------------- Simple Customer Serializer ----------------------------
# For optimized nested relationships
class SimpleCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'account_balance']

# ---------------------------- Transaction Serializer ----------------------------
class TransactionSerializer(serializers.ModelSerializer):
    # Optimize nested serialization by using a minimal customer representation
    customer_details = SimpleCustomerSerializer(source='customer', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'customer', 'customer_details', 'amount', 'transaction_type', 
            'payment_mode', 'date', 'description', 'bill_image', 'created_at'
        ]
    
    def create(self, validated_data):
        """
        Add ownership validation for creating a transaction.
        Ensure that the transaction is linked to a customer that belongs to the authenticated user.
        """
        customer = validated_data.get('customer')
        user = self.context['request'].user
        
        if customer.user != user:  # Ensure the customer belongs to the authenticated user
            raise serializers.ValidationError("You cannot create a transaction for another user's customer.")
        
        transaction = super().create(validated_data)
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

# ---------------------------- Simple Transaction Serializer ----------------------------
# For optimized nested relationships
class SimpleTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'transaction_type', 'date']

# ---------------------------- Payment Reminder Serializer ----------------------------
class PaymentReminderSerializer(serializers.ModelSerializer):
    # Optimize nested serialization
    customer_details = SimpleCustomerSerializer(source='customer', read_only=True)
    transaction_details = SimpleTransactionSerializer(source='transaction', read_only=True)
    
    class Meta:
        model = PaymentReminder
        fields = [
            'id', 'customer', 'customer_details', 'transaction', 'transaction_details',
            'amount_due', 'reminder_date', 'status', 'created_at'
        ]
        extra_kwargs = {
            "status": {"required": False},  
            "customer": {"required": False, "allow_null": True, "write_only": True},  
            "transaction": {"required": False, "allow_null": True, "write_only": True}  
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