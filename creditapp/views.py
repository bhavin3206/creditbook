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
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)

        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


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
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        customer_name = request.data.get("name")
        serializer = self.get_serializer(data=request.data)
        
        try:
            if serializer.is_valid(raise_exception=True):
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            response = str(next(iter(e.detail.values())))
            
            if "This field is required." in response:
                response = str(next(iter(e.detail.keys()))) + " field is required"
                return Response({"message": response}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"message": str(next(iter(e.detail.values()))[0])}, status=status.HTTP_400_BAD_REQUEST)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()


# ---------------------------- Delete Customer Views ----------------------------
class DeleteCustomerView(generics.DestroyAPIView):
    """
    API to delete a customer and all related transactions.
    """
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def delete(self, request, *args, **kwargs):
        try:
            customer = self.get_object()
            customer_name = customer.name
            self.perform_destroy(customer)
            return Response({"message": f"Customer '{customer_name}' deleted successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "Customer not found or alredy delete"}, status=status.HTTP_400_BAD_REQUEST)




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
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]

    ordering_fields = ['date', 'amount']
    ordering = ['-created_at']
    search_fields = ['customer__name', 'description']

    def get_queryset(self):
        """
        Manually filter transactions based on query parameters
        """
        queryset = Transaction.objects.all().order_by('-created_at')

        customer_name = self.request.query_params.get('customer_name')
        customer_id = self.request.query_params.get('customer_id')
        transaction_type = self.request.query_params.get('transaction_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        specific_date = self.request.query_params.get('specific_date')  # New parameter
        amount = self.request.query_params.get('amount')
        description_keyword = self.request.query_params.get('description')  # New filter

        if customer_name:
            queryset = queryset.filter(customer__name__icontains=customer_name)

        if customer_id:
            queryset = queryset.filter(customer__id=customer_id)

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        if specific_date:
            queryset = queryset.filter(date=specific_date)  # Exact date match

        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])

        if amount:
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
