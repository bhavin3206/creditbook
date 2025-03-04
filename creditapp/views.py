# from .models import *
# from .serializers import *
# from rest_framework.response import Response
# from rest_framework import generics
# from rest_framework_api_key.permissions import HasAPIKey
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework import status


# # Create your views here.
# class SignupView(generics.ListCreateAPIView):
#     permission_classes  = [AllowAny]
#     serializer_class    = SignupSerializer
#     queryset            = User.objects.all().order_by('-id')

#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)

# class SigninView(generics.GenericAPIView):
#     permission_classes      = [AllowAny]
#     serializer_class        = SigninSerializer
#     queryset                = User.objects.all().order_by('-id')

#     def post(self,request):
#         serializer = self.serializer_class(data=request.data)
#         if serializer.is_valid():
#             return Response(serializer.validated_data,status=status.HTTP_200_OK)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class LogoutView(generics.GenericAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = LogoutSerializer

#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from .models import User, Customer, Transaction, PaymentReminder
from .serializers import (
    SignupSerializer, SigninSerializer, LogoutSerializer,
    CustomerSerializer, TransactionSerializer, PaymentReminderSerializer
)
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated


# ---------------------------- Signup View ----------------------------
class SignupView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer
    queryset = User.objects.all().order_by('-id')


# ---------------------------- Signin View ----------------------------
class SigninView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SigninSerializer
    queryset = User.objects.all().order_by('-id')

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            return Response({"message": serializer.validated_data}, status=status.HTTP_200_OK)
        return Response({"message": serializer.errors["non_field_errors"][0]}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------- Logout View ----------------------------
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})  # Pass context
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        return Response({"message":serializer.errors[0]}, status=status.HTTP_400_BAD_REQUEST)

#----------------------------- Refresh Token View ----------------------------
class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom Token Refresh API to provide a new access token
    using a valid refresh token.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response(
            {"access_token": response.data["access"]}, 
            status=status.HTTP_200_OK
        )


# ---------------------------- Customer Views ----------------------------
class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        # Check if customer with the same name already exists
        if Customer.objects.filter(name=request.data.get("name")).exists():
            return Response({"message": "Customer with this name already exists."}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()

class DeleteCustomerView(generics.DestroyAPIView):
    """
    API to delete a customer and all related transactions.
    """
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        customer_name = customer.name
        self.perform_destroy(customer)
        return Response({"message": f"Customer '{customer_name}' deleted successfully!"}, status=status.HTTP_200_OK)



# ---------------------------- Customer Transaction Views ----------------------------
class CustomerTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        customer_id = self.kwargs['customer_id']
        return Transaction.objects.filter(customer_id=customer_id)


# ---------------------------- Transaction Views ----------------------------
class TransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        transaction = serializer.save()


# ---------------------------- Transaction Views ----------------------------
class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

#----------------------------- Transaction Delete Views ---------------------
class TransactionDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()
    lookup_field = "pk"  # Allows deleting by primary key (id)

    def delete(self, request, *args, **kwargs):
        try:
            transaction = self.get_object()
            transaction.delete()
            return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Transaction.DoesNotExist:
            return Response({"message": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

# ---------------------------- Payment Reminder Views ----------------------------
class PaymentReminderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer
    queryset = PaymentReminder.objects.all().order_by('-reminder_date')


class PaymentReminderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer
    queryset = PaymentReminder.objects.all()
            queryset = queryset.filter(amount=amount)

        if description_keyword:
            queryset = queryset.filter(description__icontains=description_keyword)  # Filters by word in description

        return queryset

    def perform_create(self, serializer):
        transaction = serializer.save()


# ---------------------------- Transaction Views ----------------------------
class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

#----------------------------- Transaction Delete Views ---------------------
class TransactionDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()
    lookup_field = "pk"  # Allows deleting by primary key (id)

    def delete(self, request, *args, **kwargs):
        try:
            transaction = self.get_object()
            transaction.delete()
            return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Transaction.DoesNotExist:
            return Response({"message": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

# ---------------------------- Payment Reminder Views ----------------------------
class PaymentReminderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer
    queryset = PaymentReminder.objects.all().order_by('-reminder_date')


class PaymentReminderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer
    queryset = PaymentReminder.objects.all()
