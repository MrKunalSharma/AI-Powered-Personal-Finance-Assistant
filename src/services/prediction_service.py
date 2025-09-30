import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from sklearn.linear_model import LinearRegression
from typing import Dict, List
from ..database.models import Transaction, User, Category

class PredictionService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_historical_spending(self, user_id: int, months: int = 6) -> pd.DataFrame:
        """Get historical spending data for predictions"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Query monthly spending
        monthly_spending = self.db.query(
            func.extract('year', Transaction.transaction_date).label('year'),
            func.extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_date
        ).group_by('year', 'month').all()
        
        # Convert to DataFrame
        data = []
        for item in monthly_spending:
            data.append({
                'year': int(item.year),
                'month': int(item.month),
                'amount': float(item.total)
            })
        
        return pd.DataFrame(data)
    
    def predict_monthly_spending(self, user_id: int) -> Dict:
        """Predict next month's spending using linear regression"""
        df = self.get_historical_spending(user_id)
        
        if len(df) < 3:  # Need at least 3 months of data
            return {
                "prediction": None,
                "confidence": 0,
                "message": "Need at least 3 months of data for predictions"
            }
        
        # Prepare data for regression
        df['month_number'] = df['year'] * 12 + df['month']
        X = df['month_number'].values.reshape(-1, 1)
        y = df['amount'].values
        
        # Train model
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next month
        current_date = datetime.now()
        next_month_number = current_date.year * 12 + current_date.month + 1
        prediction = model.predict([[next_month_number]])[0]
        
        # Calculate confidence (R-squared)
        confidence = model.score(X, y)
        
        # Calculate trend
        trend = "increasing" if model.coef_[0] > 0 else "decreasing"
        avg_monthly_change = abs(model.coef_[0])
        
        return {
            "prediction": float(prediction),
            "confidence": float(confidence),
            "trend": trend,
            "avg_monthly_change": float(avg_monthly_change),
            "historical_average": float(df['amount'].mean()),
            "last_month": float(df.iloc[-1]['amount']) if not df.empty else 0
        }
    
    def predict_category_spending(self, user_id: int, days_ahead: int = 30) -> List[Dict]:
        """Predict spending by category for next N days"""
        # Get spending pattern by day of week and category
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Last 3 months
        
        # Query daily average by category
        category_patterns = self.db.query(
            Category.name,
            func.extract('dow', Transaction.transaction_date).label('day_of_week'),
            func.avg(Transaction.amount).label('avg_amount'),
            func.count(Transaction.id).label('frequency')
        ).join(
            Transaction
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_date
        ).group_by(
            Category.name,
            'day_of_week'
        ).all()
        
        # Calculate predictions
        predictions = {}
        for pattern in category_patterns:
            if pattern.name not in predictions:
                predictions[pattern.name] = {
                    'predicted_amount': 0,
                    'predicted_transactions': 0
                }
            
            # Estimate transactions in next N days
            days_of_this_dow = days_ahead / 7  # Approximate
            predictions[pattern.name]['predicted_amount'] += float(pattern.avg_amount * pattern.frequency * days_of_this_dow / 90 * 30)
            predictions[pattern.name]['predicted_transactions'] += pattern.frequency * days_of_this_dow / 90 * 30
        
        # Convert to list format
        result = []
        for category, data in predictions.items():
            result.append({
                'category': category,
                'predicted_amount': round(data['predicted_amount'], 2),
                'predicted_transactions': round(data['predicted_transactions'])
            })
        
        return sorted(result, key=lambda x: x['predicted_amount'], reverse=True)
    
    def get_spending_insights(self, user_id: int) -> Dict:
        """Generate AI insights based on spending patterns"""
        # Get current month spending
        current_month_start = datetime.now().replace(day=1)
        current_spending = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= current_month_start
        ).scalar() or 0
        
        # Get predictions
        monthly_prediction = self.predict_monthly_spending(user_id)
        category_predictions = self.predict_category_spending(user_id, 30)
        
        insights = []
        
        # Insight 1: Spending trend
        if monthly_prediction['prediction']:
            if monthly_prediction['trend'] == 'increasing':
                insights.append(f"⚠️ Your spending is trending upward by ₹{monthly_prediction['avg_monthly_change']:.0f}/month")
            else:
                insights.append(f"✅ Good news! Your spending is decreasing by ₹{monthly_prediction['avg_monthly_change']:.0f}/month")
        
        # Insight 2: Current vs predicted
        if monthly_prediction['prediction'] and current_spending > monthly_prediction['prediction'] * 0.5:
            days_passed = datetime.now().day
            days_in_month = 30
            projected_monthly = (current_spending / days_passed) * days_in_month
            
            if projected_monthly > monthly_prediction['historical_average'] * 1.2:
                insights.append(f"🚨 At current rate, you'll spend ₹{projected_monthly:.0f} this month - 20% above your average!")
        
        # Insight 3: Top predicted category
        if category_predictions:
            top_category = category_predictions[0]
            insights.append(f"💡 Expect to spend ₹{top_category['predicted_amount']:.0f} on {top_category['category']} in the next 30 days")
        
        return {
            "insights": insights,
            "monthly_prediction": monthly_prediction,
            "category_predictions": category_predictions[:5]  # Top 5 categories
        }
