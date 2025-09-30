from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Category schemas
class CategoryBase(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    is_default: bool
    
    class Config:
        from_attributes = True

# Transaction schemas
class TransactionBase(BaseModel):
    amount: float
    currency: str = "INR"  # Add this
    description: str
    category_id: int
    transaction_date: datetime
    transaction_type: str
    source: Optional[str] = "manual"

class TransactionCreate(TransactionBase):
    raw_text: Optional[str] = None

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    amount_inr: Optional[float] = None  # Add this
    exchange_rate: Optional[float] = None  # Add this
    created_at: datetime
    category: Optional[CategoryResponse] = None
    
    class Config:
        from_attributes = True

# Analytics schemas
class SpendingByCategory(BaseModel):
    category_name: str
    total_amount: float
    percentage: float

class MonthlyTrend(BaseModel):
    month: str
    income: float
    expense: float
    savings: float

class CurrencySettingsUpdate(BaseModel):
    default_currency: str
    auto_convert: bool = True

class ExchangeRateResponse(BaseModel):
    base_currency: str
    rates: Dict[str, float]
    last_updated: datetime
    
# Budget schemas
class BudgetBase(BaseModel):
    category_id: int
    amount: float
    period: str = "monthly"
    alert_threshold: float = 0.8

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    alert_threshold: Optional[float] = None
    is_active: Optional[bool] = None

class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    category: Optional[CategoryResponse] = None
    
    class Config:
        from_attributes = True

# Budget Status
class BudgetStatus(BaseModel):
    budget_id: int
    category_name: str
    budget_amount: float
    spent_amount: float
    remaining_amount: float
    percentage_used: float
    days_left: int
    status: str  # "safe", "warning", "exceeded"
    
# Alert schemas
class AlertResponse(BaseModel):
    id: int
    alert_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
