# 🔄 n8n Setup for LUMEN

## Quick Start (2 hours total)

### 1️⃣ Install n8n (15 seconds)
```bash
npx n8n
# Opens at http://localhost:5678
```

---

## 📧 Gmail Workflow (30 minutes)

### Import & Configure

1. **Import** `n8n_workflows/lumen_gmail_workflow.json`

2. **Gmail Trigger**:
   - Add Gmail OAuth credentials
   - Poll interval: Every 1 minute
   - Optional filter: `from:payment@* OR from:transactions@*`

3. **AI Parser** (OpenAI):
   - Add OpenAI API key
   - Model: `gpt-4` or `gpt-3.5-turbo`

4. **HTTP Request**:
   - URL: `http://localhost:8000/api/v1/n8n/email`
   - Authorization: `Bearer YOUR_JWT_TOKEN`

5. **Activate** workflow

✅ **Done!** Gmail transactions auto-sync every minute.

---

## 📱 SMS Workflow (15 minutes) - Optional

### Using SMS Forwarder App

**App**: https://play.google.com/store/apps/details?id=enstone.smsfw.app

**Steps**:
1. Install SMS Forwarder on Android
2. Import `n8n_workflows/lumen_sms_gateway_workflow.json`
3. Copy n8n webhook URL
4. Configure SMS Forwarder:
   - Filter: ICICIB, HDFCBK, SBIIN, AXISBK
   - Forward to: Webhook (your n8n URL)
5. Update JWT token in n8n
6. Activate workflow

📖 **Detailed guide**: [SMS_FORWARDER_SETUP.md](SMS_FORWARDER_SETUP.md)

---

## 🧪 Testing

### Email Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/n8n/email \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"gmail","amount":1299,"merchant":"Amazon"}'
```

### SMS Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/n8n/sms \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"sms","amount":500,"merchant":"Swiggy","upi_id":"swiggy@paytm"}'
```

---

## 💡 Recommendation

**Gmail First!** Banks send emails with same data as SMS.

- ✅ More reliable
- ✅ No phone dependency
- ✅ Already tested (transaction 151 created ✅)

**SMS**: Optional, adds real-time capture

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Error | Get fresh JWT from `/auth/login` |
| 403 Forbidden | Enable consent flags |
| Workflow not running | Toggle "Active" in n8n |
| Gmail not triggering | Check OAuth & poll interval |

---

## 📚 API Docs

Full documentation: [API_DOCUMENTATION.md](API_DOCUMENTATION.md) → Section: "n8n Webhooks"
