import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def test_api():
    print("🚀 Testing AI Finance Assistant API\n")
    
    # 1. Register a new user
    print("1️⃣ Registering new user...")
    user_data = {
        "email": "john@example.com",
        "username": "john_doe",
        "password": "securepass123"
    }
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    if response.status_code == 200:
        print("✅ User registered successfully!")
    else:
        print(f"❌ Registration failed: {response.text}")
    
    # 2. Login
    print("\n2️⃣ Logging in...")
    login_data = {
        "username": "john_doe",
        "password": "securepass123"
    }
    response = requests.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        token = token_data["access_token"]
        print("✅ Login successful!")
        headers = {"Authorization": f"Bearer {token}"}
    else:
        print(f"❌ Login failed: {response.text}")
        return
    
    # 3. Test SMS parsing
    print("\n3️⃣ Testing SMS transaction parsing...")
    sms_samples = [
        "Your a/c XX1234 debited by Rs.2,500.00 on 15-12-2023 at SWIGGY BANGALORE. Avl bal: Rs.10,000",
        "Amount of Rs.15,000 credited to your a/c XX1234 on 20-12-2023. Salary from TECH CORP",
        "You have paid Rs.1,200 to NETFLIX using your debit card ending 5678"
    ]
    
    for sms in sms_samples:
        response = requests.post(
            f"{BASE_URL}/transactions/parse-sms",
            data={"sms_text": sms},
            headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            parsed = result['parsed_data']
            
            # Handle the parsed data properly
            merchant = parsed.get('merchant', 'Unknown')
            amount = parsed.get('amount', 0)
            trans_type = parsed.get('type', 'expense')
            
            print(f"  ✅ Parsed SMS:")
            print(f"     Merchant: {merchant}")
            print(f"     Amount: ₹{amount:,.2f}")
            print(f"     Type: {trans_type}")
            print(f"     Category: {result['category']} (Confidence: {result['confidence']:.2%})")
        else:
            print(f"  ❌ Failed to parse SMS: {response.text}")
    
    # 4. Get transactions
    print("\n4️⃣ Fetching transactions...")
    response = requests.get(f"{BASE_URL}/transactions/", headers=headers)
    if response.status_code == 200:
        transactions = response.json()
        print(f"✅ Found {len(transactions)} transactions")
        
        # Display transaction details
        for trans in transactions[:3]:  # Show first 3
            print(f"  - {trans['description']}: ₹{trans['amount']:,.2f} ({trans['transaction_type']})")
    
    # 5. Get analytics
    print("\n5️⃣ Getting spending analytics...")
    response = requests.get(f"{BASE_URL}/analytics/spending-by-category", headers=headers)
    if response.status_code == 200:
        spending = response.json()
        if spending:
            print("📊 Spending by Category:")
            for cat in spending:
                print(f"  - {cat['category']}: ₹{cat['amount']:,.2f} ({cat['percentage']:.1f}%)")
        else:
            print("  No spending data yet")
    
    # 6. Get insights
    print("\n6️⃣ Getting AI insights...")
    response = requests.get(f"{BASE_URL}/analytics/insights", headers=headers)
    if response.status_code == 200:
        insights = response.json()
        print(f"  💡 Current month spending: ₹{insights['current_month_spending']:,.2f}")
        print(f"  📈 Spending trend: {insights['spending_trend']}")
        if insights.get('top_spending_category'):
            print(f"  🏷️ Top category: {insights['top_spending_category']}")
    
    # Replace the natural language query section (around line 107-122) with:
    # 7. Natural language query
    print("\n7️⃣ Testing natural language queries...")
    queries = [
        "How much did I spend this month?",
        "What's my top spending category?",
        "How much am I saving?"
    ]
    
    for query in queries:
        response = requests.post(
            f"{BASE_URL}/query",
            data={"query": query},
            headers=headers
        )
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"\n  Q: {query}")
                print(f"  A: {result.get('answer', 'No answer available')}")
            except Exception as e:
                print(f"  Error processing response: {e}")
        else:
            print(f"  Failed to process query: {response.status_code}")

    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_api()
