from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
import json

from ..database.database import get_db
from ..database import models, schemas
from ..api.simple_auth import get_current_user, create_access_token, authenticate_user, get_password_hash
from ..parsers.sms_parser import SMSParser
from ..parsers.pdf_parser import PDFStatementParser
from ..ml.categorizer import TransactionCategorizer
from ..services.analytics import AnalyticsService
from ..services.budget_service import BudgetService
from ..services.prediction_service import PredictionService
# from ..parsers.receipt_parser import ReceiptParser
from ..services.currency_service import CurrencyService

router = APIRouter()
currency_service = CurrencyService()

@router.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {"message": "API is working!"}

@router.post("/simple-register")
def simple_register(email: str, username: str, password: str, db: Session = Depends(get_db)):
    """Simplified registration for debugging"""
    try:
        # Check if user exists
        existing_user = db.query(models.User).filter(
            (models.User.email == email) | (models.User.username == username)
        ).first()
        
        if existing_user:
            return {"error": "User already exists"}
        
        # Create user
        hashed_pw = get_password_hash(password)
        new_user = models.User(
            email=email,
            username=username,
            hashed_password=hashed_pw
        )
        db.add(new_user)
        db.commit()
        
        return {"message": "User created successfully", "user_id": new_user.id}
        
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}



# Initialize services
sms_parser = SMSParser()
pdf_parser = PDFStatementParser()
categorizer = TransactionCategorizer()

# Authentication endpoints
@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    print(f"Registration attempt - Email: {user.email}, Username: {user.username}")
    
    # Check if user exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    
    if db_user:
        print(f"User already exists - Email: {db_user.email}, Username: {db_user.username}")
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    try:
        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"User created successfully - ID: {db_user.id}")
        
        # Create default categories for user
        default_categories = categorizer.categories
        for cat_name in default_categories:
            category = models.Category(
                name=cat_name,
                user_id=db_user.id,
                is_default=True
            )
            db.add(category)
        db.commit()
        print(f"Created {len(default_categories)} default categories")
        
        return db_user
        
    except Exception as e:
        print(f"Error during registration: {type(e).__name__} - {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login and get access token"""
    print(f"Login attempt - Username: {username}")
    
    user = authenticate_user(db, username, password)
    if not user:
        print(f"Login failed - User not found or wrong password")
        # Let's check if user exists
        user_check = db.query(models.User).filter(models.User.username == username).first()
        if user_check:
            print(f"User exists in DB: {user_check.username}, Email: {user_check.email}")
        else:
            print("User not found in database")
        
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    print(f"Login successful for user: {user.username}")
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Transaction endpoints
@router.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a manual transaction with currency support"""
    # Convert to INR if different currency
    amount_inr = transaction.amount
    exchange_rate = 1.0
    
    if transaction.currency != "INR":
        amount_inr = currency_service.convert_to_inr(transaction.amount, transaction.currency)
        rates = currency_service.get_exchange_rates(transaction.currency)
        exchange_rate = rates.get("INR", 1.0)
    
    db_transaction = models.Transaction(
        user_id=current_user.id,
        amount=transaction.amount,
        currency=transaction.currency,
        amount_inr=amount_inr,
        exchange_rate=exchange_rate,
        description=transaction.description,
        category_id=transaction.category_id,
        transaction_date=transaction.transaction_date,
        transaction_type=transaction.transaction_type,
        source=transaction.source
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Check budget (using INR amount)
    if transaction.transaction_type == "expense":
        budget_service = BudgetService(db)
        alert = budget_service.check_budget_alert(current_user.id, transaction.category_id)
        if alert:
            print(f"Budget alert created: {alert.title}")
    
    return db_transaction


@router.get("/transactions/", response_model=List[schemas.TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's transactions"""
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return transactions

@router.post("/transactions/parse-sms")
def parse_sms_transactions(
    sms_text: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse SMS and create transaction"""
    try:
        # Parse SMS
        parsed = sms_parser.parse_sms(sms_text)
        
        if not parsed['amount']:
            raise HTTPException(status_code=400, detail="Could not extract transaction amount from SMS")
        
        # Get category prediction - Handle None merchant
        description = parsed.get('merchant') or 'Unknown Transaction'
        if not description:
            description = 'Unknown Transaction'
            
        category_name, confidence = categorizer.predict(description)
        
        # Find category
        category = db.query(models.Category).filter(
            models.Category.name == category_name,
            models.Category.user_id == current_user.id
        ).first()
        
        # If category not found, use default "Others" category
        if not category:
            category = db.query(models.Category).filter(
                models.Category.name == "Others",
                models.Category.user_id == current_user.id
            ).first()
            
            # If still no category, create it
            if not category:
                category = models.Category(
                    name="Others",
                    user_id=current_user.id,
                    is_default=True
                )
                db.add(category)
                db.commit()
                db.refresh(category)
        
        # Handle date
        if parsed['date']:
            try:
                transaction_date = datetime.strptime(parsed['date'], '%Y-%m-%d')
            except:
                transaction_date = datetime.now()
        else:
            transaction_date = datetime.now()
        
        # Handle currency and conversion
        currency = parsed.get('currency', 'INR')
        amount = parsed['amount']
        amount_inr = amount
        exchange_rate = 1.0
        
        if currency != 'INR':
            amount_inr = currency_service.convert_to_inr(amount, currency)
            rates = currency_service.get_exchange_rates(currency)
            exchange_rate = rates.get('INR', 1.0)
        
        # Create transaction
        transaction = models.Transaction(
            user_id=current_user.id,
            amount=amount,
            currency=currency,
            amount_inr=amount_inr,
            exchange_rate=exchange_rate,
            description=description,
            category_id=category.id,
            transaction_type='expense' if parsed.get('type') == 'debit' else 'income',
            transaction_date=transaction_date,
            source='bank_sms',
            raw_text=sms_text
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # Initialize alert variable
        alert = None
        
        # Check budget for expense transactions
        if transaction.transaction_type == "expense":
            budget_service = BudgetService(db)
            alert = budget_service.check_budget_alert(current_user.id, transaction.category_id)
            if alert:
                print(f"Budget alert created: {alert.title}")
        
        return {
            "transaction_id": transaction.id,
            "parsed_data": parsed,
            "category": category_name,
            "confidence": confidence,
            "budget_alert": alert.title if alert else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in SMS parsing: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")



@router.post("/transactions/upload-pdf")
async def upload_pdf_statement(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse PDF bank statement"""
    # Save uploaded file temporarily
    temp_path = f"temp_{current_user.id}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    try:
        # Parse PDF
        df = pdf_parser.parse_statement(temp_path)
        
        # Process transactions
        created_transactions = []
        for _, row in df.iterrows():
            # Get category prediction
            description = row.get('description', 'Transaction')
            category_name, _ = categorizer.predict(description)
            
            # Find category
            category = db.query(models.Category).filter(
                models.Category.name == category_name,
                models.Category.user_id == current_user.id
            ).first()
            
            # Determine transaction type and amount
            amount = row.get('amount', 0)
            if 'debit' in row and row['debit']:
                amount = row['debit']
                trans_type = 'expense'
            elif 'credit' in row and row['credit']:
                amount = row['credit']
                trans_type = 'income'
            else:
                trans_type = 'expense' if amount > 0 else 'income'
                amount = abs(amount)
            
            # Create transaction
            transaction = models.Transaction(
                user_id=current_user.id,
                amount=amount,
                description=description,
                category_id=category.id if category else None,
                transaction_type=trans_type,
                transaction_date=row.get('date', datetime.now()),
                source='pdf',
                raw_text=str(row.to_dict())
            )
            
            db.add(transaction)
            created_transactions.append(transaction)
        
        db.commit()
        
        return {
            "message": f"Successfully imported {len(created_transactions)} transactions",
            "count": len(created_transactions)
        }
        
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Analytics endpoints
@router.get("/analytics/spending-by-category")
def get_spending_by_category(
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get spending breakdown by category"""
    analytics = AnalyticsService(db)
    return analytics.get_spending_by_category(current_user.id, start_date, end_date)

@router.get("/analytics/monthly-trend")
def get_monthly_trend(
    months: int = 6,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly income/expense trend"""
    analytics = AnalyticsService(db)
    return analytics.get_monthly_trend(current_user.id, months)

@router.get("/analytics/insights")
def get_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated financial insights"""
    analytics = AnalyticsService(db)
    return analytics.get_insights(current_user.id)

# Category endpoints
@router.get("/categories/", response_model=List[schemas.CategoryResponse])
def get_categories(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's categories"""
    categories = db.query(models.Category).filter(
        models.Category.user_id == current_user.id
    ).all()
    return categories

@router.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(
    category: schemas.CategoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a custom category"""
    db_category = models.Category(
        **category.dict(),
        user_id=current_user.id,
        is_default=False
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# Natural Language Query endpoint
@router.post("/query")
def natural_language_query(
    query: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle natural language queries about finances"""
    query_lower = query.lower()
    
    # Get current month date range
    now = datetime.now()
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate common values once
    income_total = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.transaction_type == 'income',
        models.Transaction.transaction_date >= start_date
    ).scalar() or 0
    
    expense_total = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.transaction_type == 'expense',
        models.Transaction.transaction_date >= start_date
    ).scalar() or 0
    
    # Check queries in specific order (most specific first)
    
    # Percentage queries
    if "percentage" in query_lower or "percent" in query_lower or "%" in query_lower:
        if income_total > 0:
            percentage = (expense_total / income_total) * 100
            savings_rate = 100 - percentage
            return {
                "query": query,
                "answer": f"You're spending {percentage:.1f}% of your income. Savings rate: {savings_rate:.1f}%",
                "data": {
                    "income": income_total,
                    "expenses": expense_total,
                    "spending_percentage": percentage,
                    "savings_rate": savings_rate
                }
            }
        else:
            return {
                "query": query,
                "answer": "No income recorded this month to calculate percentage.",
                "data": None
            }
    
    # Income vs Expenses comparison
    elif ("income" in query_lower and "expense" in query_lower) or "vs" in query_lower or "versus" in query_lower:
        balance = income_total - expense_total
        status = "surplus" if balance > 0 else "deficit"
        
        return {
            "query": query,
            "answer": f"Income vs Expenses:\n• Income: ₹{income_total:,.2f}\n• Expenses: ₹{expense_total:,.2f}\n• Net {status}: ₹{abs(balance):,.2f}",
            "data": {
                "income": income_total,
                "expenses": expense_total,
                "balance": balance,
                "status": status
            }
        }
    
    # Spending queries
    elif "spent" in query_lower and ("month" in query_lower or "total" in query_lower):
        count = db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.transaction_type == 'expense',
            models.Transaction.transaction_date >= start_date
        ).count()
        
        return {
            "query": query,
            "answer": f"You have spent ₹{expense_total:,.2f} this month across {count} transactions.",
            "data": {"total_spending": expense_total, "transaction_count": count}
        }
    
    # Income/Earning queries
    elif "earn" in query_lower or ("income" in query_lower and "how much" in query_lower):
        income_count = db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.transaction_type == 'income',
            models.Transaction.transaction_date >= start_date
        ).count()
        
        return {
            "query": query,
            "answer": f"You have earned ₹{income_total:,.2f} this month from {income_count} income source(s).",
            "data": {"total_income": income_total, "income_count": income_count}
        }
    
    # Savings queries
    elif "save" in query_lower or "saving" in query_lower:
        savings = income_total - expense_total
        savings_rate = (savings / income_total * 100) if income_total > 0 else 0
        
        return {
            "query": query,
            "answer": f"Your current month savings: ₹{savings:,.2f} ({savings_rate:.1f}% of income)\n• Income: ₹{income_total:,.2f}\n• Expenses: ₹{expense_total:,.2f}",
            "data": {
                "income": income_total,
                "expenses": expense_total,
                "savings": savings,
                "savings_rate": savings_rate
            }
        }
    
    # Category queries
    elif "category" in query_lower or "most" in query_lower:
        analytics = AnalyticsService(db)
        spending = analytics.get_spending_by_category(current_user.id, start_date)
        if spending:
            top = max(spending, key=lambda x: x['amount'])
            return {
                "query": query,
                "answer": f"Your highest spending category is {top['category']} with ₹{top['amount']:,.2f} ({top['percentage']:.1f}% of total spending).",
                "data": top
            }
        else:
            return {
                "query": query,
                "answer": "You haven't made any expense transactions yet.",
                "data": None
            }
    
    # Net balance queries
    elif "balance" in query_lower or "left" in query_lower or "remaining" in query_lower:
        balance = income_total - expense_total
        
        return {
            "query": query,
            "answer": f"Your net balance this month: ₹{balance:,.2f}\n(₹{income_total:,.2f} earned - ₹{expense_total:,.2f} spent)",
            "data": {
                "income": income_total,
                "expenses": expense_total,
                "balance": balance
            }
        }
    
    # Specific category spending (food, shopping, etc.)
    elif any(cat.lower() in query_lower for cat in ["food", "dining", "shopping", "entertainment", "transport", "bills"]):
        # Find which category was mentioned
        category_map = {
            "food": "Food & Dining",
            "dining": "Food & Dining",
            "shopping": "Shopping",
            "entertainment": "Entertainment",
            "transport": "Transportation",
            "bills": "Bills & Utilities"
        }
        
        mentioned_cat = None
        for key, value in category_map.items():
            if key in query_lower:
                mentioned_cat = value
                break
        
        if mentioned_cat:
            cat_total = db.query(func.sum(models.Transaction.amount)).join(
                models.Category
            ).filter(
                models.Transaction.user_id == current_user.id,
                models.Transaction.transaction_type == 'expense',
                models.Category.name == mentioned_cat,
                models.Transaction.transaction_date >= start_date
            ).scalar() or 0
            
            return {
                "query": query,
                "answer": f"You have spent ₹{cat_total:,.2f} on {mentioned_cat} this month.",
                "data": {"category": mentioned_cat, "amount": cat_total}
            }
    
    # Default response
    else:
        return {
            "query": query,
            "answer": "I can help you with questions like:\n• How much did I spend this month?\n• How much did I earn this month?\n• What's my income vs expenses?\n• What percentage of income am I spending?\n• Am I saving money?\n• What's my net balance?\n• What's my top spending category?\n• How much did I spend on food/shopping/entertainment?",
            "data": None
        }


# Import from various sources
@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import transactions from CSV file"""
    import csv
    import io
    
    content = await file.read()
    decoded = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(decoded))
    
    transactions_created = 0
    for row in csv_reader:
        # Map CSV columns to transaction fields
        amount = float(row.get('amount', row.get('Amount', 0)))
        description = row.get('description', row.get('Description', 'Imported transaction'))
        date_str = row.get('date', row.get('Date', ''))
        
        # Parse date
        try:
            trans_date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            trans_date = datetime.now()
        
        # Predict category
        category_name, _ = categorizer.predict(description)
        category = db.query(models.Category).filter(
            models.Category.name == category_name,
            models.Category.user_id == current_user.id
        ).first()
        
        # Determine transaction type
        trans_type = row.get('type', 'expense')
        if 'credit' in description.lower() or 'deposit' in description.lower():
            trans_type = 'income'
        
        # Create transaction
        transaction = models.Transaction(
            user_id=current_user.id,
            amount=abs(amount),
            description=description,
            category_id=category.id if category else None,
            transaction_type=trans_type,
            transaction_date=trans_date,
            source='csv',
            raw_text=json.dumps(row)
        )
        
        db.add(transaction)
        transactions_created += 1
    
    db.commit()
    
    return {
        "message": f"Successfully imported {transactions_created} transactions from CSV",
        "count": transactions_created
    }

# Budget management
@router.post("/budget/set")
def set_budget(
    category_id: int = Form(...),
    amount: float = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set budget for a category"""
    # Verify category belongs to user
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # In a real app, you'd have a Budget model
    # For now, return a simple response
    return {
        "message": f"Budget set for {category.name}: ₹{amount:,.2f}",
        "category": category.name,
        "budget_amount": amount
    }

@router.get("/export/transactions")
def export_transactions(
    format: str = "csv",  # csv or json
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export user's transactions"""
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    ).all()
    
    if format == "json":
        return [{
            "id": t.id,
            "date": t.transaction_date.isoformat(),
            "description": t.description,
            "amount": t.amount,
            "type": t.transaction_type,
            "category": t.category.name if t.category else None
        } for t in transactions]
    
    else:  # CSV format
        import io
        import csv
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Date", "Description", "Amount", "Type", "Category"])
        
        # Data
        for t in transactions:
            writer.writerow([
                t.transaction_date.strftime('%Y-%m-%d'),
                t.description,
                t.amount,
                t.transaction_type,
                t.category.name if t.category else ""
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"}
        )



# Budget Management Endpoints
@router.post("/budgets/", response_model=schemas.BudgetResponse)
def create_budget(
    budget: schemas.BudgetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update budget for a category"""
    # Check if budget already exists
    existing = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.category_id == budget.category_id,
        models.Budget.is_active == True
    ).first()
    
    if existing:
        # Update existing budget
        existing.amount = budget.amount
        existing.period = budget.period
        existing.alert_threshold = budget.alert_threshold
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new budget
    db_budget = models.Budget(
        **budget.dict(),
        user_id=current_user.id
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@router.get("/budgets/", response_model=List[schemas.BudgetResponse])
def get_budgets(
    active_only: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's budgets"""
    query = db.query(models.Budget).filter(models.Budget.user_id == current_user.id)
    if active_only:
        query = query.filter(models.Budget.is_active == True)
    return query.all()

@router.get("/budgets/status", response_model=List[schemas.BudgetStatus])
def get_budgets_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of all active budgets"""
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.is_active == True
    ).all()
    
    budget_service = BudgetService(db)
    statuses = []
    
    for budget in budgets:
        status = budget_service.get_budget_status(budget.id)
        if status:
            statuses.append(status)
    
    return statuses

@router.get("/alerts/", response_model=List[schemas.AlertResponse])
def get_alerts(
    unread_only: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's alerts"""
    query = db.query(models.Alert).filter(models.Alert.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.Alert.is_read == False)
    return query.order_by(models.Alert.created_at.desc()).limit(20).all()

@router.put("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark alert as read"""
    alert = db.query(models.Alert).filter(
        models.Alert.id == alert_id,
        models.Alert.user_id == current_user.id
    ).first()
    
    if alert:
        alert.is_read = True
        db.commit()
        return {"message": "Alert marked as read"}
    
    raise HTTPException(status_code=404, detail="Alert not found")


# Import prediction service at the top
from ..services.prediction_service import PredictionService

# Prediction Endpoints
@router.get("/predictions/monthly")
def get_monthly_predictions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly spending predictions"""
    prediction_service = PredictionService(db)
    predictions = prediction_service.predict_monthly_spending(current_user.id)
    return predictions

@router.get("/predictions/category")
def get_category_predictions(
    days: int = 30,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get spending predictions by category"""
    prediction_service = PredictionService(db)
    predictions = prediction_service.predict_category_spending(current_user.id, days)
    return predictions

@router.get("/predictions/insights")
def get_ai_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered spending insights and predictions"""
    prediction_service = PredictionService(db)
    insights = prediction_service.get_spending_insights(current_user.id)
    return insights



# Initialize receipt parser
# receipt_parser = ReceiptParser()

# Receipt OCR Endpoint
@router.post("/transactions/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Receipt OCR temporarily disabled in production"""
    raise HTTPException(
        status_code=503, 
        detail="Receipt OCR is temporarily disabled in production deployment"
    )
# @router.post("/transactions/upload-receipt")
# async def upload_receipt(
#     file: UploadFile = File(...),
#     current_user: models.User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Upload and parse receipt image"""
#     # Validate file type
#     if not file.content_type.startswith('image/'):
#         raise HTTPException(status_code=400, detail="Please upload an image file")
    
#     try:
#         # Read image
#         contents = await file.read()
        
#         # Parse receipt
#         result = receipt_parser.parse_receipt(contents)
        
#         if not result['success']:
#             raise HTTPException(status_code=400, detail=result.get('error', 'Failed to parse receipt'))
        
#         if not result['amount']:
#             raise HTTPException(status_code=400, detail="Could not extract amount from receipt")
        
#         # Predict category
#         merchant = result.get('merchant', 'Receipt Transaction')
#         category_name, confidence = categorizer.predict(merchant)
        
#         # Find or create category
#         category = db.query(models.Category).filter(
#             models.Category.name == category_name,
#             models.Category.user_id == current_user.id
#         ).first()
        
#         if not category:
#             category = db.query(models.Category).filter(
#                 models.Category.name == "Others",
#                 models.Category.user_id == current_user.id
#             ).first()
        
#         # Create transaction
#         transaction = models.Transaction(
#             user_id=current_user.id,
#             amount=result['amount'],
#             description=f"{merchant} - Receipt",
#             category_id=category.id if category else None,
#             transaction_type='expense',
#             transaction_date=datetime.now(),  # Could parse from receipt if available
#             source='receipt_ocr',
#             raw_text=result['raw_text'][:1000]  # Store first 1000 chars
#         )
        
#         db.add(transaction)
#         db.commit()
#         db.refresh(transaction)
        
#         # Check budget
#         if category:
#             budget_service = BudgetService(db)
#             alert = budget_service.check_budget_alert(current_user.id, category.id)
        
#         return {
#             "transaction_id": transaction.id,
#             "parsed_data": {
#                 "amount": result['amount'],
#                 "merchant": result['merchant'],
#                 "items": result.get('items', []),
#                 "date": result.get('date')
#             },
#             "category": category_name,
#             "confidence": confidence,
#             "message": f"Receipt processed successfully. Transaction of ₹{result['amount']:,.2f} created."
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"Receipt processing error: {e}")
#         raise HTTPException(status_code=500, detail=f"Error processing receipt: {str(e)}")
    
# Currency Endpoints
@router.get("/currency/rates")
def get_exchange_rates(
    base_currency: str = "INR",
    current_user: models.User = Depends(get_current_user)
):
    """Get current exchange rates"""
    rates = currency_service.get_exchange_rates(base_currency)
    return {
        "base_currency": base_currency,
        "rates": rates,
        "last_updated": datetime.now()
    }

@router.get("/currency/supported")
def get_supported_currencies(
    current_user: models.User = Depends(get_current_user)
):
    """Get list of supported currencies"""
    return currency_service.supported_currencies

@router.post("/currency/convert")
def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    current_user: models.User = Depends(get_current_user)
):
    """Convert amount between currencies"""
    converted = currency_service.convert_currency(amount, from_currency, to_currency)
    rate = currency_service.get_exchange_rates(from_currency).get(to_currency, 1.0)
    
    return {
        "original_amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": converted,
        "exchange_rate": rate
    }