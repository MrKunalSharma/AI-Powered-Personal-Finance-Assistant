import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from typing import List, Tuple
import os

class TransactionCategorizer:
    """ML-based transaction categorization system"""
    
    def __init__(self):
        self.model = None
        self.categories = [
            "Food & Dining",
            "Shopping",
            "Transportation",
            "Bills & Utilities",
            "Entertainment",
            "Healthcare",
            "Education",
            "Travel",
            "Groceries",
            "ATM/Cash",
            "Income",
            "Others"
        ]
        
        # Training data (in production, load from database)
        self.training_data = [
            # Food & Dining
            ("swiggy payment", "Food & Dining"),
            ("zomato order", "Food & Dining"),
            ("restaurant bill", "Food & Dining"),
            ("dominos pizza", "Food & Dining"),
            ("pizza", "Food & Dining"),
            ("cafe coffee", "Food & Dining"),
            ("mcdonalds", "Food & Dining"),
            ("burger king", "Food & Dining"),
            ("kfc", "Food & Dining"),
            
            # Shopping
            ("amazon purchase", "Shopping"),
            ("amazon shopping", "Shopping"),
            ("flipkart order", "Shopping"),
            ("myntra fashion", "Shopping"),
            ("online shopping", "Shopping"),
            
            # Transportation
            ("uber ride", "Transportation"),
            ("ola cab", "Transportation"),
            ("petrol pump", "Transportation"),
            ("metro card recharge", "Transportation"),
            ("railway", "Transportation"),
            
            # Bills & Utilities
            ("electricity bill", "Bills & Utilities"),
            ("mobile recharge", "Bills & Utilities"),
            ("internet bill", "Bills & Utilities"),
            ("water bill", "Bills & Utilities"),
            ("gas bill", "Bills & Utilities"),
            ("airtel", "Bills & Utilities"),
            ("vodafone", "Bills & Utilities"),
            ("jio", "Bills & Utilities"),
            
            # Entertainment
            ("netflix subscription", "Entertainment"),
            ("netflix", "Entertainment"),
            ("movie ticket", "Entertainment"),
            ("spotify premium", "Entertainment"),
            ("spotify", "Entertainment"),
            ("amazon prime", "Entertainment"),
            ("hotstar", "Entertainment"),
            ("pvr cinema", "Entertainment"),
            
            # Healthcare
            ("apollo pharmacy", "Healthcare"),
            ("doctor consultation", "Healthcare"),
            ("medical store", "Healthcare"),
            ("hospital", "Healthcare"),
            ("medicine", "Healthcare"),
            ("clinic", "Healthcare"),
            
            # ATM/Cash
            ("atm withdrawal", "ATM/Cash"),
            ("cash withdrawal", "ATM/Cash"),
            ("atm", "ATM/Cash"),
            ("withdrawn from atm", "ATM/Cash"),
            ("hdfc bank atm", "ATM/Cash"),
            ("sbi atm", "ATM/Cash"),
            
            # Income
            ("salary", "Income"),
            ("salary credit", "Income"),
            ("salary from", "Income"),
            ("tech private limited", "Income"),
            ("credited salary", "Income"),
            ("monthly salary", "Income"),
            
            # Groceries
            ("bigbasket order", "Groceries"),
            ("dmart purchase", "Groceries"),
            ("vegetable market", "Groceries"),
            ("grocery", "Groceries"),
            ("supermarket", "Groceries"),
        ]
        
        self.model_path = "data/models/categorizer.pkl"
        self._initialize_model()

    
    def _initialize_model(self):
        """Initialize or load the model"""
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            self.train()
    
    def train(self):
        """Train the categorization model"""
        # Prepare training data
        descriptions, categories = zip(*self.training_data)
        
        # Create pipeline with TF-IDF and Naive Bayes
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                ngram_range=(1, 2),
                max_features=1000
            )),
            ('classifier', MultinomialNB())
        ])
        
        # Train model
        self.model.fit(descriptions, categories)
        
        # Save model
        self.save_model()
    
    def predict(self, description: str) -> Tuple[str, float]:
        """Predict category for a transaction description"""
        if not self.model:
            self.train()
        
        # Handle None or empty descriptions
        if not description:
            description = "Unknown Transaction"
        
        # Ensure description is a string
        description = str(description)
        
        # Get prediction and probability
        category = self.model.predict([description])[0]
        probabilities = self.model.predict_proba([description])[0]
        confidence = max(probabilities)
        
        return category, confidence

    
    def predict_batch(self, descriptions: List[str]) -> List[Tuple[str, float]]:
        """Predict categories for multiple descriptions"""
        if not self.model:
            self.train()
        
        predictions = self.model.predict(descriptions)
        probabilities = self.model.predict_proba(descriptions)
        
        results = []
        for pred, probs in zip(predictions, probabilities):
            confidence = max(probs)
            results.append((pred, confidence))
        
        return results
    
    def save_model(self):
        """Save the trained model"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
    
    def load_model(self):
        """Load a saved model"""
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
    
    def add_training_data(self, description: str, category: str):
        """Add new training example and retrain"""
        self.training_data.append((description, category))
        self.train()
