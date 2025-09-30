import re
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd

class SMSParser:
    """Industry-level SMS parser for bank transactions"""
    
    def __init__(self):
        # Common bank SMS patterns
        self.patterns = {
            'amount': [
                r'INR\s*([\d,]+\.?\d*)',
                r'Rs\.?\s*([\d,]+\.?\d*)',
                r'for\s*Rs\.?\s*([\d,]+\.?\d*)',
                r'amount\s*of\s*Rs\.?\s*([\d,]+\.?\d*)',
            ],
            'type': {
                'debit': ['debited', 'withdrawn', 'paid', 'spent', 'purchase', 'debit', 'withdrawn from'],
                'credit': ['credited', 'received', 'deposited', 'refund', 'credit', 'salary']
            },
            'merchant': [
                r'at\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+Avl|\s+\.|$)',  # Updated pattern
                r'to\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+from|\s+\.|$)',
                r'from\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+Bal|\s+\.|$)',
                r'for\s+payment\s+at\s+([A-Za-z0-9\s&\-\.]+)',
                r'withdrawn\s+from\s+ATM\s+at\s+([A-Za-z0-9\s&\-\.]+)',
            ],
            'card_last_digits': [
                r'card\s*ending\s*(\d{4})',
                r'card\s*\*+(\d{4})',
                r'Card\s+XX(\d{4})',
                r'a/c\s*XX(\d{4})',
            ],
            'date': [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(\d{1,2}\s+\w+\s+\d{2,4})',
                r'on\s+(\d{1,2}-\d{1,2}-\d{4})',  # Added pattern for "on DD-MM-YYYY"
            ]
        }
        self.currency_patterns = {
            'USD': [r'\$\s*([\d,]+\.?\d*)', r'USD\s*([\d,]+\.?\d*)'],
            'EUR': [r'€\s*([\d,]+\.?\d*)', r'EUR\s*([\d,]+\.?\d*)'],
            'GBP': [r'£\s*([\d,]+\.?\d*)', r'GBP\s*([\d,]+\.?\d*)'],
            'AED': [r'AED\s*([\d,]+\.?\d*)', r'Dhs?\s*([\d,]+\.?\d*)'],
            'INR': [r'₹\s*([\d,]+\.?\d*)', r'Rs\.?\s*([\d,]+\.?\d*)', r'INR\s*([\d,]+\.?\d*)']
        }

        
    def parse_sms(self, sms_text: str) -> Dict[str, Optional[str]]:
        """Parse a single SMS and extract transaction details"""
        
        result = {
            'amount': None,
            'currency': 'INR',  # Add currency field
            'type': None,
            'merchant': None,
            'card_last_digits': None,
            'date': None,
            'raw_text': sms_text
        }
        
        # Extract currency and amount
        currency, amount = self.extract_currency_and_amount(sms_text)
        if amount:
            result['currency'] = currency
            result['amount'] = amount
        
        # Extract amount
        for pattern in self.patterns['amount']:
            match = re.search(pattern, sms_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                result['amount'] = float(amount_str)
                break
        
        # Determine transaction type
        sms_lower = sms_text.lower()
        for trans_type, keywords in self.patterns['type'].items():
            if any(keyword in sms_lower for keyword in keywords):
                result['type'] = trans_type
                break
        
        # Extract merchant name
        for pattern in self.patterns['merchant']:
            match = re.search(pattern, sms_text, re.IGNORECASE)
            if match:
                result['merchant'] = match.group(1).strip()
                break
        
        # Extract card last digits
        for pattern in self.patterns['card_last_digits']:
            match = re.search(pattern, sms_text, re.IGNORECASE)
            if match:
                result['card_last_digits'] = match.group(1)
                break
        
        # Extract date
        for pattern in self.patterns['date']:
            match = re.search(pattern, sms_text)
            if match:
                result['date'] = self._parse_date(match.group(1))
                break
        
        return result
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Convert various date formats to standard format"""
        date_formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y',
            '%d %B %Y', '%d %b %Y', '%d %B %y', '%d %b %y',
            '%d-%b-%y', '%d-%B-%y', '%d-%b-%Y', '%d-%B-%Y',
            '%d-DEC-23', '%d-JAN-23', '%d-FEB-23',  # Add month abbreviations
        ]
        
        # Handle DD-MMM-YY format specifically
        import re
        if re.match(r'\d{1,2}-[A-Z]{3}-\d{2}', date_str):
            try:
                return datetime.strptime(date_str, '%d-%b-%y').strftime('%Y-%m-%d')
            except:
                pass
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    
    def parse_bulk_sms(self, sms_list: List[str]) -> pd.DataFrame:
        """Parse multiple SMS messages and return DataFrame"""
        parsed_data = []
        for sms in sms_list:
            parsed_data.append(self.parse_sms(sms))
        
        return pd.DataFrame(parsed_data)
    

    def extract_currency_and_amount(self, text: str) -> tuple:
        """Extract currency and amount from text"""
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    return currency, float(amount_str)
        
        # Default INR extraction if no currency symbol found
        for pattern in self.patterns['amount']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                return 'INR', float(amount_str)
        
        return None, None
