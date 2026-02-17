# Frontend Connection Guide

## ✅ Configuration Complete

Your frontend is already configured to connect to the backend API:

**File:** `apps/web/.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws
NEXT_PUBLIC_TENANT_ID=acme
```

## 🚀 Start the Frontend

### Option 1: Start Frontend Only

```bash
cd /Users/imenenadir/Documents/Yufeed/apps/web
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### Option 2: Start Both Backend + Frontend

**Terminal 1 - Backend:**
```bash
cd /Users/imenenadir/Documents/Yufeed/apps/api
python3 -m uvicorn src.main:app --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/imenenadir/Documents/Yufeed/apps/web
npm run dev
```

## 🔍 Verify Connection

Once both are running, test these URLs:

1. **API Health:** http://localhost:8000/api/query/health
2. **Frontend:** http://localhost:3000
3. **RAG Query:**
   ```bash
   curl -X POST "http://localhost:8000/api/query/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is MiCA?"}'
   ```

## 📡 API Endpoints Available

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query/ask` | POST | Ask questions about regulations |
| `/api/query/suggestions` | GET | Get query suggestions |
| `/api/obligations` | GET | List compliance obligations |
| `/api/obligations/{id}/approve` | PATCH | Approve obligation |
| `/api/ingestion/manual` | POST | Trigger manual ingestion |

## 🎯 Test the Full Flow

1. **Start backend:** `cd apps/api && python3 -m uvicorn src.main:app --port 8000`
2. **Start frontend:** `cd apps/web && npm run dev`
3. **Open browser:** http://localhost:3000
4. **Navigate to:** AML Officer → Ask (or Compliance → Dashboard)
5. **Ask a question:** "What are the MiCA requirements?"

## ⚠️ Troubleshooting

### CORS Errors
If you see CORS errors, the backend already has CORS configured. Check:
- Backend is running on port 8000
- Frontend env has `NEXT_PUBLIC_API_URL=http://localhost:8000`

### API Not Found
If API returns 404:
```bash
# Check if API is running
curl http://localhost:8000/api/query/health

# If not, start it
cd apps/api && python3 -m uvicorn src.main:app --port 8000
```

### WebSocket Connection Failed
WebSocket requires backend to be running. The error toast spam has been fixed - it will fail silently in development.

## 📊 What You'll See

### Frontend Pages:
- **Dashboard:** Overview of obligations, deadlines, alerts
- **AML Officer → Ask:** RAG query interface
- **Compliance → Policies:** Policy management
- **Compliance → Deadlines:** Track implementation deadlines

### API Features:
- AI-generated answers about regulations
- Source citations with CELEX numbers
- Real-time WebSocket notifications
- Document search and retrieval

---

**Ready to start?**

```bash
# Terminal 1 - Backend (already running)
# Terminal 2 - Frontend
cd /Users/imenenadir/Documents/Yufeed/apps/web && npm run dev
```
