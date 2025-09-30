from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base  # Make sure this import is correct

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")

# Add to the Transaction model (update the existing class)
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")  # Add this line
    amount_inr = Column(Float)  # Add this line - stores INR equivalent
    exchange_rate = Column(Float, default=1.0)  # Add this line
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    transaction_date = Column(DateTime, nullable=False)
    transaction_type = Column(String, nullable=False)
    source = Column(String)
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

# Add a new Currency Settings model
class CurrencySettings(Base):
    __tablename__ = "currency_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    default_currency = Column(String, default="INR")
    auto_convert = Column(Boolean, default=True)
    
    user = relationship("User", backref="currency_settings", uselist=False)


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_default = Column(Boolean, default=False)
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)
    
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    period = Column(String, default="monthly")  # monthly/weekly/yearly
    alert_threshold = Column(Float, default=0.8)  # Alert at 80% by default
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="budgets")
    category = relationship("Category", backref="budgets")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_type = Column(String, nullable=False)  # budget_exceed, unusual_spending, goal_reached
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="alerts")

