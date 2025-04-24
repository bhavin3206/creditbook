import asyncio
import random
from datetime import datetime, timedelta

import httpx
from faker import Faker

fake = Faker()

# === CONFIGURATION ===
API_BASE = "http://127.0.0.1:8000/api"
CUSTOMER_COUNT = 20
MAX_TRANSACTIONS_PER_CUSTOMER = 10
OWNER_USER_ID = 1  # Replace with your actual user ID
AUTH_TOKEN = "74961b7b3301be58c9955f83249db549a2aefe82"  # Replace with your token

HEADERS = {
    "Authorization": f"Token {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

client = httpx.AsyncClient(headers=HEADERS)

async def create_customer():
    data = {
        "name": fake.name(),
        "contact_number": fake.numerify(text="##########"),
        "email": fake.email(),
        "address": fake.address(),
    }
    try:
        response = await client.post(f"{API_BASE}/customers/", json=data)
        if response.status_code == 201:
            customer = response.json()
            print(f"✅ Created customer: {customer['name']}")
            return customer['id']
        else:
            print(f"❌ Customer creation failed: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"⚠️ Error creating customer: {e}")
    return None

async def create_transaction(customer_id):
    transaction_type = random.choice(["credit", "debit"])
    data = {
        "customer": customer_id,
        "amount": round(random.uniform(50, 1000), 2),
        "transaction_type": transaction_type,
        "payment_mode": random.choice(["cash", "upi", "bank_transfer", "cheque", "card", "other"]),
        "date": (datetime.now() - timedelta(days=random.randint(1, 100))).date().isoformat(),
        "description": fake.sentence(),
    }
    try:
        response = await client.post(f"{API_BASE}/transactions/", json=data)
        if response.status_code == 201:
            transaction = response.json()
            print(f"   → Created {transaction_type} ₹{data['amount']} (ID: {transaction['id']})")
            return transaction['id'], data['amount']
        else:
            print(f"❌ Transaction failed: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"⚠️ Error creating transaction: {e}")
    return None, None

async def create_payment_reminder(customer_id, transaction_id, amount, due_type):
    if due_type == "overdue":
        reminder_date = (datetime.now() - timedelta(days=3)).date().isoformat()
    elif due_type == "due_today":
        reminder_date = (datetime.now() + timedelta(days=1)).date().isoformat()
    else:  # upcoming
        reminder_date = (datetime.now() + timedelta(days=5)).date().isoformat()

    data = {
        "customer": customer_id,
        "transaction": transaction_id,
        "amount_due": amount,
        "reminder_date": reminder_date,
        "status": "pending",
    }
    try:
        response = await client.post(f"{API_BASE}/payment-reminders/", json=data)
        if response.status_code == 201:
            print(f"   📌 Created payment reminder ({due_type}) for ₹{amount}")
        else:
            print(f"❌ Reminder failed: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"⚠️ Error creating payment reminder: {e}")

async def create_customer_with_transactions():
    customer_id = await create_customer()
    if customer_id:
        transaction_refs = []
        for _ in range(random.randint(5, MAX_TRANSACTIONS_PER_CUSTOMER)):
            tid, amt = await create_transaction(customer_id)
            if tid:
                transaction_refs.append((tid, amt))

        if len(transaction_refs) >= 3:
            await create_payment_reminder(customer_id, transaction_refs[0][0], transaction_refs[0][1], "overdue")
            await create_payment_reminder(customer_id, transaction_refs[1][0], transaction_refs[1][1], "due_today")
            await create_payment_reminder(customer_id, transaction_refs[2][0], transaction_refs[2][1], "upcoming")

async def main():
    tasks = [create_customer_with_transactions() for _ in range(CUSTOMER_COUNT)]
    await asyncio.gather(*tasks)
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
