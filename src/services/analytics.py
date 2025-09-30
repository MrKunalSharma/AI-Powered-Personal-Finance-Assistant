from sqlalchemy.orm import Session
from sqlalchemy import func, extract  # Make sure func is imported here
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
from ..database.models import Transaction, Category, User


class AnalyticsService:
    """Service for financial analytics and insights"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_spending_by_category(self, user_id: int, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get spending breakdown by category"""
        
        query = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(
            Transaction
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense'
        )
        
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        
        results = query.group_by(Category.name).all()
        
        # Calculate percentages
        total_spending = sum(r.total for r in results)
        
        return [
            {
                'category': r.name,
                'amount': float(r.total),
                'percentage': (float(r.total) / total_spending * 100) if total_spending > 0 else 0
            }
            for r in results
        ]
    
    def get_monthly_trend(self, user_id: int, months: int = 6) -> List[Dict]:
        """Get monthly income/expense trend"""
        
        start_date = datetime.now() - timedelta(days=months * 30)
        
        # Query for monthly aggregates
        query = self.db.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            Transaction.transaction_type,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date
        ).group_by(
            'year', 'month', Transaction.transaction_type
        )
        
        results = query.all()
        
        # Process results into monthly summary
        monthly_data = {}
        for r in results:
            key = f"{r.year}-{r.month:02d}"
            if key not in monthly_data:
                monthly_data[key] = {'income': 0, 'expense': 0}
            
            if r.transaction_type == 'income':
                monthly_data[key]['income'] = float(r.total)
            else:
                monthly_data[key]['expense'] = float(r.total)
        
        # Calculate savings and format response
        response = []
        for month, data in sorted(monthly_data.items()):
            response.append({
                'month': month,
                'income': data['income'],
                'expense': data['expense'],
                'savings': data['income'] - data['expense']
            })
        
        return response
    
    def get_insights(self, user_id: int) -> Dict:
        """Generate intelligent insights for user"""
        
        # Get last 30 days data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Current month spending
        current_month_spending = self.db.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_date
        ).scalar() or 0
        
        # Previous month spending
        prev_start = start_date - timedelta(days=30)
        prev_month_spending = self.db.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date < start_date
        ).scalar() or 0
        
        # Top spending category
        top_category = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(
            Transaction
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_date
        ).group_by(
            Category.name
        ).order_by(
            func.sum(Transaction.amount).desc()
        ).first()
        
        # Generate insights
        insights = {
            'current_month_spending': float(current_month_spending),
            'spending_trend': 'increased' if current_month_spending > prev_month_spending else 'decreased',
            'trend_percentage': abs((current_month_spending - prev_month_spending) / prev_month_spending * 100) if prev_month_spending > 0 else 0,
            'top_spending_category': top_category.name if top_category else None,
            'recommendations': []
        }
        
        # Add recommendations
        if insights['spending_trend'] == 'increased' and insights['trend_percentage'] > 20:
            insights['recommendations'].append(
                f"Your spending increased by {insights['trend_percentage']:.1f}% this month. Consider reviewing your {insights['top_spending_category']} expenses."
            )
        
        return insights
