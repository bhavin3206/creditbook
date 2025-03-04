from django.urls import path
from django.conf.urls.static import static
from django.conf import settings

from .views import (
    SignupView, SigninView, LogoutView,
    CustomerListCreateView, CustomerDetailView,
    DeleteCustomerView, CustomTokenRefreshView,
    CustomerTransactionsView, TransactionDeleteView,
    TransactionListCreateView, TransactionDetailView,
    PaymentReminderListCreateView, PaymentReminderDetailView
)

urlpatterns = [
    # Authentication URLs
    path('signup/', SignupView.as_view(), name='signup'),
    path('signin/', SigninView.as_view(), name='signin'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),


    # Customer URLs
    path('customers/', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('delete-customer/<int:pk>/', DeleteCustomerView.as_view(), name='delete-customer'),


    # Transaction URLs
    path('transactions/', TransactionListCreateView.as_view(), name='transaction-list-create'),
    path('customers/<int:customer_id>/transactions/', CustomerTransactionsView.as_view(), name='customer-transactions'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/delete/<int:pk>/', TransactionDeleteView.as_view(), name='delete-transaction'),


    # Payment Reminder URLs
    path('payment-reminders/', PaymentReminderListCreateView.as_view(), name='payment-reminder-list-create'),
    path('payment-reminders/<int:pk>/', PaymentReminderDetailView.as_view(), name='payment-reminder-detail'),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
