from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.files.storage import default_storage
import os
import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F


# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email=None , mobile_number=None, password=None, **extra_fields):
        if not email and not mobile_number:
            raise ValueError("User must have a mobile number or email")
        if email and not mobile_number:
            user = self.model(email=email, **extra_fields)
        if mobile_number and not email:
            user = self.model(mobile_number=mobile_number, **extra_fields)
        if mobile_number and email:
            user = self.model(email=email, mobile_number=mobile_number, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, password, email=None , mobile_number=None):
        if not password:
            raise ValueError("Superuser must have a password")
                
        user = self.create_user(password, mobile_number=mobile_number, email=email)
        user.is_superuser = True
        user.is_staff = True
        user.is_verified = True
        user.is_approved = True
        user.save(using=self._db)
        return user

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=50, unique=True, null=True, blank=True,  db_index=True)
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True, db_index=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
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
        return f"{self.first_name or ''} {self.last_name or ''} ({self.mobile_number})"

# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Customer Model
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')  # Use 'customers' for the reverse relationship
    name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)  # Made optional
    address = models.TextField()
    account_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Unique constraint: name must be unique within the scope of each user
        constraints = [
            models.UniqueConstraint(fields=['user', 'name', 'contact_number'], name='unique_customer_name_per_user')
        ]


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

    PAYMENT_MODE_CHOICES = [
        ("cash", "Cash"),
        ("gpay", "G-pay"),
        ("phonepe", "Phonepe"),
        ("imps", "IMPS"),
        ("neft", "NEFT"),
        ("rtgs", "RTGS"),
        ("debit-card", "Debit Card"),
        ("credit-card", "Credit Card"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="transactions")
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    payment_mode = models.CharField(max_length=11, choices=PAYMENT_MODE_CHOICES, default='cash')
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    bill_image = models.ImageField(upload_to=transaction_bill_upload_path, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.customer:
            self.customer_name = self.customer.name
        super().save(*args, **kwargs)
        # self.customer.update_balance()
    
    def delete(self, *args, **kwargs):
        if self.bill_image and default_storage.exists(self.bill_image.name):
            self.bill_image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.amount}"

# Payment Reminder Model
class PaymentReminder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
    ]


    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payment_reminders", null=True, blank=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="reminders", null=True, blank=True)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    reminder_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Unique constraint: name must be unique within the scope of each user
        constraints = [
            models.UniqueConstraint(fields=['customer', 'transaction', 'amount_due'], name='unique_customer_name_per_transaction')
        ]

    def __str__(self):
        return f"Reminder for {self.customer.name} - {self.status}"


from django.db.models import F, Sum, Case, When, DecimalField



@receiver(post_save, sender=Transaction)
def update_balance_on_transaction_save(sender, instance, created, **kwargs):
    """Handles balance updates when a transaction is created or updated."""
    if created:
        # New transaction: Apply balance change
        delta = instance.amount if instance.transaction_type == "credit" else -instance.amount
        Customer.objects.filter(id=instance.customer.id).update(account_balance=F('account_balance') + delta)
    else:
        # Transaction updated: Adjust for the old amount
        try:
            old_transaction = sender.objects.get(id=instance.id)
            
            # Compute balance difference
            old_impact = old_transaction.amount if old_transaction.transaction_type == "credit" else -old_transaction.amount
            new_impact = instance.amount if instance.transaction_type == "credit" else -instance.amount
            net_change = new_impact - old_impact

            # Apply net change
            if net_change != 0:
                Customer.objects.filter(id=instance.customer.id).update(account_balance=F('account_balance') + net_change)
        except sender.DoesNotExist:
            # If transaction record was missing, recalculate balance
            recalculate_customer_balance(instance.customer.id)

@receiver(post_delete, sender=Transaction)
def update_balance_on_transaction_delete(sender, instance, **kwargs):
    """Handles balance updates when a transaction is deleted."""
    # Reverse the impact of the deleted transaction
    delta = -instance.amount if instance.transaction_type == "credit" else instance.amount
    Customer.objects.filter(id=instance.customer.id).update(account_balance=F('account_balance') + delta)

def recalculate_customer_balance(customer_id):
    """Fallback function to recalculate the entire balance in case of inconsistencies."""
    result = Transaction.objects.filter(customer_id=customer_id).aggregate(
        balance=Sum(
            Case(
                When(transaction_type="credit", then=F("amount")),
                When(transaction_type="debit", then=-F("amount")),
                default=0,
                output_field=DecimalField()
            )
        )
    )
    
    balance = result["balance"] or 0
    Customer.objects.filter(id=customer_id).update(account_balance=balance)
