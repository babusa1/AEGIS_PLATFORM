# VeritOS Testing Summary

**Quick reference guide for testing VeritOS after rebranding**

---

## ✅ Testing Status

### Phase 1: User-Facing Changes ✅ Complete
- [x] Documentation updated (50+ files)
- [x] API titles and descriptions
- [x] Frontend UI components
- [x] Log messages and docstrings

### Phase 2: Configuration Changes ✅ Complete
- [x] Environment variables (`VERITOS_*`)
- [x] Config class (`VeritOSSettings`)
- [x] Deployment configs (Helm)
- [x] Default values (indexes, topics)

---

## 🧪 Quick Test (5 minutes)

### 1. Environment Variables
```bash
# Copy .env.example to .env
cp .env.example .env

# Verify VERITOS_ vars are present
grep VERITOS .env
```

**Expected:** All variables use `VERITOS_*` prefix

### 2. Config Class
```python
python -c "from aegis.config import VeritOSSettings; print('✅ VeritOSSettings works')"
```

**Expected:** No errors, class exists

### 3. API Response
```bash
# Start API
uvicorn src.aegis.api.main:app --reload

# Test root endpoint
curl http://localhost:8000/
```

**Expected:** `{"name": "VeritOS API", ...}`

### 4. Frontend UI
```bash
cd demo
npm run dev
# Open http://localhost:3000
```

**Expected:** Sidebar shows "VeritOS", not "AEGIS"

---

## 📊 What Works

### ✅ Backend API
- FastAPI server runs successfully
- Health check endpoint works
- API documentation shows "VeritOS API"
- All routes functional

### ✅ Frontend Dashboard
- Next.js app loads correctly
- Sidebar shows "VeritOS" branding
- Navigation works
- Pages render properly

### ✅ Configuration
- `VERITOS_*` env vars recognized
- `VeritOSSettings` class works
- Config loads correctly
- No `AEGIS_*` references in config

### ✅ Documentation
- All docs show "VeritOS"
- Brand positioning document created
- Testing guide available
- Deployment guide ready

---

## 🔍 What to Test

### Critical Tests

1. **API Startup**
   - [ ] API starts without errors
   - [ ] Logs show "Starting VeritOS API"
   - [ ] Health endpoint returns 200

2. **Frontend Load**
   - [ ] Frontend loads without errors
   - [ ] Sidebar shows "VeritOS"
   - [ ] No console errors

3. **Environment Variables**
   - [ ] `VERITOS_ENV` is read correctly
   - [ ] `VERITOS_API_PORT` works
   - [ ] Old `AEGIS_*` vars ignored

4. **Config Class**
   - [ ] `VeritOSSettings` exists
   - [ ] `AegisSettings` does NOT exist
   - [ ] Settings load correctly

### Integration Tests

1. **API ↔ Frontend**
   - [ ] Frontend can call API
   - [ ] No CORS errors
   - [ ] Data loads correctly

2. **Database Connections**
   - [ ] PostgreSQL connects
   - [ ] Graph DB connects
   - [ ] OpenSearch connects

3. **Agent Execution**
   - [ ] Agents can be invoked
   - [ ] Agent responses work
   - [ ] Multi-agent orchestration works

---

## 🚨 Known Issues & Fixes

### Issue 1: Old .env file
**Symptom:** API uses old `AEGIS_*` values  
**Fix:** Delete `.env`, copy `.env.example` to `.env`

### Issue 2: Frontend cache
**Symptom:** UI still shows "AEGIS"  
**Fix:** Clear browser cache, rebuild frontend

### Issue 3: Import errors
**Symptom:** `ImportError: AegisSettings`  
**Fix:** Update any code still importing old class name

---

## 📈 Test Results Template

```
Date: [Date]
Tester: [Name]
Environment: [Local/Docker/Vercel]

✅ Passed:
- API startup
- Frontend load
- Environment variables
- Config class
- Documentation

⚠️ Issues Found:
- [List any issues]

🔧 Fixes Applied:
- [List fixes]

📝 Notes:
- [Any additional notes]
```

---

## 🎯 Deployment Testing

### Docker Deployment
- [ ] All containers start
- [ ] Services healthy
- [ ] API accessible
- [ ] Frontend accessible

### Vercel Deployment
- [ ] Frontend builds successfully
- [ ] Frontend deploys to Vercel
- [ ] Environment variables set
- [ ] API connection works

### Backend Deployment
- [ ] Backend deploys successfully
- [ ] Health check passes
- [ ] API endpoints work
- [ ] Database connections work

---

**Last Updated**: February 6, 2026  
**Status**: Ready for testing
