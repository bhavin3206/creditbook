from .models import *
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from rest_framework import filters, generics, status, pagination
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import  IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import *
from rest_framework.generics import UpdateAPIView
from django.shortcuts import get_object_or_404
from django.http import Http404
from datetime import date
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
import requests
from dotenv import load_dotenv

load_dotenv()

# Custom pagination class
class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

#-----------------------------signup /signin view with google --------

class GoogleLoginView(APIView):
    def post(self, request):
        # Get token from request
        access_token = request.data.get("access_token")
        if not access_token:
            return Response({"error": "Access token required"}, status=400)
        
        
        try:
            # Verify token with Google
            idinfo = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            ).json()  

            email = idinfo.get('email')
        
            # Check if user exists - using only required fields
            user = None
            try:
                # Only fetch fields we need
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user with minimal fields
                user = User.objects.create_user(
                    email=email,
                    first_name=idinfo.get('given_name'),
                    last_name=idinfo.get('family_name')
                )
                user.is_verified = True
                user.save()
            
            # This depends on your auth solution (JWT, token, etc.)
            token, _ = Token.objects.get_or_create(user=user)

            # Only return necessary fields
            return Response({
                "email": user.email,
                "address": user.address,
                "category": user.category,  # Return ID instead of full object
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                'profile_picture': user.profile_picture.url if user.profile_picture else None,
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
                return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            response = str(next(iter(e.detail.values())))
            if "This field is required." in response: 
                response = str(next(iter(e.detail.keys()))) + " field is required"
                return Response({"message": response}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": str(next(iter(e.detail.values()))[0])}, status=status.HTTP_400_BAD_REQUEST)

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
        # Use select_related for category to avoid additional query
        if '@' in username:
            try:
                user = User.objects.get(email=username)
            except ObjectDoesNotExist:
                pass

        if not user:
            user = authenticate(username=username, password=password)
            if user:
                # Fetch the category relationship to avoid an extra query later
                user = User.objects.get(pk=user.pk)

        if user:
            # Use delete() with filter for efficiency
            Token.objects.filter(user=user).delete()
            
            token, _ = Token.objects.get_or_create(user=user)
            
            # Only return necessary data
            data = {
                "email": user.email,
                "address": user.address,
                "category": user.category,  # Return ID instead of object
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                'profile_picture': user.profile_picture.url if user.profile_picture else None,
                'token': token.key
            }
            return Response(data, status=status.HTTP_200_OK)

        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# ---------------------------- User Edit View ----------------------------
class UserEditAPIView(UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Use select_related to get related fields in one query
        return User.objects.get(pk=self.request.user.pk)

    def update(self, request, *args, **kwargs):
        # Overriding to perform any extra actions before updating
        user = self.get_object()

        # Ensure the user is editing their own details
        if user.pk != request.user.pk:
            return Response({"message": "Not Found."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed with update
        return super().update(request, *args, **kwargs)
    
# --------------------------- get user profile -------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    token = Token.objects.get(user=user).key  # Get the token

    return Response({
        "email": user.email,
        "address": user.address,
        "category": user.category,  # Return ID instead of object
        "first_name": user.first_name,
        "last_name": user.last_name,
        "mobile_number": user.mobile_number,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'token': token
    })


# ---------------------------- Logout View ----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    if request.method == 'POST':
        try:
            # Delete the user's token to logout - no need to retrieve it first
            Token.objects.filter(user=request.user).delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------- User Transaction Summary View ----------------------------
class UserTransactionSummaryView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserTransactionSummarySerializer

    def get(self, request, *args, **kwargs):
        user = request.user

        # Get total customers for the user
        total_customers = Customer.objects.filter(user=user).count()

        # Get total transaction counts and amounts for credits and debits
        transaction_summary = Transaction.objects.filter(customer__user=user).aggregate(
            total_credit_transactions=Count('id', filter=Q(transaction_type='credit')),
            total_debit_transactions=Count('id', filter=Q(transaction_type='debit')),
            total_credit_amount=Sum('amount', filter=Q(transaction_type='credit')),
            total_debit_amount=Sum('amount', filter=Q(transaction_type='debit')),
        )

        data = {
            "total_customers": total_customers,
            "total_credit_transactions": transaction_summary['total_credit_transactions'],
            "total_debit_transactions": transaction_summary['total_debit_transactions'],
            "total_credit_amount": transaction_summary['total_credit_amount'] or 0,
            "total_debit_amount": transaction_summary['total_debit_amount'] or 0,
        }

        return Response(data)






# ---------------------------- Customer Views ----------------------------
class CustomerListCreateView(generics.ListCreateAPIView):
    """
    API endpoint to list all customers or create a new customer.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Only return customers belonging to the authenticated user.
        """
        # Use only() to select specific fields
        return Customer.objects.filter(user=self.request.user).only(
            'id', 'name', 'contact_number', 'email', 'address', 'account_balance', 
            'created_at', 'updated_at'
        ).order_by('-created_at')  # Order by creation date
    
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
            # Store name before deletion for message
            customer_name = customer.name
            self.perform_destroy(customer)
            return Response({"message": f"Customer '{customer_name}' deleted successfully!"}, status=status.HTTP_200_OK)
        except Http404:
            return Response({"message": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "An error occurred while deleting the customer."}, status=status.HTTP_400_BAD_REQUEST)

# ---------------------------- Customer Transaction Views ----------------------------
class CustomerTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Ensure the authenticated user can only retrieve transactions for their own customers.
        """
        customer_id = self.kwargs.get('customer_id')
        user = self.request.user

        try:
            # First verify the customer belongs to user (lightweight query)
            customer = get_object_or_404(Customer.objects.only('id', 'user_id'), id=customer_id, user=user)
        except Http404:
            raise Http404("Customer not found.")

        # Only select fields that are needed in the serializer response
        return Transaction.objects.filter(customer=customer).only(
            'id', 'customer_id', 'amount', 'transaction_type', 'payment_mode', 
            'date', 'description', 'created_at'
        ).select_related('customer').order_by('-created_at')  # Optimize related customer lookups

    def list(self, request, *args, **kwargs):
        """
        Override list method to return a custom error response instead of Django's default 404.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
                
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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Returns transactions belonging to the authenticated user's customers,
        with additional filtering options.
        """
        user = self.request.user
        queryset = Transaction.objects.filter(customer__user=user).order_by('-created_at')
        
        # Get filter parameters
        customer_name = self.request.query_params.get('customer_name')
        customer_id = self.request.query_params.get('customer_id')
        transaction_type = self.request.query_params.get('transaction_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        specific_date = self.request.query_params.get('specific_date')
        amount = self.request.query_params.get('amount')
        description_keyword = self.request.query_params.get('description')
        payment_mode = self.request.query_params.get('payment_mode')

        # Build filters incrementally to prevent unnecessary query complexity
        filters = Q()

        # Filter by customer name (case-insensitive)
        if customer_name:
            filters &= Q(customer__name__icontains=customer_name)

        # Filter by customer ID
        if customer_id:
            filters &= Q(customer__id=customer_id)

        # Filter by transaction type (credit/debit)
        if transaction_type:
            filters &= Q(transaction_type=transaction_type)

        # Filter by specific date
        if specific_date:
            filters &= Q(date=specific_date)

        # Filter by date range
        if start_date and end_date:
            filters &= Q(date__range=[start_date, end_date])

        # Filter by payment mode
        if payment_mode :
            filters &= Q(payment_mode=payment_mode) if payment_mode == "cash" else ~Q(payment_mode="cash")
         
        # Filter by amount
        if amount:
            filters &= Q(amount=amount)

        # Filter by description keyword
        if description_keyword:
            filters &= Q(description__icontains=description_keyword)

        # Apply all filters at once
        if filters:
            queryset = queryset.filter(filters)

        # Select only needed fields for optimization
        return queryset.select_related('customer').only(
            'id', 'customer_id', 'amount', 'transaction_type', 'payment_mode',
            'date', 'description', 'created_at', 'customer__name'
        )

    def paginate_queryset(self, queryset):
        """Disable pagination when ?pagination=false"""
        pagination_param = self.request.query_params.get('pagination', 'true').lower()
        if pagination_param == 'false':
            return None
        return super().paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        """Return full list if pagination is disabled"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save()

# ---------------------------- Transaction Views ----------------------------
class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Only allow retrieving transactions belonging to the authenticated user.
        """
        return Transaction.objects.filter(customer__user=self.request.user).select_related('customer')

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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Return payment reminders for customers or transactions 
        belonging to the authenticated user.
        """
        user = self.request.user
        queryset = PaymentReminder.objects.filter(customer__user=user).order_by('-created_at')
        
        # Use select_related for better query performance
        queryset = queryset.select_related('customer', 'transaction')
        
        # Only select needed fields
        queryset = queryset.only(
            'id', 'customer_id', 'transaction_id', 'amount_due', 
            'reminder_date', 'status', 'created_at',
            'customer__name', 'transaction__amount', 'transaction__date',
            'transaction__transaction_type'
        )

        payment_status = self.request.query_params.get('payment_status')
        today = date.today()

        # Apply filters as needed
        if payment_status == "overdue":
            queryset = queryset.filter(reminder_date__lt=today, status="pending")
        elif payment_status == "upcoming":
            queryset = queryset.filter(reminder_date__gt=today, status="pending")
        elif payment_status == "due_today":
            queryset = queryset.filter(reminder_date=today, status="pending")
        elif payment_status == "pending":
            queryset = queryset.filter(status="pending")

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
            Q(customer__user=self.request.user) | 
            Q(transaction__customer__user=self.request.user)
        ).select_related('customer', 'transaction')