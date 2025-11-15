# n8n Workflow Templates

This directory contains ready-to-import n8n workflow templates for autonomous transaction ingestion in LUMEN.

## 📁 Files

### `lumen_gmail_workflow.json`
**Gmail Transaction Auto-Ingestion**

Monitors your Gmail inbox and automatically extracts transaction details from payment emails.

**Components:**
- Gmail Trigger (polls every minute)
- OpenAI GPT-4 Parser (extracts transaction data)
- Format & Validation Logic
- HTTP Request to LUMEN API

**Setup Time:** ~30 minutes

---

### `lumen_sms_workflow.json`
**SMS Transaction Auto-Capture (Twilio)**

Receives SMS from Twilio and parses UPI transaction alerts from Indian banks.

**Components:**
- Twilio Webhook Trigger
- Regex-based UPI Parser
- Format & Validation Logic
- HTTP Request to LUMEN API

**Supported Banks:**
- ICICI Bank
- HDFC Bank
- State Bank of India (SBI)
- Paytm
- Generic UPI patterns

**Setup Time:** ~30 minutes

---

## 🚀 Quick Import

### Step 1: Start n8n
```bash
npx n8n
# Opens at http://localhost:5678
```

### Step 2: Import Workflow

1. Open n8n dashboard
2. Click **"Workflows"** in sidebar
3. Click **"Import from File"**
4. Select the JSON file
5. Click **"Import"**

### Step 3: Configure

**For Gmail Workflow:**
1. Click **"Gmail Trigger"** node → Add credentials
2. Click **"AI Transaction Parser"** → Add OpenAI API key
3. Click **"POST to LUMEN API"** → Update Authorization token

**For SMS Workflow:**
1. Click **"Webhook"** → Copy webhook URL
2. Configure Twilio to forward to that URL
3. Click **"POST to LUMEN API"** → Update Authorization token

### Step 4: Test & Activate

1. Click **"Test workflow"** to run once
2. Check execution history
3. Toggle **"Active"** to enable automatic execution

---

## 📖 Documentation

- **Complete Guide**: [../N8N_INTEGRATION_GUIDE.md](../N8N_INTEGRATION_GUIDE.md)
- **Quick Setup**: [../N8N_QUICK_SETUP.md](../N8N_QUICK_SETUP.md)
- **Reference**: [../N8N_REFERENCE.md](../N8N_REFERENCE.md)

---

## ⚙️ Configuration Required

### Both Workflows Need:
- ✅ Valid LUMEN JWT token
- ✅ LUMEN API running at `http://localhost:8000`
- ✅ User consent enabled (`consent_gmail_ingest` or `consent_sms_ingest`)

### Gmail Workflow Needs:
- ✅ Gmail OAuth credentials
- ✅ OpenAI API key (or alternative AI service)

### SMS Workflow Needs:
- ✅ Twilio account + phone number
- ✅ Twilio configured to forward SMS to n8n webhook

---

## 🧪 Testing

### Test Gmail Workflow
1. Send yourself a payment confirmation email
2. Wait 1 minute (poll interval)
3. Check n8n execution history
4. Verify transaction in LUMEN dashboard

### Test SMS Workflow
1. Send test UPI SMS to Twilio number:
   ```
   Rs 500 debited from A/c XX1234 on 15Nov to VPA swiggy@paytm UPI Ref 434512345678
   ```
2. Check n8n execution history immediately
3. Verify transaction in LUMEN dashboard

---

## 🔧 Customization

### Modify AI Prompt (Gmail)
Edit the **"AI Transaction Parser"** node:
```
Extract transaction from this email and return JSON:
{
  "amount": <number>,
  "merchant": "<name>",
  "category": "<category>",
  ...
}
```

### Add Bank Pattern (SMS)
Edit the **"Parse UPI SMS"** node, add to patterns array:
```javascript
/Your custom bank regex pattern/i
```

### Change API URL
If deploying to production, update **"POST to LUMEN API"** nodes:
```
https://your-domain.com/api/v1/n8n/email
https://your-domain.com/api/v1/n8n/sms
```

---

## 🐛 Troubleshooting

### Workflow Not Running
- Check if workflow is **Active** (toggle in top-right)
- Verify credentials are valid
- Check n8n execution history for errors

### 401 Unauthorized
- JWT token expired - get new token from `/api/v1/auth/login`
- Token format must be: `Bearer <token>`

### No Transactions Created
- Check user has consent enabled
- Verify API URL is correct
- Check FastAPI logs: `tail -f logs/app.log`

### AI Parser Returns Null
- Email may not contain transaction data
- Improve AI prompt with examples
- Check OpenAI API credits

---

## 📊 Workflow Versions

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-15 | Initial release |

---

## 🤝 Contributing

To contribute improved workflow templates:

1. Export your workflow from n8n
2. Remove sensitive credentials
3. Test import works correctly
4. Document any new nodes or features
5. Submit for review

---

## 📄 License

These workflow templates are part of the LUMEN project.

---

**Need Help?** Check the full integration guide or visit n8n documentation: https://docs.n8n.io
