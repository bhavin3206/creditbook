# API Documentation

## 1. Signup API
- **Endpoint**: `POST http://127.0.0.1:8000/api/signup/`
- **Headers**: 
  - Content-Type: application/json
- **Request Payload**:
```json
{
  "username": "exampleuser",
  "password": "examplepassword"
}
```
- **Response**:
  - **200 OK**: 
  ```json
  {
    "message": "User created successfully",
    "user": {
      "id": 1,
      "username": "exampleuser"
    }
  }
  ```
  - **400 BAD REQUEST**: 
  ```json
  {
    "message": "Validation error messages"
  }
  ```

## 2. Signin API
- **Endpoint**: `POST http://127.0.0.1:8000/api/signin/`
- **Headers**: 
  - Content-Type: application/json
- **Request Payload**:
```json
{
  "username": "exampleuser",
  "password": "examplepassword"
}
```
- **Response**:
  - **200 OK**: 
  ```json
  {
    "message": {
      "access": "your_access_token",
      "refresh": "your_refresh_token"
    }
  }
  ```
  - **400 BAD REQUEST**: 
  ```json
  {
    "message": "Invalid credentials"
  }
  ```

## 3. Logout API
- **Endpoint**: `POST http://127.0.0.1:8000/api/logout/`
- **Headers**: 
  - Content-Type: application/json
  - Authorization: Bearer your_access_token
- **Request Payload**:
```json
{}
```
- **Response**:
  - **205 RESET CONTENT**: 
  ```json
  {
    "message": "Logout successful"
  }
  ```
  - **400 BAD REQUEST**: 
  ```json
  {
    "message": "Error message"
  }
  ```

## 4. Customer List API
- **Endpoint**: `GET http://127.0.0.1:8000/api/customers/`
- **Headers**: 
  - Authorization: Bearer your_access_token
- **Response**:
  - **200 OK**: 
  ```json
  [
    {
      "id": 1,
      "name": "Customer Name",
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
  ```

## 5. Customer Transactions API
- **Endpoint**: `GET http://127.0.0.1:8000/api/customers/{customer_id}/transactions`
- **Headers**: 
  - Authorization: Bearer your_access_token
- **Response**:
  - **200 OK**: 
  ```json
  [
    {
      "id": 1,
      "amount": 100,
      "date": "2023-01-01T00:00:00Z"
    }
  ]
  ```

## 6. Payment Reminder API
- **Endpoint**: `POST http://127.0.0.1:8000/api/payment-reminders`
- **Headers**: 
  - Authorization: Bearer your_access_token
  - Content-Type: application/json
- **Request Payload**:
```json
{
  "reminder_date": "2023-01-01T00:00:00Z",
  "message": "Payment due"
}
```
- **Response**:
  - **201 CREATED**: 
  ```json
  {
    "message": "Payment reminder created successfully"
  }
  ```

## Authorization Header Example
- **Format**: `Authorization: Bearer <token>`
- **Example**: `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
