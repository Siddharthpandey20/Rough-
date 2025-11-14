"""
OCR and Document Parsing Service
"""

import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import os
from typing import Dict, List, Tuple
from datetime import datetime
import dateparser
import logging

from app.core.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

# Set Tesseract path if configured
if settings.TESSERACT_PATH and os.path.exists(settings.TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
    logger.info(f"Tesseract path set to: {settings.TESSERACT_PATH}")
else:
    # Try common Windows installation paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe"
    ]
    for path in common_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract found at: {path}")
            break
    else:
        logger.warning("Tesseract not found. OCR functionality will be limited. Please install from: https://github.com/UB-Mannheim/tesseract/wiki")


class OCRService:
    """OCR and Document Parsing Service"""
    
    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            
            # Noise removal
            gray = cv2.medianBlur(gray, 3)
            
            return gray
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return cv2.imread(image_path)
    
    @staticmethod
    def extract_text(image_path: str) -> Tuple[str, float]:
        """
        Extract text from image using Tesseract OCR
        
        Returns: (extracted_text, confidence_score)
        """
        try:
            # Preprocess image
            processed_img = OCRService.preprocess_image(image_path)
            
            # Perform OCR with detailed data
            data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            avg_confidence = avg_confidence / 100.0  # Normalize to 0-1
            
            # Extract text
            text = pytesseract.image_to_string(processed_img)
            
            logger.info(f"OCR completed with confidence: {avg_confidence:.2f}")
            return text, avg_confidence
        
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "", 0.0
    
    @staticmethod
    def parse_receipt(ocr_text: str) -> Dict:
        """
        Parse receipt using AI first, fallback to regex
        
        Returns: {
            "date": datetime,
            "amount": float,
            "merchant_name": str,
            "invoice_no": str,
            "items": List[Dict],
            "tax": float,
            "payment_method": str
        }
        """
        try:
            import json
            
            prompt = f"""You are a financial document parser. Extract structured data from this receipt/invoice OCR text.

OCR Text:
{ocr_text}

Extract the following information (use null if not found):
- merchant_name: The business/store name
- amount: Total amount (number only, no currency symbols)
- date: Date in YYYY-MM-DD format
- invoice_no: Invoice/Bill number
- tax: Tax amount (GST/VAT)
- payment_method: cash/card/upi/wallet/netbanking
- items: List of purchased items with price (if clearly visible)
- currency: INR/USD/etc

Respond ONLY with valid JSON:
{{
    "merchant_name": "string or null",
    "amount": number or null,
    "date": "YYYY-MM-DD or null",
    "invoice_no": "string or null",
    "tax": number or null,
    "payment_method": "string or null",
    "items": [],
    "currency": "INR"
}}"""

            response = gemini_service.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed_data = json.loads(result_text)
            
            # Convert date string to datetime if present
            if parsed_data.get("date"):
                try:
                    parsed_data["date"] = datetime.strptime(parsed_data["date"], "%Y-%m-%d")
                except:
                    parsed_data["date"] = dateparser.parse(parsed_data["date"])
            
            logger.info(f"AI parsed receipt: {parsed_data}")
            return parsed_data
        
        except Exception as e:
            logger.error(f"AI parsing failed: {e}, falling back to regex")
            return OCRService._parse_receipt_regex(ocr_text)
    
    @staticmethod
    def _parse_receipt_regex(ocr_text: str) -> Dict:
        """
        Parse receipt/invoice text to extract structured data
        
        Returns: {
            "date": datetime,
            "amount": float,
            "merchant_name": str,
            "invoice_no": str,
            "items": List[Dict],
            "tax": float,
            "payment_method": str
        }
        """
        parsed_data = {
            "date": None,
            "amount": None,
            "merchant_name": None,
            "invoice_no": None,
            "items": [],
            "tax": None,
            "payment_method": None
        }
        
        try:
            lines = ocr_text.strip().split('\n')
            
            # Extract merchant name (usually first few lines)
            for i, line in enumerate(lines[:5]):
                if line.strip() and len(line.strip()) > 3:
                    parsed_data["merchant_name"] = line.strip()
                    break
            
            # Extract amount (look for patterns like: Total: ₹1234.56, Amount: 1234.56)
            amount_patterns = [
                r'total[:\s]*₹?\s*(\d+\.?\d*)',
                r'amount[:\s]*₹?\s*(\d+\.?\d*)',
                r'₹\s*(\d+\.?\d*)',
                r'rs\.?\s*(\d+\.?\d*)',
            ]
            
            for pattern in amount_patterns:
                matches = re.findall(pattern, ocr_text.lower())
                if matches:
                    try:
                        parsed_data["amount"] = float(matches[-1])  # Usually last match is total
                        break
                    except:
                        continue
            
            # Extract date
            date_patterns = [
                r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
                r'\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, ocr_text.lower())
                if matches:
                    try:
                        parsed_data["date"] = dateparser.parse(matches[0])
                        break
                    except:
                        continue
            
            # Extract invoice number
            invoice_patterns = [
                r'invoice[:\s#]*([A-Z0-9-]+)',
                r'bill[:\s#]*([A-Z0-9-]+)',
                r'receipt[:\s#]*([A-Z0-9-]+)',
            ]
            
            for pattern in invoice_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    parsed_data["invoice_no"] = matches[0]
                    break
            
            # Extract tax
            tax_patterns = [
                r'gst[:\s]*₹?\s*(\d+\.?\d*)',
                r'tax[:\s]*₹?\s*(\d+\.?\d*)',
            ]
            
            for pattern in tax_patterns:
                matches = re.findall(pattern, ocr_text.lower())
                if matches:
                    try:
                        parsed_data["tax"] = float(matches[0])
                        break
                    except:
                        continue
            
            # Extract payment method
            payment_keywords = ['upi', 'card', 'cash', 'credit', 'debit', 'wallet', 'netbanking']
            for keyword in payment_keywords:
                if keyword in ocr_text.lower():
                    parsed_data["payment_method"] = keyword.upper()
                    break
            
            logger.info(f"Regex parsed receipt: {parsed_data}")
            return parsed_data
        
        except Exception as e:
            logger.error(f"Receipt parsing error: {e}")
            return parsed_data
    
    @staticmethod
    def parse_upi_message(message_text: str) -> Dict:
        """
        Parse UPI SMS/message to extract transaction details
        
        Example: "Rs 500.00 debited from A/c XX1234 to VPA john@paytm on 15-Jan-24. UPI Ref: 123456789"
        """
        parsed_data = {
            "amount": None,
            "date": None,
            "upi_id": None,
            "upi_ref": None,
            "account": None,
            "transaction_type": None
        }
        
        try:
            # Extract amount
            amount_match = re.search(r'rs\.?\s*(\d+\.?\d*)', message_text.lower())
            if amount_match:
                parsed_data["amount"] = float(amount_match.group(1))
            
            # Determine transaction type
            if 'debited' in message_text.lower() or 'debit' in message_text.lower():
                parsed_data["transaction_type"] = "debit"
            elif 'credited' in message_text.lower() or 'credit' in message_text.lower():
                parsed_data["transaction_type"] = "credit"
            
            # Extract UPI ID
            upi_match = re.search(r'(?:to|from)\s+(?:vpa\s+)?([a-z0-9._-]+@[a-z]+)', message_text.lower())
            if upi_match:
                parsed_data["upi_id"] = upi_match.group(1)
            
            # Extract UPI reference
            ref_match = re.search(r'(?:upi\s+ref|ref\s*no|reference)[:\s]*([a-z0-9]+)', message_text.lower())
            if ref_match:
                parsed_data["upi_ref"] = ref_match.group(1)
            
            # Extract account number
            acc_match = re.search(r'a/?c\s+(?:xx)?(\d+)', message_text.lower())
            if acc_match:
                parsed_data["account"] = acc_match.group(1)
            
            # Extract date
            date_match = re.search(r'\d{1,2}-\w{3}-\d{2,4}', message_text)
            if date_match:
                parsed_data["date"] = dateparser.parse(date_match.group())
            
            logger.info(f"Parsed UPI message: {parsed_data}")
            return parsed_data
        
        except Exception as e:
            logger.error(f"UPI message parsing error: {e}")
            return parsed_data


# Global instance
ocr_service = OCRService()
