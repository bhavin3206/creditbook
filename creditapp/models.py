from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.files.storage import default_storage
import os
import uuid
from django.db.models.signals import  post_delete
from django.dispatch import receiver
from django.db.models import F, Sum, Case, When, DecimalField
from django.utils.functional import cached_property

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email=None, mobile_number=None, password=None, **extra_fields):
        if not email and not mobile_number:
            raise ValueError("User must have a mobile number or email")
        
        user = self.model(
            email=email,
            mobile_number=mobile_number,
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, password, email=None, mobile_number=None):
        if not password:
            raise ValueError("Superuser must have a password")
                
        user = self.create_user(email=email, mobile_number=mobile_number, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.is_verified = True
        user.is_approved = True
        user.save(using=self._db)
        return user

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True, db_index=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=50, default="Other")  # CharField for category
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", default="default_profile/avatar_blank.jpg")
    
    is_approved = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_owner = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'mobile_number'
    objects = UserManager()

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''} ({self.mobile_number or self.email})"

    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['mobile_number']),
        ]

# Function to generate unique filename for uploaded images
def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"bill_{uuid.uuid4()}.{ext}"
    return os.path.join('uploads/', filename)

# Customer Model
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=255, db_index=True)
    contact_number = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField()
    account_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @cached_property
    def total_credit(self):
        return self.transactions.filter(transaction_type='credit').aggregate(total=Sum('amount'))['total'] or 0

    @cached_property
    def total_debit(self):
        return self.transactions.filter(transaction_type='debit').aggregate(total=Sum('amount'))['total'] or 0

    @cached_property
    def current_balance(self):
        # Using annotate for more efficient calculation
        balance = self.transactions.aggregate(
            balance=Sum(
                Case(
                    When(transaction_type='credit', then=F('amount')),
                    When(transaction_type='debit', then=-F('amount')),
                    default=0,
                    output_field=DecimalField()
                )
            )
        )['balance'] or 0
        return balance

    def update_account_balance(self):
        self.account_balance = self.current_balance
        self.save(update_fields=['account_balance'])

    class Meta:
        unique_together = ['user', 'contact_number']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['user', 'contact_number']),
        ]

# Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    PAYMENT_MODES = (
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Credit/Debit Card'),
        ('other', 'Other'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='cash')
    date = models.DateField()
    description = models.TextField(null=True, blank=True)
    bill_image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.amount}"

    def save(self, *args, **kwargs):
        # Check if this is an update and bill_image is being replaced
        if not self._state.adding and self.pk:
            try:
                old_instance = Transaction.objects.get(pk=self.pk)
                if old_instance.bill_image and self.bill_image != old_instance.bill_image:
                    # Delete the old image
                    if default_storage.exists(old_instance.bill_image.path):
                        default_storage.delete(old_instance.bill_image.path)
            except Transaction.DoesNotExist:
                pass
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update customer balance on transaction save
        self.customer.update_account_balance()

    def delete(self, *args, **kwargs):
        # Delete associated bill image if it exists
        if self.bill_image:
            try:
                if default_storage.exists(self.bill_image.path):
                    default_storage.delete(self.bill_image.path)
            except Exception as e:
                # Log error but continue with deletion
                print(f"Error deleting bill image: {e}")
        
        super().delete(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'transaction_type']),
            models.Index(fields=['date']),
            models.Index(fields=['payment_mode']),
        ]

# Payment Reminder Model
class PaymentReminder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ("paid", "Paid"),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payment_reminders', null=True, blank=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='payment_reminders', null=True, blank=True)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    reminder_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.customer:
            return f"Reminder to {self.customer.name} for {self.amount_due}"
        elif self.transaction:
            return f"Reminder for transaction {self.transaction.id} - {self.amount_due}"
        return f"Reminder for {self.amount_due}"

    class Meta:
        indexes = [
            models.Index(fields=['reminder_date', 'status']),
            models.Index(fields=['customer']),
            models.Index(fields=['transaction']),
        ]

# Signal handlers for Transaction model
@receiver(post_delete, sender=Transaction)
def update_balance_on_delete(sender, instance, **kwargs):
    """Update the customer's account balance when a transaction is deleted."""
    if instance.customer:
        instance.customer.update_account_balance()