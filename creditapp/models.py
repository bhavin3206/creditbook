from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.files.storage import default_storage
import os
import uuid

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, mobile_number, password=None):
        if not mobile_number:
            raise ValueError("User must have a mobile number")

        user = self.model(mobile_number=mobile_number)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, mobile_number, password):
        if not password:
            raise ValueError("Superuser must have a password")

        user = self.create_user(mobile_number, password)
        user.is_superuser = True
        user.is_staff = True
        user.is_verified = True
        user.is_approved = True
        user.save(using=self._db)
        return user

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    # groups = models.ManyToManyField(
    #     'auth.Group',
    #     related_name='creditapp_user_set',  # Updated related_name to avoid clash
    #     blank=True,
    # )
    # user_permissions = models.ManyToManyField(
    #     'auth.Permission',
    #     related_name='creditapp_user_set',  # Updated related_name to avoid clash
    #     blank=True,
    # )

    email = models.EmailField(max_length=50, unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, unique=True, db_index=True)
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
        return f"{self.first_name or ''} {self.last_name or ''} ({self.mobile_number})"

# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Customer Model
class Customer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)  # Made optional
    address = models.TextField()
    account_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_balance(self):
        """
        Automatically calculates balance based on transactions
        """
        credits = self.transactions.filter(transaction_type="credit").aggregate(models.Sum("amount"))["amount__sum"] or 0
        debits = self.transactions.filter(transaction_type="debit").aggregate(models.Sum("amount"))["amount__sum"] or 0
        self.account_balance = credits - debits
        self.save()

    def delete(self, *args, **kwargs):
        """ Delete all transactions and their images first for fast processing """
        transactions = self.transactions.all()

        # Collect all file paths
        bill_images = [transaction.bill_image.name for transaction in transactions if transaction.bill_image]

        # Bulk delete transactions (faster than calling .delete() on each)
        transactions.delete()

        # Bulk delete bill images (super fast)
        for bill in bill_images:
            if default_storage.exists(bill):
                default_storage.delete(bill)

        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

# Function to generate unique filenames for transaction bills
def transaction_bill_upload_path(instance, filename):
    """Generate a unique filename for uploaded bills"""
    ext = filename.split('.')[-1]
    unique_filename = f"bill_{uuid.uuid4().hex}.{ext}"
    return os.path.join("transaction_bills/", unique_filename)

# Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="transactions")
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    bill_image = models.ImageField(upload_to=transaction_bill_upload_path, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.customer:
            self.customer_name = self.customer.name
        super().save(*args, **kwargs)
        self.customer.update_balance()
    
    def delete(self, *args, **kwargs):
        if self.bill_image and default_storage.exists(self.bill_image.name):
            self.bill_image.delete(save=False)
        super().delete(*args, **kwargs)
        self.customer.update_balance()


    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.amount}"

# Payment Reminder Model
class PaymentReminder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("paid", "Paid"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payment_reminders")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    reminder_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reminder for {self.customer.name} - {self.status}"
