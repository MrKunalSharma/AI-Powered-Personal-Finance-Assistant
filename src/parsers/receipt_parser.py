import cv2
import pytesseract
import numpy as np
from PIL import Image
import re
from typing import Dict, List, Optional
import io

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class ReceiptParser:
    """OCR-based receipt parser"""
    
    def __init__(self):
        self.amount_patterns = [
            r'TOTAL[\s:]+(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)',
            r'Grand\s*Total[\s:]+(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)',
            r'Amount[\s:]+(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)',
            r'(?:Rs\.?|₹)\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*(?:Rs\.?|₹)',
            r'\b(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)\b'  # General number pattern
        ]
        
        self.merchant_patterns = [
            r'^([A-Z][A-Z\s&\-\.]{2,})$',  # All caps line at start
            r'(?:From|Merchant|Store|Restaurant)[\s:]+([A-Za-z\s&\-\.]+)',
            r'([A-Z][A-Za-z\s&\-\.]{3,})\s*\n'  # Title case at line start
        ]
        
        self.date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
            r'Date[\s:]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        ]
    
    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get better OCR results
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(thresh, 3)
        
        return denoised
    
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract text from receipt image using OCR"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_bytes)
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_img, config='--psm 6')
            
            return text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def extract_amount(self, text: str) -> Optional[float]:
        """Extract total amount from receipt text"""
        amounts_found = []
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    # Clean and convert amount
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    if 10 <= amount <= 100000:  # Reasonable amount range
                        amounts_found.append(amount)
                except ValueError:
                    continue
        
        # Return the largest amount (usually the total)
        return max(amounts_found) if amounts_found else None
    
    def extract_merchant(self, text: str) -> Optional[str]:
        """Extract merchant name from receipt"""
        lines = text.split('\n')
        
        # Check first few lines for merchant name
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and line.isupper():
                # Likely merchant name
                return line.title()
        
        # Try patterns
        for pattern in self.merchant_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip().title()
        
        return None
    
    def extract_items(self, text: str) -> List[Dict]:
        """Extract line items from receipt"""
        items = []
        lines = text.split('\n')
        
        # Pattern for item lines (item name followed by price)
        item_pattern = r'(.+?)\s+(\d+(?:\.\d{2})?)\s*$'
        
        for line in lines:
            match = re.match(item_pattern, line.strip())
            if match:
                item_name = match.group(1).strip()
                price = float(match.group(2))
                
                # Filter out totals and subtotals
                if not any(word in item_name.lower() for word in ['total', 'tax', 'subtotal', 'balance']):
                    items.append({
                        'name': item_name,
                        'price': price
                    })
        
        return items
    
    def parse_receipt(self, image_bytes: bytes) -> Dict:
        """Main method to parse receipt"""
        text = self.extract_text_from_image(image_bytes)
        
        if not text:
            return {
                'success': False,
                'error': 'Could not extract text from image',
                'raw_text': ''
            }
        
        amount = self.extract_amount(text)
        merchant = self.extract_merchant(text)
        items = self.extract_items(text)
        
        # Try to extract date
        date = None
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                date = match.group(1)
                break
        
        return {
            'success': True,
            'amount': amount,
            'merchant': merchant or 'Unknown Merchant',
            'date': date,
            'items': items,
            'raw_text': text
        }
