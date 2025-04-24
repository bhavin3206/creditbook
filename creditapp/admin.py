from django.contrib import admin

# Register your models here.
from .models import User,  Customer, Transaction, PaymentReminder

admin.site.register(User)
admin.site.register(Customer)
admin.site.register(Transaction)
admin.site.register(PaymentReminder)
