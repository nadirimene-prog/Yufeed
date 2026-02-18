# Yufeed Integration Guide
## How to Activate All New Systems

**Last Updated:** 2026-02-17  
**Systems:** Deadline Reminders + Gap Analyzer + Policy Generator

---

## 🚀 QUICK START (5 Minutes)

### Step 1: Add Routers to main.py

Edit `apps/api/src/main.py`:

```python
# Add these imports at the top (around line 20)
from src.api.reminders import router as reminders_router
from src.api.gap_analysis import router as gap_analysis_router
from src.api.policy_generator import router as policy_generator_router

# Add these lines after other router includes (around line 100)
app.include_router(reminders_router)
app.include_router(gap_analysis_router)
app.include_router(policy_generator_router)
```

### Step 2: Configure Celery for Reminders

Edit your Celery configuration file:

```python
# Add to Celery beat schedule
from src.tasks.reminders import reminder_schedule

app.conf.beat_schedule.update(reminder_schedule)
```

### Step 3: Restart Services

```bash
# Restart FastAPI
uvicorn src.main:app --reload

# Start Celery worker (new terminal)
cd apps/api
celery -A src.worker worker --loglevel=info

# Start Celery beat scheduler (new terminal)
celery -A src.worker beat --loglevel=info
```

### Step 4: Test Everything

```bash
# Test Gap Analyzer Dashboard
curl http://localhost:8000/api/gap-analysis/dashboard

# Test Reminders
curl http://localhost:8000/api/reminders/upcoming

# Test Policy Generator Templates
curl http://localhost:8000/api/policy-generator/templates
```

**That's it!** All systems are now active.

---

## 📊 SYSTEM BY SYSTEM GUIDE

### 1. Deadline Reminder System

**What it does:**
- Sends email reminders at 30, 14, 7, 1 days before deadlines
- Weekly digest every Monday
- Tracks email opens and clicks

**To verify it's working:**

```bash
# Check upcoming deadlines
curl http://localhost:8000/api/reminders/upcoming?days=30

# Check statistics
curl http://localhost:8000/api/reminders/statistics

# Manually trigger a reminder (admin only)
curl -X POST http://localhost:8000/api/reminders/send-now/123
```

**Configuration:**
```python
# Optional: Customize reminder schedule
# Edit src/services/reminder_service.py

DEFAULT_REMINDER_DAYS = [30, 14, 7, 1]  # Change as needed
```

---

### 2. Compliance Gap Analyzer

**What it does:**
- Shows which obligations aren't covered by policies
- Auto-categorizes obligations into 11 categories
- Calculates severity based on deadline and risk
- Suggests policy templates

**To run initial analysis:**

```python
# Create a script: run_gap_analysis.py
from src.services.gap_analyzer import GapAnalyzer
from src.database import get_db

db = next(get_db())
analyzer = GapAnalyzer(db)

# Run analysis
report = analyzer.analyze_coverage()

print(f"Overall Coverage: {report.overall_coverage}%")
print(f"Total Obligations: {report.total_obligations}")
print(f"Uncovered: {report.uncovered_count}")
print(f"Gaps: {len(report.gaps)}")

# Print top 5 gaps
for gap in report.gaps[:5]:
    print(f"  {gap.severity.value}: {gap.celex} - {gap.category.value}")
```

**To use the API:**

```bash
# View dashboard
curl http://localhost:8000/api/gap-analysis/dashboard

# List all gaps
curl "http://localhost:8000/api/gap-analysis/gaps?severity=critical"

# Map obligation to policy
curl -X POST http://localhost:8000/api/gap-analysis/map-obligation \
  -H "Content-Type: application/json" \
  -d '{"obligation_id": 123, "policy_id": 456}'
```

---

### 3. Smart Policy Generator

**What it does:**
- Generates policies from obligations using AI
- Uses templates with variable substitution
- Creates professional policy documents
- Tracks generation jobs

**To generate a policy:**

```bash
# 1. List available templates
curl http://localhost:8000/api/policy-generator/templates

# 2. Get template variables
curl http://localhost:8000/api/policy-generator/templates/aml-cft-policy-master/variables

# 3. Generate policy
curl -X POST http://localhost:8000/api/policy-generator/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "aml-cft-policy-master",
    "obligation_ids": [1, 2, 3],
    "variable_values": {
      "institution_name": "My Bank",
      "mlro_name": "John Smith",
      "jurisdiction": "European Union"
    }
  }'

# 4. View result
curl http://localhost:8000/api/policy-generator/results/{job_id}

# 5. Approve (creates actual policy)
curl -X POST http://localhost:8000/api/policy-generator/results/{job_id}/approve
```

**Quick Generate (Simplified):**

```bash
# One-step generation
curl -X POST "http://localhost:8000/api/policy-generator/quick-generate?template_id=aml-cft-policy-master&institution_name=My%20Bank&mlro_name=John%20Smith" \
  -H "Content-Type: application/json" \
  -d '[1, 2, 3]'  # obligation IDs
```

---

## 🧪 TESTING CHECKLIST

### Basic Functionality

- [ ] **Gap Dashboard loads**
  ```bash
  curl http://localhost:8000/api/gap-analysis/dashboard | jq
  ```

- [ ] **Reminders endpoint works**
  ```bash
  curl http://localhost:8000/api/reminders/upcoming | jq
  ```

- [ ] **Policy templates listed**
  ```bash
  curl http://localhost:8000/api/policy-generator/templates | jq
  ```

- [ ] **Gap mapping works**
  ```bash
  curl -X POST http://localhost:8000/api/gap-analysis/map-obligation \
    -d '{"obligation_id": 1, "policy_id": 1}' | jq
  ```

### Email Testing (Optional)

To test email reminders, you'll need SMTP configured in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
EMAILS_FROM_EMAIL=noreply@yufeed.app
EMAILS_FROM_NAME=Yufeed Compliance
```

Then test:
```bash
curl -X POST http://localhost:8000/api/reminders/send-now/1
```

---

## 📈 MONITORING

### Key Metrics to Watch

**1. Coverage Percentage**
```sql
-- Run in database
SELECT
  coverage_status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM regulatory_obligations
WHERE coverage_status IS NOT NULL
GROUP BY coverage_status;
```

**2. Reminders Sent**
```sql
SELECT
  date(sent_at) as date,
  COUNT(*) as reminders_sent,
  SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened
FROM reminder_logs
WHERE sent_at > datetime('now', '-7 days')
GROUP BY date(sent_at);
```

**3. Policy Generation Stats**
```bash
curl http://localhost:8000/api/policy-generator/stats?days=30
```

---

## 🐛 TROUBLESHOOTING

### Issue: "No module named 'src'"
**Solution:** Make sure you're running from the `apps/api` directory
```bash
cd /Users/imenenadir/Documents/Yufeed/apps/api
python3 -m uvicorn src.main:app
```

### Issue: Celery tasks not running
**Solution:** Check Celery is running
```bash
# Check worker
celery -A src.worker inspect ping

# Check beat scheduler
ps aux | grep celery
```

### Issue: Database tables missing
**Solution:** Run migrations again
```bash
cd apps/api
python3 scripts/create_reminder_tables.py
python3 scripts/create_gap_analyzer_tables.py
python3 scripts/create_policy_generator_tables.py
```

### Issue: AI generation not working
**Solution:** Check API key
```python
# In Python
from src.config import settings
print(settings.ANTHROPIC_API_KEY)  # Should show your key
```

---

## 🎯 WORKFLOW EXAMPLES

### Workflow 1: Find and Fix Gaps

```bash
# 1. Check current coverage
curl http://localhost:8000/api/gap-analysis/dashboard

# 2. Get critical gaps
curl "http://localhost:8000/api/gap-analysis/gaps?severity=critical&limit=5"

# 3. Generate policy for gaps
curl -X POST http://localhost:8000/api/policy-generator/quick-generate \
  -d 'template_id=aml-cft-policy-master&institution_name=My%20Bank&mlro_name=John'

# 4. Approve generated policy
curl -X POST http://localhost:8000/api/policy-generator/results/{job_id}/approve

# 5. Map obligations to new policy
curl -X POST http://localhost:8000/api/gap-analysis/map-obligation \
  -d '{"obligation_id": 123, "policy_id": 456}'

# 6. Verify coverage improved
curl http://localhost:8000/api/gap-analysis/dashboard
```

### Workflow 2: Set Up Deadline Reminders

```bash
# 1. Check upcoming deadlines
curl http://localhost:8000/api/reminders/upcoming?days=90

# 2. Subscribe to notifications (if needed)
curl -X POST http://localhost:8000/api/reminders/subscriptions \
  -d '{"obligation_id": 123, "email_enabled": true}'

# 3. Verify reminders are queued
curl http://localhost:8000/api/reminders/statistics
```

---

## 🔐 SECURITY NOTES

### Access Control

All endpoints require authentication:
- `user` role: Can view gaps and upcoming deadlines
- `compliance` role: Can map obligations, generate policies
- `admin` role: Full access including admin endpoints

### Rate Limiting

Policy generation is resource-intensive. Consider:
```python
# Add to endpoints if needed
@router.post("/generate")
@rate_limit(requests=5, window=60)  # 5 requests per minute
async def generate_policy(...)
```

---

## 📞 SUPPORT

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -f apps/api/logs/app.log
   ```

2. **Verify database:**
   ```bash
   sqlite3 apps/api/compliance.db ".tables"
   ```

3. **Test services:**
   ```bash
   cd apps/api
   python3 scripts/test_all_systems.py
   ```

---

**END OF INTEGRATION GUIDE**
