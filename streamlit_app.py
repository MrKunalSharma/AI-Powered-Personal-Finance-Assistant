import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# API Configuration
if 'API_URL' in st.secrets:
    BASE_URL = st.secrets['https://ai-finance-api-sj9l.onrender.com/api/v1']
else:
    BASE_URL = os.getenv('API_URL', 'http://localhost:8000/api/v1')


# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Page config
st.set_page_config(
    page_title="AI Finance Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=AI+Finance", width=150)
    st.markdown("---")
    
    if st.session_state.token is None:
        # Login/Register
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("### Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_btn"):
                try:
                    response = requests.post(
                        f"{BASE_URL}/login",
                        data={"username": username, "password": password},
                        timeout=8
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.username = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API at host 'localhost:8000'. Please start the backend server.")
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
        
        with tab2:
            st.markdown("### Register")
            new_email = st.text_input("Email", key="reg_email")
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input("Password", type="password", key="reg_password")
            
            if st.button("Register", key="register_btn"):
                try:
                    response = requests.post(
                        f"{BASE_URL}/register",
                        json={
                            "email": new_email,
                            "username": new_username,
                            "password": new_password
                        },
                        timeout=8
                    )
                    if response.status_code == 200:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Registration failed")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API at host 'localhost:8000'. Please start the backend server.")
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")
    else:
        # User menu
        st.markdown(f"### Welcome, {st.session_state.username}!")
        st.markdown("---")
        
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()

# Main content
if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    # Header
    st.markdown('<h1 class="main-header">💰 AI Finance Assistant</h1>', unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 Dashboard", "💳 Transactions", "📈 Analytics", "🤖 AI Assistant", "📤 Import", "💰 Budgets", "💱 Currency"])

    
    # Dashboard Tab
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        
        # Get insights
        insights_response = requests.get(f"{BASE_URL}/analytics/insights", headers=headers)
        if insights_response.status_code == 200:
            insights = insights_response.json()
            
            with col1:
                st.metric(
                    "Current Month Spending",
                    f"₹{insights['current_month_spending']:,.2f}",
                    f"{insights['trend_percentage']:.1f}% vs last month"
                )
            
            with col2:
                st.metric("Spending Trend", insights['spending_trend'].title())
            
            with col3:
                st.metric("Top Category", insights.get('top_spending_category', 'N/A'))
        
        # Spending by category chart
        st.markdown("### 📊 Spending by Category")
        spending_response = requests.get(f"{BASE_URL}/analytics/spending-by-category", headers=headers)
        if spending_response.status_code == 200:
            spending_data = spending_response.json()
            if spending_data:
                df = pd.DataFrame(spending_data)
                fig = px.pie(df, values='amount', names='category', title='Spending Distribution')
                st.plotly_chart(fig, use_container_width=True)
        
        # Monthly trend
        st.markdown("### 📈 Monthly Trend")
        trend_response = requests.get(f"{BASE_URL}/analytics/monthly-trend", headers=headers)
        if trend_response.status_code == 200:
            trend_data = trend_response.json()
            if trend_data:
                df_trend = pd.DataFrame(trend_data)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_trend['month'], y=df_trend['income'], name='Income', line=dict(color='green')))
                fig.add_trace(go.Scatter(x=df_trend['month'], y=df_trend['expense'], name='Expenses', line=dict(color='red')))
                fig.add_trace(go.Scatter(x=df_trend['month'], y=df_trend['savings'], name='Savings', line=dict(color='blue')))
                fig.update_layout(title='Income vs Expenses vs Savings', xaxis_title='Month', yaxis_title='Amount (₹)')
                st.plotly_chart(fig, use_container_width=True)

        # Add Predictions Section in Dashboard
        st.markdown("---")
        st.markdown("### 🔮 AI Predictions & Insights")
        
        # Get predictions
        predictions_response = requests.get(f"{BASE_URL}/predictions/insights", headers=headers)
        if predictions_response.status_code == 200:
            predictions = predictions_response.json()
            
            # Show AI insights
            if predictions.get('insights'):
                st.markdown("#### 💡 AI Insights")
                for insight in predictions['insights']:
                    st.info(insight)
            
            # Monthly prediction
            if predictions.get('monthly_prediction') and predictions['monthly_prediction']['prediction']:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Next Month Prediction",
                        f"₹{predictions['monthly_prediction']['prediction']:,.0f}",
                        f"Confidence: {predictions['monthly_prediction']['confidence']*100:.0f}%"
                    )
                
                with col2:
                    st.metric(
                        "Spending Trend",
                        predictions['monthly_prediction']['trend'].title(),
                        f"₹{predictions['monthly_prediction']['avg_monthly_change']:,.0f}/month"
                    )
                
                with col3:
                    historical_avg = predictions['monthly_prediction']['historical_average']
                    predicted = predictions['monthly_prediction']['prediction']
                    change_pct = ((predicted - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0
                    st.metric(
                        "vs Historical Average",
                        f"₹{historical_avg:,.0f}",
                        f"{change_pct:+.1f}%"
                    )
            
            # Category predictions
            if predictions.get('category_predictions'):
                st.markdown("#### 📊 Next 30 Days Category Predictions")
                
                cat_pred_df = pd.DataFrame(predictions['category_predictions'])
                if not cat_pred_df.empty:
                    # Create bar chart
                    fig = px.bar(
                        cat_pred_df,
                        x='category',
                        y='predicted_amount',
                        title='Predicted Spending by Category (Next 30 Days)',
                        color='predicted_amount',
                        color_continuous_scale='Blues'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show prediction details
                    with st.expander("View Detailed Predictions"):
                        for pred in predictions['category_predictions']:
                            st.write(f"**{pred['category']}**: ₹{pred['predicted_amount']:,.0f} "
                                   f"({pred['predicted_transactions']} transactions expected)")
        
        # Add a warning if user is predicted to exceed budget
        budget_response = requests.get(f"{BASE_URL}/budgets/status", headers=headers)
        if budget_response.status_code == 200 and predictions_response.status_code == 200:
            budget_statuses = budget_response.json()
            category_predictions = predictions.get('category_predictions', [])
            
            for budget in budget_statuses:
                # Find matching prediction
                pred = next((p for p in category_predictions if p['category'] == budget['category_name']), None)
                if pred and pred['predicted_amount'] > budget['remaining_amount']:
                    st.warning(f"⚠️ **Budget Alert**: You're predicted to exceed your {budget['category_name']} "
                             f"budget by ₹{pred['predicted_amount'] - budget['remaining_amount']:,.0f} this month!")

    
        # Transactions Tab
        # Transactions Tab - Update the Add Transaction form
    with tab2:
        st.markdown("### 💳 Recent Transactions")
        
        # Add transaction form
        with st.expander("➕ Add Manual Transaction"):
            col1, col2, col3 = st.columns(3)
            with col1:
                amount = st.number_input("Amount", min_value=0.0, step=0.01)
                description = st.text_input("Description")
                
            with col2:
                # Currency selection
                currencies = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "CAD", "AUD", "JPY"]
                selected_currency = st.selectbox("Currency", currencies, index=0)
                trans_type = st.selectbox("Type", ["expense", "income"])
                
            with col3:
                # Initialize selected_cat_id
                selected_cat_id = None
                
                # Get categories
                try:
                    cat_response = requests.get(f"{BASE_URL}/categories/", headers=headers, timeout=5)
                    if cat_response.status_code == 200:
                        categories = cat_response.json()
                        if categories:
                            cat_names = [cat['name'] for cat in categories]
                            
                            # For income transactions, default to "Others" or "Income" category
                            if trans_type == "income":
                                if "Income" in cat_names:
                                    default_index = cat_names.index("Income")
                                elif "Others" in cat_names:
                                    default_index = cat_names.index("Others")
                                else:
                                    default_index = 0
                            else:
                                default_index = 0
                            
                            selected_cat = st.selectbox("Category", cat_names, index=default_index)
                            
                            # Get the category ID
                            for cat in categories:
                                if cat['name'] == selected_cat:
                                    selected_cat_id = cat['id']
                                    break
                            
                            if not selected_cat_id:
                                st.error("Category not found!")
                        else:
                            st.warning("No categories found. Please create some categories first.")
                    elif cat_response.status_code == 401:
                        st.error("Authentication failed. Please login again.")
                    else:
                        st.error(f"Failed to load categories (Status: {cat_response.status_code})")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API. Please start the backend server.")
                except Exception as e:
                    st.error(f"Error loading categories: {str(e)}")
                
                trans_date = st.date_input("Date", datetime.now())
            
            # Show conversion if not INR
            if selected_currency != "INR" and amount > 0:
                convert_response = requests.post(
                    f"{BASE_URL}/currency/convert",
                    params={
                        "amount": amount,
                        "from_currency": selected_currency,
                        "to_currency": "INR"
                    },
                    headers=headers
                )
                if convert_response.status_code == 200:
                    conversion = convert_response.json()
                    st.info(f"💱 Converts to ₹{conversion['converted_amount']:,.2f} @ {conversion['exchange_rate']:.4f}")
            
            if st.button("Add Transaction"):
                if selected_cat_id is not None and amount > 0:  # Check if category ID exists
                    trans_data = {
                        "amount": amount,
                        "currency": selected_currency,
                        "description": description,
                        "category_id": selected_cat_id,
                        "transaction_date": trans_date.isoformat() + "T00:00:00",
                        "transaction_type": trans_type,
                        "source": "manual"
                    }
                    response = requests.post(f"{BASE_URL}/transactions/", json=trans_data, headers=headers)
                    if response.status_code == 200:
                        st.success("Transaction added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to add transaction: {response.text}")
                else:
                    st.error("Please fill all required fields")

        
        # Update transaction display to show currency
        trans_response = requests.get(f"{BASE_URL}/transactions/", headers=headers)
        if trans_response.status_code == 200:
            transactions = trans_response.json()
            if transactions:
                trans_data = []
                for trans in transactions:
                    # Parse date
                    try:
                        date_obj = datetime.fromisoformat(trans['transaction_date'].replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        formatted_date = trans['transaction_date'][:10]
                    
                    # Format amount with currency
                    currency = trans.get('currency', 'INR')
                    currency_symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency)
                    amount_display = f"{currency_symbol}{trans['amount']:,.2f}"
                    
                    # Show INR equivalent if different currency
                    if currency != "INR" and trans.get('amount_inr'):
                        amount_display += f" (₹{trans['amount_inr']:,.2f})"
                    
                    trans_data.append({
                        'Date': formatted_date,
                        'Description': trans['description'],
                        'Amount': amount_display,
                        'Type': trans['transaction_type'],
                        'Source': trans['source']
                    })
                
                df_display = pd.DataFrame(trans_data)
                st.dataframe(df_display, use_container_width=True)

    
    # Analytics Tab
    with tab3:
        st.markdown("### 📈 Detailed Analytics")
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        # Filtered analytics
        if st.button("Update Analytics"):
            params = {
                "start_date": start_date.isoformat() + "T00:00:00",
                "end_date": end_date.isoformat() + "T23:59:59"
            }
            filtered_response = requests.get(
                f"{BASE_URL}/analytics/spending-by-category",
                params=params,
                headers=headers
            )
            if filtered_response.status_code == 200:
                filtered_data = filtered_response.json()
                if filtered_data:
                    df_filtered = pd.DataFrame(filtered_data)
                    fig = px.bar(df_filtered, x='category', y='amount', title='Spending by Category (Filtered)')
                    st.plotly_chart(fig, use_container_width=True)
    
    # AI Assistant Tab
    with tab4:
        st.markdown("### 🤖 AI Financial Assistant")
        st.markdown("Ask me anything about your finances!")
        
        # Natural language query
        user_query = st.text_input("Your question:", placeholder="e.g., How much did I spend this month?")
        
        if st.button("Ask AI"):
            if user_query:
                response = requests.post(
                    f"{BASE_URL}/query",
                    data={"query": user_query},
                    headers=headers
                )
                if response.status_code == 200:
                    result = response.json()
                    st.markdown(f"**Answer:** {result['answer']}")
                    if result.get('data'):
                        st.json(result['data'])
        
                # Parse SMS
                # Parse SMS section in AI Assistant tab
        st.markdown("---")
        st.markdown("### 📱 Parse SMS Transaction")
        sms_text = st.text_area("Paste your bank SMS here:")

        if st.button("Parse SMS"):
            if sms_text:
                try:
                    response = requests.post(
                        f"{BASE_URL}/transactions/parse-sms",
                        data={"sms_text": sms_text},
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success("SMS parsed successfully!")
                        st.json(result['parsed_data'])
                        st.info(f"Category: {result['category']} (Confidence: {result['confidence']:.2%})")
                        
                        # Show transaction details
                        parsed = result['parsed_data']
                        if parsed.get('amount'):
                            st.success(f"✅ Transaction created: ₹{parsed['amount']:,.2f}")
                    elif response.status_code == 400:
                        st.error("Could not extract transaction details from this SMS")
                        st.info("Make sure the SMS contains amount information")
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Error parsing SMS: {str(e)}")
            else:
                st.warning("Please paste an SMS to parse")

    
    # Import Tab
    with tab5:
        st.markdown("### 📤 Import Transactions")
        
        # File upload options
        upload_type = st.selectbox("Select import type:", ["CSV", "PDF Bank Statement", "Receipt Image (OCR)"])
        
        if upload_type == "CSV":
            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
            if uploaded_file:
                if st.button("Import CSV"):
                    files = {"file": uploaded_file}
                    response = requests.post(
                        f"{BASE_URL}/import/csv",
                        files=files,
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(result['message'])
        
        elif upload_type == "PDF Bank Statement":
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
            if uploaded_file:
                if st.button("Import PDF"):
                    files = {"file": uploaded_file}
                    response = requests.post(
                        f"{BASE_URL}/transactions/upload-pdf",
                        files=files,
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(result['message'])
        
        else:  # Receipt Image OCR
            st.markdown("#### 📸 Upload Receipt Image")
            st.info("Upload a photo of your receipt and we'll extract the transaction details automatically!")
            
            uploaded_file = st.file_uploader(
                "Choose a receipt image", 
                type=["jpg", "jpeg", "png", "bmp"],
                help="Take a clear photo of your receipt with good lighting"
            )
            
            if uploaded_file:
                # Show preview
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### Receipt Preview")
                    st.image(uploaded_file, use_column_width=True)
                
                with col2:
                    st.markdown("##### Processing")
                    
                    if st.button("🔍 Extract Transaction from Receipt", key="process_receipt"):
                        with st.spinner("Processing receipt..."):
                            try:
                                # Reset file pointer
                                uploaded_file.seek(0)
                                
                                # Send to API
                                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                                response = requests.post(
                                    f"{BASE_URL}/transactions/upload-receipt",
                                    files=files,
                                    headers=headers
                                )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    st.success("✅ " + result['message'])
                                    
                                    # Show extracted data
                                    st.markdown("##### Extracted Information")
                                    parsed = result['parsed_data']
                                    
                                    st.write(f"**Amount:** ₹{parsed['amount']:,.2f}")
                                    st.write(f"**Merchant:** {parsed['merchant']}")
                                    st.write(f"**Category:** {result['category']} (Confidence: {result['confidence']:.1%})")
                                    
                                    if parsed.get('date'):
                                        st.write(f"**Date:** {parsed['date']}")
                                    
                                    if parsed.get('items'):
                                        with st.expander("View Items"):
                                            for item in parsed['items']:
                                                st.write(f"- {item['name']}: ₹{item['price']}")
                                    
                                    st.balloons()
                                    
                                else:
                                    error_detail = response.json().get('detail', 'Unknown error')
                                    st.error(f"Failed to process receipt: {error_detail}")
                                    
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
            
            # Tips for better OCR
            with st.expander("📌 Tips for Better Results"):
                st.markdown("""
                - **Good Lighting**: Take photo in well-lit area
                - **Clear Focus**: Make sure text is sharp and readable
                - **Full Receipt**: Include the entire receipt in frame
                - **Flat Surface**: Place receipt on flat surface
                - **Avoid Shadows**: Minimize shadows on receipt
                """)





    # Add Budget Management Tab (add this after the Import tab code):
    with tab6:
        st.markdown("### 💰 Budget Management")
        
        # Create two columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Set Budget")
            
            # Get categories for dropdown
            cat_response = requests.get(f"{BASE_URL}/categories/", headers=headers)
            if cat_response.status_code == 200:
                categories = cat_response.json()
                category_names = [cat['name'] for cat in categories]
                
                # Budget form
                selected_category = st.selectbox("Category", category_names, key="budget_category")
                selected_cat_id = next(cat['id'] for cat in categories if cat['name'] == selected_category)
                
                budget_amount = st.number_input("Monthly Budget (₹)", min_value=0.0, step=100.0, key="budget_amount")
                alert_threshold = st.slider("Alert when spent (%)", min_value=50, max_value=100, value=80, key="alert_threshold")
                
                if st.button("Set Budget", key="set_budget_btn"):
                    if budget_amount > 0:
                        budget_data = {
                            "category_id": selected_cat_id,
                            "amount": budget_amount,
                            "period": "monthly",
                            "alert_threshold": alert_threshold / 100
                        }
                        
                        response = requests.post(
                            f"{BASE_URL}/budgets/",
                            json=budget_data,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            st.success(f"Budget set for {selected_category}: ₹{budget_amount:,.2f}")
                            st.rerun()
                        else:
                            st.error("Failed to set budget")
        
        with col2:
            st.markdown("#### 🚨 Recent Alerts")
            
            # Get alerts
            alerts_response = requests.get(f"{BASE_URL}/alerts/", headers=headers)
            if alerts_response.status_code == 200:
                alerts = alerts_response.json()
                
                if alerts:
                    for alert in alerts[:5]:  # Show latest 5 alerts
                        alert_color = "🔴" if alert['alert_type'] == "budget_exceed" else "🟡"
                        with st.expander(f"{alert_color} {alert['title']}", expanded=not alert['is_read']):
                            st.write(alert['message'])
                            st.caption(f"Date: {alert['created_at'][:10]}")
                            
                            if not alert['is_read']:
                                if st.button(f"Mark as read", key=f"read_{alert['id']}"):
                                    requests.put(
                                        f"{BASE_URL}/alerts/{alert['id']}/read",
                                        headers=headers
                                    )
                                    st.rerun()
                else:
                    st.info("No alerts yet. Set budgets to get spending alerts!")
        
        # Budget Status Section
        st.markdown("---")
        st.markdown("### 📊 Budget Status")
        
        # Get budget status
        status_response = requests.get(f"{BASE_URL}/budgets/status", headers=headers)
        if status_response.status_code == 200:
            budget_statuses = status_response.json()
        else:
            budget_statuses = []
            
            if budget_statuses:
                # Create columns for budget cards
                cols = st.columns(3)
                
                for idx, status in enumerate(budget_statuses):
                    with cols[idx % 3]:
                        # Determine color based on status
                        if status['status'] == 'exceeded':
                            color = "#FF4B4B"
                        elif status['status'] == 'warning':
                            color = "#FFA500"
                        else:
                            color = "#00CC88"
                        
                        # Create budget card
                        st.markdown(f"""
                            <div style='padding: 1rem; border-radius: 0.5rem; border: 2px solid {color}; margin-bottom: 1rem;'>
                                <h4 style='margin: 0; color: {color};'>{status['category_name']}</h4>
                                <p style='margin: 0.5rem 0; font-size: 1.2rem;'>₹{status['spent_amount']:,.0f} / ₹{status['budget_amount']:,.0f}</p>
                                <p style='margin: 0; font-size: 0.9rem;'>{status['percentage_used']:.1f}% used</p>
                                <p style='margin: 0; font-size: 0.8rem; color: gray;'>{status['days_left']} days left</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Progress bar
                        st.progress(min(status['percentage_used'] / 100, 1.0))
            else:
                st.info("No budgets set yet. Create budgets above to track your spending!")
        
        # Budget vs Actual Chart
        if budget_statuses:
            st.markdown("### 📈 Budget vs Actual Spending")
            
            # Prepare data for chart
            budget_df = pd.DataFrame(budget_statuses)
            
            # Create bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Budget',
                x=budget_df['category_name'],
                y=budget_df['budget_amount'],
                marker_color='lightblue'
            ))
            
            fig.add_trace(go.Bar(
                name='Spent',
                x=budget_df['category_name'],
                y=budget_df['spent_amount'],
                marker_color=budget_df['status'].map({
                    'safe': 'lightgreen',
                    'warning': 'orange',
                    'exceeded': 'red'
                })
            ))
            
            fig.update_layout(
                title='Budget vs Actual Spending',
                xaxis_title='Category',
                yaxis_title='Amount (₹)',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)


    with tab7:
        st.markdown("### 💱 Currency Exchange")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Currency Converter")
            
            # Converter form
            conv_amount = st.number_input("Amount to convert", min_value=0.0, value=100.0, step=10.0)
            
            col_from, col_to = st.columns(2)
            with col_from:
                from_curr = st.selectbox("From", ["INR", "USD", "EUR", "GBP", "AED", "SGD"], key="from_curr")
            with col_to:
                to_curr = st.selectbox("To", ["INR", "USD", "EUR", "GBP", "AED", "SGD"], index=1, key="to_curr")
            
            if st.button("Convert", key="convert_btn"):
                if conv_amount > 0:
                    response = requests.post(
                        f"{BASE_URL}/currency/convert",
                        params={
                            "amount": conv_amount,
                            "from_currency": from_curr,
                            "to_currency": to_curr
                        },
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"{from_curr} {conv_amount:,.2f} = {to_curr} {result['converted_amount']:,.2f}")
                        st.info(f"Exchange Rate: 1 {from_curr} = {result['exchange_rate']:.4f} {to_curr}")
        
        with col2:
            st.markdown("#### Current Exchange Rates")
            
            base_currency = st.selectbox("Base Currency", ["INR", "USD", "EUR", "GBP"], key="base_curr")
            
            rates_response = requests.get(
                f"{BASE_URL}/currency/rates",
                params={"base_currency": base_currency},
                headers=headers
            )
            
            if rates_response.status_code == 200:
                rates_data = rates_response.json()
                rates = rates_data['rates']
                
                # Display rates
                st.markdown(f"**1 {base_currency} equals:**")
                for curr, rate in rates.items():
                    if curr != base_currency:
                        st.write(f"• {curr}: {rate:.4f}")

if not st.session_state.token:
    # Not logged in
    st.markdown('<h1 class="main-header">💰 AI Finance Assistant</h1>', unsafe_allow_html=True)
    st.markdown("### Welcome! Please login or register to continue.")
    
    # Features
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 🤖 AI-Powered")
        st.write("Smart categorization and insights using machine learning")
    with col2:
        st.markdown("#### 📊 Analytics")
        st.write("Detailed spending analysis and trends")
    with col3:
        st.markdown("#### 📱 SMS Parsing")
        st.write("Automatic transaction extraction from bank SMS")
