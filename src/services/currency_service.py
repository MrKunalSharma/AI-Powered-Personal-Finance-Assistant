import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

class CurrencyService:
    """Service for currency conversion and exchange rates"""
    
    def __init__(self):
        # Using exchangerate-api (free tier available)
        self.base_url = "https://api.exchangerate-api.com/v4/latest/"
        self.supported_currencies = {
            "INR": "₹",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "AED": "د.إ",
            "SGD": "S$",
            "CAD": "C$",
            "AUD": "A$",
            "JPY": "¥",
            "CNY": "¥"
        }
        self.exchange_rates = {}
        self.last_update = None
    
    def get_exchange_rates(self, base_currency: str = "INR") -> Dict[str, float]:
        """Get current exchange rates"""
        # Cache rates for 1 hour
        if self.last_update and (datetime.now() - self.last_update) < timedelta(hours=1):
            if base_currency in self.exchange_rates:
                return self.exchange_rates[base_currency]
        
        try:
            # For demo purposes, using mock data
            # In production, uncomment the API call below
            
            # response = requests.get(f"{self.base_url}{base_currency}")
            # data = response.json()
            # rates = data['rates']
            
            # Mock exchange rates (as of Dec 2023)
            if base_currency == "INR":
                rates = {
                    "INR": 1.0,
                    "USD": 0.012,  # 1 INR = 0.012 USD
                    "EUR": 0.011,
                    "GBP": 0.0096,
                    "AED": 0.044,
                    "SGD": 0.016,
                    "CAD": 0.016,
                    "AUD": 0.018,
                    "JPY": 1.75,
                    "CNY": 0.086
                }
            elif base_currency == "USD":
                rates = {
                    "INR": 83.12,  # 1 USD = 83.12 INR
                    "USD": 1.0,
                    "EUR": 0.92,
                    "GBP": 0.79,
                    "AED": 3.67,
                    "SGD": 1.33,
                    "CAD": 1.36,
                    "AUD": 1.52,
                    "JPY": 147.66,
                    "CNY": 7.16
                }
            else:
                # Default to INR rates for other currencies
                rates = self.get_exchange_rates("INR")
                inr_to_base = 1 / rates.get(base_currency, 1)
                rates = {k: v * inr_to_base for k, v in rates.items()}
            
            self.exchange_rates[base_currency] = rates
            self.last_update = datetime.now()
            
            return rates
            
        except Exception as e:
            print(f"Error fetching exchange rates: {e}")
            # Return default rates
            return {"INR": 1.0, "USD": 0.012, "EUR": 0.011}
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        rates = self.get_exchange_rates(from_currency)
        rate = rates.get(to_currency, 1.0)
        
        return amount * rate
    
    def convert_to_inr(self, amount: float, from_currency: str) -> float:
        """Convert any currency to INR"""
        return self.convert_currency(amount, from_currency, "INR")
    
    def format_currency(self, amount: float, currency: str) -> str:
        """Format amount with currency symbol"""
        symbol = self.supported_currencies.get(currency, "")
        return f"{symbol}{amount:,.2f}"
    
    def detect_currency_from_text(self, text: str) -> str:
        """Detect currency from transaction text"""
        text_lower = text.lower()
        
        # Currency detection patterns
        currency_patterns = {
            "USD": ["$", "usd", "dollar", "dollars"],
            "EUR": ["€", "eur", "euro", "euros"],
            "GBP": ["£", "gbp", "pound", "pounds"],
            "AED": ["aed", "dirham", "dirhams", "د.إ"],
            "SGD": ["sgd", "s$", "singapore dollar"],
            "JPY": ["¥", "jpy", "yen"],
            "INR": ["₹", "rs", "rupee", "rupees", "inr"]
        }
        
        for currency, patterns in currency_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return currency
        
        return "INR"  # Default to INR
