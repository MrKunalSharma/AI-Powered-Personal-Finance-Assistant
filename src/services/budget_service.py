from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta
from typing import List, Optional
from ..database.models import Budget, Transaction, Category, Alert, User
from ..database.schemas import BudgetStatus

class BudgetService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_budget_period_dates(self, period: str):
        """Get start and end date for budget period"""
        now = datetime.now()
        
        if period == "monthly":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Get last day of month
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif period == "weekly":
            # Start from Monday
            days_since_monday = now.weekday()
            start_date = now - timedelta(days=days_since_monday)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        else:  # yearly
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(month=12, day=31, hour=23, minute=59, second=59)
        
        return start_date, end_date
    
    def get_spent_amount(self, user_id: int, category_id: int, start_date: datetime, end_date: datetime) -> float:
        """Get amount spent in a category during a period"""
        return self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ).scalar() or 0
    
    def check_budget_alert(self, user_id: int, category_id: int) -> Optional[Alert]:
        """Check if budget alert should be created"""
        # Get active budget for category
        budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.is_active == True
        ).first()
        
        if not budget:
            return None
        
        # Get spending for budget period
        start_date, end_date = self.get_budget_period_dates(budget.period)
        spent = self.get_spent_amount(user_id, category_id, start_date, end_date)
        
        percentage = (spent / budget.amount) * 100 if budget.amount > 0 else 0
        
        # Check if alert needed
        if percentage >= (budget.alert_threshold * 100):
            # Check if alert already exists for this period
            existing_alert = self.db.query(Alert).filter(
                Alert.user_id == user_id,
                Alert.alert_type == "budget_exceed",
                Alert.created_at >= start_date,
                Alert.title.contains(budget.category.name)
            ).first()
            
            if not existing_alert:
                # Create alert
                status = "exceeded" if percentage >= 100 else "warning"
                alert = Alert(
                    user_id=user_id,
                    alert_type="budget_exceed",
                    title=f"{budget.category.name} Budget {status.title()}!",
                    message=f"You've spent ₹{spent:,.2f} ({percentage:.1f}%) of your ₹{budget.amount:,.2f} {budget.period} budget for {budget.category.name}."
                )
                self.db.add(alert)
                self.db.commit()
                return alert
        
        return None
    
    def get_budget_status(self, budget_id: int) -> BudgetStatus:
        """Get detailed budget status"""
        budget = self.db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            return None
        
        start_date, end_date = self.get_budget_period_dates(budget.period)
        spent = self.get_spent_amount(budget.user_id, budget.category_id, start_date, end_date)
        
        remaining = budget.amount - spent
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        days_left = (end_date - datetime.now()).days + 1
        
        # Determine status
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= budget.alert_threshold * 100:
            status = "warning"
        else:
            status = "safe"
        
        return BudgetStatus(
            budget_id=budget.id,
            category_name=budget.category.name,
            budget_amount=budget.amount,
            spent_amount=spent,
            remaining_amount=remaining,
            percentage_used=percentage,
            days_left=days_left,
            status=status
        )
