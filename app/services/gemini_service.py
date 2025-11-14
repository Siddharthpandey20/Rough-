"""
Gemini AI Service - Integration with Google Gemini API
"""

import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json
import time
from google.api_core import retry

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    """Google Gemini AI Service for classification and RAG"""
    
    def __init__(self):
        # Use gemini-1.5-flash-latest (stable) instead of experimental models
        # Fallback to basic responses if API fails
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            self.chat_model = genai.GenerativeModel('gemini-1.5-flash-latest')
            logger.info("Gemini models initialized with gemini-1.5-flash-latest")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini models: {e}")
            self.model = None
            self.chat_model = None
    
    def _call_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Call Gemini API with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota/rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                        logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for Gemini API: {e}")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"Gemini API error: {e}")
                    raise
        return None
    
    def classify_transaction(
        self,
        merchant_name: str,
        amount: float,
        parsed_fields: Dict,
        user_categories: List[str],
        user_history: Optional[Dict] = None
    ) -> Dict:
        """
        Classify transaction using Gemini
        
        Returns: {
            "category": str,
            "confidence": float,
            "reasoning": str
        }
        """
        try:
            # Fallback if model not available
            if self.model is None:
                logger.warning("Gemini model not available, using fallback classification")
                return self._fallback_classification(merchant_name, user_categories)
            
            prompt = f"""You are a financial transaction classifier.

User's Categories: {', '.join(user_categories)}

Transaction Details:
- Merchant: {merchant_name}
- Amount: ₹{amount}
- Parsed Fields: {json.dumps(parsed_fields, indent=2)}

{f"User History: User typically categorizes similar merchants as: {user_history}" if user_history else ""}

Task: Classify this transaction into ONE of the user's categories.

Respond ONLY with valid JSON in this format:
{{
    "category": "category_name",
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}

If you cannot confidently classify (confidence < 0.6), use category "Unknown"."""

            response = self._call_with_retry(self.model.generate_content, prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Validate category is in user's list
            if result['category'] not in user_categories and result['category'] != "Unknown":
                result['category'] = "Unknown"
                result['confidence'] = 0.3
                result['reasoning'] = "Category not in user's defined categories"
            
            logger.info(f"Classified transaction as {result['category']} with confidence {result['confidence']}")
            return result
        
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self._fallback_classification(merchant_name, user_categories)
    
    def _fallback_classification(self, merchant_name: str, user_categories: List[str]) -> Dict:
        """Fallback classification using simple keyword matching"""
        merchant_lower = merchant_name.lower()
        
        # Simple keyword mapping
        keyword_map = {
            "groceries": ["grocery", "supermarket", "market", "store"],
            "food & dining": ["restaurant", "cafe", "pizza", "burger", "food", "dining"],
            "transport": ["uber", "ola", "taxi", "fuel", "petrol", "gas"],
            "utilities": ["electricity", "water", "phone", "internet"],
            "entertainment": ["movie", "cinema", "netflix", "spotify", "game"],
            "shopping": ["amazon", "flipkart", "shop"],
            "inventory": ["supplier", "wholesale", "stock"],
            "supplies": ["office", "supply", "stationery"],
        }
        
        # Check each category
        for category in user_categories:
            category_lower = category.lower()
            keywords = keyword_map.get(category_lower, [category_lower])
            
            for keyword in keywords:
                if keyword in merchant_lower:
                    return {
                        "category": category,
                        "confidence": 0.6,
                        "reasoning": f"Matched keyword '{keyword}' in merchant name (fallback classification)"
                    }
        
        return {
            "category": "Unknown",
            "confidence": 0.3,
            "reasoning": "Could not classify - Gemini API unavailable and no keyword match"
        }
    
    def generate_chat_response(
        self,
        query: str,
        context: List[Dict],
        session_memory: Dict,
        persistent_memory: Dict
    ) -> Dict:
        """
        Generate RAG response using Gemini
        
        Args:
            query: User's question
            context: Retrieved transaction/document context
            session_memory: Session-level facts
            persistent_memory: Persistent user facts
        
        Returns: {
            "response": str,
            "intent": str,
            "confidence": float,
            "provenance": [transaction_ids]
        }
        """
        try:
            # Fallback if model not available
            if self.chat_model is None:
                logger.warning("Gemini chat model not available, using fallback response")
                return self._fallback_chat_response(query, context)
            
            # Build context string
            context_str = "\n\n".join([
                f"Transaction {i+1} (ID: {ctx.get('id', 'N/A')}): ₹{ctx.get('amount', 0)} at {ctx.get('merchant', 'Unknown')} on {ctx.get('date', 'Unknown')}"
                for i, ctx in enumerate(context[:5])  # Top 5 contexts, simplified
            ])
            
            session_facts = "\n".join([f"- {k}: {v}" for k, v in session_memory.items()])
            persistent_facts = "\n".join([f"- {k}: {v}" for k, v in persistent_memory.items()])
            
            prompt = f"""You are LUMEN, an AI financial assistant helping a user understand their transactions.

Session Facts (Current conversation):
{session_facts if session_facts else "None"}

Persistent User Facts:
{persistent_facts if persistent_facts else "None"}

Retrieved Transaction Context:
{context_str if context_str else "No specific transactions found"}

User Query: {query}

Instructions:
1. Answer the user's question based on the provided transaction data
2. Be conversational and helpful
3. If you found specific transactions, mention their IDs and details
4. If no relevant data, say so honestly
5. Classify the intent: "exact_lookup", "summary", "trend", "conversational", or "unknown"
6. Provide confidence score (0-1)

Respond ONLY with valid JSON:
{{
    "response": "Your natural language response here",
    "intent": "intent_type",
    "confidence": 0.95,
    "provenance": [list of transaction IDs used],
    "reasoning": "Why you gave this answer"
}}"""

            response = self._call_with_retry(self.chat_model.generate_content, prompt)
            result_text = response.text.strip()
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"Generated chat response with intent {result.get('intent', 'unknown')}")
            return result
        
        except Exception as e:
            logger.error(f"Chat generation error: {e}")
            return self._fallback_chat_response(query, context)
    
    def _fallback_chat_response(self, query: str, context: List[Dict]) -> Dict:
        """Fallback chat response when Gemini is unavailable"""
        query_lower = query.lower()
        
        # Greetings
        if any(greeting in query_lower for greeting in ["hello", "hi", "hey"]):
            return {
                "response": "Hello! I'm LUMEN, your financial assistant. I can help you understand your transactions, spending patterns, and answer questions about your finances. How can I help you today?",
                "intent": "conversational",
                "confidence": 0.9,
                "provenance": [],
                "reasoning": "Greeting detected"
            }
        
        # If we have context, provide basic summary
        if context and len(context) > 0:
            total = sum(ctx.get('amount', 0) for ctx in context)
            count = len(context)
            return {
                "response": f"I found {count} relevant transaction(s) totaling ₹{total:.2f}. The transactions include: " + ", ".join([f"₹{ctx.get('amount', 0)} at {ctx.get('merchant', 'Unknown')}" for ctx in context[:3]]) + ". (Note: AI assistant is currently unavailable, showing basic data)",
                "intent": "summary",
                "confidence": 0.6,
                "provenance": [ctx.get('id') for ctx in context if 'id' in ctx],
                "reasoning": "Fallback response with transaction data"
            }
        
        # No context available
        return {
            "response": "I'm currently running in limited mode. I couldn't find specific transactions related to your query. This could be because there are no matching transactions, or the AI service is temporarily unavailable. Please try again later or rephrase your question.",
            "intent": "unknown",
            "confidence": 0.3,
            "provenance": [],
            "reasoning": "No context available and Gemini unavailable"
        }
    
    def extract_intent(self, query: str) -> str:
        """Extract intent from user query"""
        try:
            prompt = f"""Classify the intent of this user query about financial transactions:

Query: "{query}"

Intents:
- exact_lookup: User asking about a specific payment ("Did I pay X?")
- summary: User wants aggregated data ("How much did I spend?")
- trend: User asking about patterns ("Where do I spend most?")
- conversational: General chat or greetings
- unknown: Cannot determine

Respond with ONLY ONE WORD: the intent name."""

            response = self.model.generate_content(prompt)
            intent = response.text.strip().lower()
            
            valid_intents = ["exact_lookup", "summary", "trend", "conversational", "unknown"]
            if intent not in valid_intents:
                intent = "unknown"
            
            return intent
        
        except Exception as e:
            logger.error(f"Intent extraction error: {e}")
            return "unknown"
    
    def explain_anomaly(
        self,
        transaction: Dict,
        pattern: Dict,
        anomaly_details: Dict
    ) -> str:
        """Generate human-readable explanation for anomaly"""
        try:
            prompt = f"""Explain why this transaction was flagged as unusual:

Transaction:
{json.dumps(transaction, indent=2)}

Normal Pattern:
{json.dumps(pattern, indent=2)}

Anomaly Details:
{json.dumps(anomaly_details, indent=2)}

Provide a clear, non-technical explanation for the user in 2-3 sentences."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        
        except Exception as e:
            logger.error(f"Anomaly explanation error: {e}")
            return "This transaction appears unusual based on your spending patterns."


# Global instance
gemini_service = GeminiService()
