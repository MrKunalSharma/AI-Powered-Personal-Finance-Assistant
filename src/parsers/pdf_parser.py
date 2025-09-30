import PyPDF2
import re
from typing import List, Dict
import tabula
import pandas as pd

class PDFStatementParser:
    """Parse bank statements from PDF files"""
    
    def __init__(self):
        self.transaction_patterns = {
            'date': r'(\d{2}[-/]\d{2}[-/]\d{4})',
            'description': r'[A-Za-z\s]+',
            'amount': r'[\d,]+\.?\d*',
            'balance': r'[\d,]+\.?\d*'
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract raw text from PDF"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[pd.DataFrame]:
        """Extract tables from PDF using tabula"""
        try:
            tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            return tables
        except Exception as e:
            print(f"Error extracting tables: {e}")
            return []
    
    def parse_statement(self, pdf_path: str) -> pd.DataFrame:
        """Main method to parse bank statement"""
        
        # Try table extraction first (more reliable)
        tables = self.extract_tables_from_pdf(pdf_path)
        
        if tables:
            # Process the largest table (usually the transaction table)
            df = max(tables, key=len)
            return self._clean_transaction_table(df)
        else:
            # Fallback to text extraction
            text = self.extract_text_from_pdf(pdf_path)
            return self._parse_text_transactions(text)
    
    def _clean_transaction_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize extracted table"""
        
        # Common column name mappings
        column_mappings = {
            'Date': 'date',
            'Transaction Date': 'date',
            'Description': 'description',
            'Narration': 'description',
            'Debit': 'debit',
            'Credit': 'credit',
            'Amount': 'amount',
            'Balance': 'balance'
        }
        
        # Rename columns
        df.columns = [column_mappings.get(col, col.lower()) for col in df.columns]
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert amount columns
        for col in ['debit', 'credit', 'amount', 'balance']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('Rs.', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _parse_text_transactions(self, text: str) -> pd.DataFrame:
        """Parse transactions from raw text"""
        lines = text.split('\n')
        transactions = []
        
        for line in lines:
            # Look for transaction patterns
            if re.search(self.transaction_patterns['date'], line):
                transaction = self._extract_transaction_from_line(line)
                if transaction:
                    transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def _extract_transaction_from_line(self, line: str) -> Dict:
        """Extract transaction details from a text line"""
        # Implementation depends on specific bank format
        # This is a simplified version
        date_match = re.search(self.transaction_patterns['date'], line)
        amount_matches = re.findall(r'[\d,]+\.?\d*', line)
        
        if date_match and amount_matches:
            return {
                'date': date_match.group(),
                'description': line,
                'amount': float(amount_matches[-1].replace(',', ''))
            }
        return None
