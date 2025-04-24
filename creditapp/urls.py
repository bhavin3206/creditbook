from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .views import *

urlpatterns = [
    # Authentication URLs
    path('signup/', SignupView, name='signup'),
    path('signin/', user_login, name='signin'),
    path('logout/', user_logout, name='logout'),
    path('edit/', UserEditAPIView.as_view(), name='user-edit'),
    path('user/profile/', get_user_profile),
    # path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),

    # social login 
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),

    # Customer URLs
    path('customers/', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer-detail'),


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
