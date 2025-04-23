from .models import *
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import *
from rest_framework.generics import UpdateAPIView
from django.shortcuts import get_object_or_404, get_list_or_404
from django.http import Http404
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from google.oauth2 import id_token
from google.auth.transport import requests
import os
from dotenv import load_dotenv

load_dotenv()
#-----------------------------signup /signin view with google --------

class GoogleLoginView(APIView):
    def post(self, request):
        # Get token from request
        token = request.data.get('id_token')
        
        try:
            # Verify token with Google
            google_client_id = os.environ.get('CLIENT_ID')
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), google_client_id)
            email = idinfo.get('email')
        
            # Check if user exists
            user = None
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user
                user = User.objects.create_user(
                    email=email,
                    first_name=idinfo.get('given_name'),
                    last_name=idinfo.get('family_name')
                )
                user.is_verified = True
                user.save()
            
            # This depends on your auth solution (JWT, token, etc.)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                "email" : user.email,
                "address" : user.address,
                "category" : user.category,
                "first_name" : user.first_name,
                "last_name" : user.last_name,
                "mobile_number" : user.mobile_number,
                'profile_picture': user.profile_picture.url if user.profile_picture else None,  # Handle None for profile_picture
                'token': token.key

            })
        
        except ValueError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

# ---------------------------- Signup View ----------------------------
@api_view(['POST'])
def SignupView(request):
    if request.method == 'POST':
        serializer = SignupSerializer(data=request.data)
        try:
            if serializer.is_valid(raise_exception=True):
                user = serializer.save()
                return Response({"message": "User  created successfully."}, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            response = str(next(iter(e.detail.values())))
            if "This field is required." in response: 
                response = str(next(iter(e.detail.keys()))) + " field is required"
                return Response({"message":response}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message":str(next(iter(e.detail.values()))[0])}, status=status.HTTP_400_BAD_REQUEST)

# ---------------------------- Signin View ----------------------------
@api_view(['POST'])
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        if not username:
            return Response({'message': 'username field required'}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get('password')
        if not password:
            return Response({'message': 'password field required'}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except ObjectDoesNotExist:
                pass

        if not user:
            user = authenticate(username=username, password=password)

        if user:
            Token.objects.filter(user=user).delete()
            
            token, _ = Token.objects.get_or_create(user=user)
            data = {
                "email" : user.email,
                "address" : user.address,
                "category" : user.category,
                "first_name" : user.first_name,
                "last_name" : user.last_name,
                "mobile_number" : user.mobile_number,
                'profile_picture': user.profile_picture.url if user.profile_picture else None,  # Handle None for profile_picture
                'token': token.key
            }
            return Response(data, status=status.HTTP_200_OK)

        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# ---------------------------- User Edit View ----------------------------
class UserEditAPIView(UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated to edit

    def get_object(self):
        return self.request.user  # Assumes you're updating the currently authenticated user

    def update(self, request, *args, **kwargs):
        # Overriding to perform any extra actions before updating
        user = self.get_object()

        # Ensure the user is editing their own details
        if user != request.user :
            return Response({"message": "Not Found."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed with update
        return super().update(request, *args, **kwargs)



# ---------------------------- Logout View ----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    if request.method == 'POST':
        try:
            # Delete the user's token to logout
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    """
    API endpoint to list all customers or create a new customer.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        """
        Only return customers belonging to the authenticated user.
        """
        return Customer.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            if 'UNIQUE constraint failed:' in str(e):
                return Response({'message': 'Customer with this Mobile number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'message': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update, or delete a specific customer.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        """
        Ensure the customer being accessed belongs to the authenticated user.
        """
        return Customer.objects.filter(user=self.request.user)


# ---------------------------- Delete Customer Views ----------------------------
class DeleteCustomerView(generics.DestroyAPIView):
    """
    API to delete a customer and all related transactions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        """Ensure customers belong to the authenticated user."""
        return Customer.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        try:
            customer_id = self.kwargs.get("pk")
            customer = get_object_or_404(Customer, id=customer_id, user=self.request.user)
            self.perform_destroy(customer)
            return Response({"message": f"Customer '{customer.name}' deleted successfully!"}, status=status.HTTP_200_OK)
        except Http404:  # Catch customer not found
            return Response({"message": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "An error occurred while deleting the customer."}, status=status.HTTP_400_BAD_REQUEST)



# ---------------------------- Customer Transaction Views ----------------------------
class CustomerTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Ensure the authenticated user can only retrieve transactions for their own customers.
        """
        customer_id = self.kwargs.get('customer_id')
        user = self.request.user

        try:
            customer = get_object_or_404(Customer, id=customer_id, user=user)
        except Http404:
            raise Http404("Customer not found.")  # Custom error message

        return Transaction.objects.filter(customer=customer)

    def list(self, request, *args, **kwargs):
        """
        Override list method to return a custom error response instead of Django's default 404.
        """
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404 as e:
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)

# ---------------------------- Transaction Views ----------------------------
class TransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['date', 'amount']
    ordering = ['-created_at']
    search_fields = ['customer__name', 'description']

    def get_queryset(self):
        """
        Returns transactions belonging to the authenticated user's customers,
        with additional filtering options.
        """
        user = self.request.user
        queryset = Transaction.objects.filter(customer__user=user)
        # Get filter parameters
        customer_name = self.request.query_params.get('customer_name')
        customer_id = self.request.query_params.get('customer_id')
        transaction_type = self.request.query_params.get('transaction_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        specific_date = self.request.query_params.get('specific_date')
        amount = self.request.query_params.get('amount')
        description_keyword = self.request.query_params.get('description')
        payment_mode = self.request.query_params.get('payment_mode')  # New filter

        today = date.today()

        # Filter by customer name (case-insensitive)
        if customer_name:
            queryset = queryset.filter(customer__name__icontains=customer_name)

        # Filter by customer ID
        if customer_id:
            queryset = queryset.filter(customer__id=customer_id)

        # Filter by transaction type (credit/debit)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # Filter by specific date
        if specific_date:
            queryset = queryset.filter(date=specific_date)

        # Filter by date range
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])

        # Filter by payment mode
        if payment_mode:
            queryset = queryset.filter(payment_mode=payment_mode)

        # Filter by amount
        if amount:
            queryset = queryset.filter(amount=amount)

        # Filter by description keyword
        if description_keyword:
            queryset = queryset.filter(description__icontains=description_keyword)

        return queryset

    def perform_create(self, serializer):
        transaction = serializer.save()


# ---------------------------- Transaction Views ----------------------------
class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Only allow retrieving transactions belonging to the authenticated user.
        """
        return Transaction.objects.filter(customer__user=self.request.user)

#----------------------------- Transaction Delete Views ---------------------
class TransactionDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        """
        Ensure only the authenticated user's transactions can be deleted.
        """
        return Transaction.objects.filter(customer__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        """
        Handle transaction deletion with user validation.
        """
        transaction = self.get_object()
        self.perform_destroy(transaction)
        return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

# ---------------------------- Payment Reminder Views ----------------------------
class PaymentReminderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer

    def get_queryset(self):
        """
        Return payment reminders for customers or transactions 
        belonging to the authenticated user.
        """
        # return PaymentReminder.objects.filter(
        #     models.Q(customer__user=self.request.user) | 
        #     models.Q(transaction__customer__user=self.request.user)
        # )
        user = self.request.user
        queryset = PaymentReminder.objects.filter(customer__user=self.request.user)

        today = date.today()

        payment_status = self.request.query_params.get('payment_status')  # New filter

        if payment_status == "overdue":
            queryset = queryset.filter(reminder_date__lt=today, status="pending").distinct()
        elif payment_status == "upcoming":
            queryset = queryset.filter(reminder_date__gt=today, status="pending").distinct()
        elif payment_status == "due_today":
            queryset = queryset.filter(reminder_date=today, status="pending").distinct()

        return queryset
    
    def perform_create(self, serializer):
        """
        Create a reminder after validation in the serializer.
        """
        serializer.save()



class PaymentReminderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReminderSerializer

    def get_queryset(self):
        """
        Return only reminders that belong to the authenticated user's customers or transactions.
        """
        return PaymentReminder.objects.filter(
            models.Q(customer__user=self.request.user) | 
            models.Q(transaction__customer__user=self.request.user)
        )
