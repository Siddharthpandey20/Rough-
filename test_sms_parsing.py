"""
Test SMS-FW.com webhook parsing
"""

import re

def test_sms_parsing():
    # Test case 1: Non-payment SMS (should be filtered)
    non_payment_sms = """Forwarded using https://www.sms-fw.com
From: 'IIIT NR Utkarsh Gupta DSAI' (+917017982662)
To: '#phonenumber-sim1'
When: 2025-11-15 06:39:55
************
Bsdk"""
    
    # Test case 2: Payment SMS (should be processed)
    payment_sms = """Forwarded using https://www.sms-fw.com
From: 'ICICIB' (+919876543210)
To: '#phonenumber-sim1'
When: 2025-11-15 10:30:00
************
Rs 500.00 debited from A/c XX1234 on 15Nov24 to VPA swiggy@paytm UPI Ref 434567890123"""
    
    # Test case 3: Credit card payment
    card_payment_sms = """Forwarded using https://www.sms-fw.com
From: 'HDFCBK' (+919123456789)
To: '#phonenumber-sim1'
When: 2025-11-15 14:20:00
************
Rs.1299.00 spent on Card XX5678 at AMAZON INDIA on 15-Nov-25. Avl Bal: Rs.45000.00"""
    
    def parse_sms(raw_sms):
        print(f"\n{'='*60}")
        print("Testing SMS:")
        print(raw_sms[:100] + "...")
        print("-" * 60)
        
        # Extract SMS body
        sms_body_match = re.search(r'\*{8,}[\r\n]+(.+)', raw_sms, re.DOTALL)
        sms_body = sms_body_match.group(1).strip() if sms_body_match else raw_sms
        print(f"SMS Body: {sms_body}")
        
        # Extract sender
        from_match = re.search(r"From: '(.+?)' \((.+?)\)", raw_sms)
        sender_name = from_match.group(1) if from_match else None
        sender_number = from_match.group(2) if from_match else None
        print(f"Sender: {sender_name} ({sender_number})")
        
        # Payment detection
        payment_keywords = [
            r'\brs\.?\s*\d+', r'₹\s*\d+', r'inr\s*\d+',
            r'debited?', r'credited?', r'paid', r'received', r'sent', r'spent',
            r'upi', r'imps', r'neft', r'rtgs',
            r'a/?c\s*(?:no\.?)?\s*[x*]*\d+',
            r'ref(?:erence)?(?:\s*no\.?)?[:\s]*\d+',
            r'txn', r'transaction', r'payment',
        ]
        
        is_payment = any(re.search(pattern, sms_body, re.IGNORECASE) for pattern in payment_keywords)
        print(f"Is Payment: {is_payment}")
        
        if not is_payment:
            print("❌ Filtered out (non-payment)")
            return None
        
        # Parse transaction details
        # Amount
        amount = None
        amount_patterns = [
            r'(?:rs\.?|₹|inr)\s*([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*(?:rs\.?|₹|inr)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, sms_body, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                break
        
        # Transaction type
        transaction_type = "debit"
        if re.search(r'credited?|received|deposited', sms_body, re.IGNORECASE):
            transaction_type = "credit"
        elif re.search(r'spent', sms_body, re.IGNORECASE):
            transaction_type = "debit"
        
        # UPI ID / VPA
        upi_match = re.search(r'(?:to|from)\s+(?:vpa\s+)?([a-z0-9._-]+@[a-z]+)', sms_body, re.IGNORECASE)
        upi_id = upi_match.group(1) if upi_match else None
        merchant = upi_id.split('@')[0] if upi_id else None
        
        # Merchant name (if no UPI)
        if not merchant:
            merchant_patterns = [
                r'(?:at|to|from)\s+([A-Z][A-Z\s]+)',  # All caps
                r'(?:at|to|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Title case
            ]
            for pattern in merchant_patterns:
                match = re.search(pattern, sms_body)
                if match:
                    merchant = match.group(1).strip()
                    break
        
        if not merchant:
            merchant = sender_name
        
        # Reference number
        ref_patterns = [
            r'upi\s+ref(?:erence)?[:\s]*([0-9]+)',
            r'ref(?:erence)?(?:\s*no\.?)?[:\s]*([0-9]+)',
            r'txn[:\s]*([0-9]+)',
        ]
        reference_number = None
        for pattern in ref_patterns:
            match = re.search(pattern, sms_body, re.IGNORECASE)
            if match:
                reference_number = match.group(1)
                break
        
        # Account number
        acc_match = re.search(r'a/?c\s*(?:no\.?)?\s*[x*]*([0-9]{4})', sms_body, re.IGNORECASE)
        account_number = acc_match.group(1) if acc_match else None
        
        # Balance
        balance_match = re.search(r'(?:avl\s+)?(?:bal|balance)[:\s]*(?:rs\.?|₹)?\s*([0-9,]+\.?[0-9]*)', sms_body, re.IGNORECASE)
        balance = float(balance_match.group(1).replace(',', '')) if balance_match else None
        
        print(f"\n✅ Parsed Transaction:")
        print(f"  Amount: ₹{amount}")
        print(f"  Merchant: {merchant}")
        print(f"  UPI ID: {upi_id}")
        print(f"  Type: {transaction_type}")
        print(f"  Reference: {reference_number}")
        print(f"  Account: {account_number}")
        print(f"  Balance: ₹{balance}")
        
        return {
            "amount": amount,
            "merchant": merchant,
            "upi_id": upi_id,
            "transaction_type": transaction_type,
            "reference_number": reference_number,
            "account_number": account_number,
            "balance": balance,
            "sender_name": sender_name
        }
    
    # Test all cases
    parse_sms(non_payment_sms)
    parse_sms(payment_sms)
    parse_sms(card_payment_sms)

if __name__ == "__main__":
    test_sms_parsing()
