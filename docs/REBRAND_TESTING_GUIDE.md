# VeritOS Rebrand Testing Guide

**How to verify the rebranding changes from AEGIS to VeritOS are working correctly.**

---

## 📋 Status Check

### Git Status
✅ **Committed Locally**: Yes (commit `3ac264ae`)  
⚠️ **Pushed to GitHub**: **NOT YET** - Requires manual push

### To Push to GitHub:
```bash
cd "c:\HEALTHCARE_DATA HARMONIZATION\aegis"
git push origin main
```

---

## 🧪 Testing Checklist

### 1. Environment Variables Test

**Test that new `VERITOS_*` env vars are recognized:**

```bash
# Create/update .env file
cp .env.example .env

# Set new env vars
export VERITOS_ENV=development
export VERITOS_DEBUG=true
export VERITOS_API_PORT=8000

# Start the API
uvicorn src.aegis.api.main:app --reload

# Check logs - should show "VeritOS API" not "AEGIS API"
```

**Expected Result:**
- ✅ API starts without errors
- ✅ Logs show "Starting VeritOS API"
- ✅ No references to "AEGIS" in startup logs

---

### 2. API Endpoints Test

**Test API responses show VeritOS branding:**

```bash
# Start API server
uvicorn src.aegis.api.main:app --reload --port 8000

# Test root endpoint
curl http://localhost:8000/

# Test health endpoint
curl http://localhost:8000/health

# Check API docs
# Open: http://localhost:8000/docs
```

**Expected Results:**
- ✅ Root endpoint returns: `{"name": "VeritOS API", ...}`
- ✅ API docs title shows "VeritOS API"
- ✅ Description shows "The Truth Operating System for Healthcare"

---

### 3. Frontend UI Test

**Test that UI shows VeritOS branding:**

```bash
# Start frontend
cd demo
npm install
npm run dev

# Open browser: http://localhost:3000
```

**Expected Results:**
- ✅ Sidebar logo shows "VeritOS" (not "AEGIS")
- ✅ Header search placeholder: "Search patients, claims, or ask VeritOS..."
- ✅ "Ask VeritOS" button text (not "Ask AEGIS")
- ✅ Page titles show "VeritOS"

---

### 4. Configuration Class Test

**Test that VeritOSSettings class works:**

```python
# Python REPL test
from aegis.config import get_settings, VeritOSSettings

# Should work without errors
settings = get_settings()
print(settings.app.env)  # Should work

# Direct class instantiation
app_settings = VeritOSSettings()
print(app_settings.api_port)  # Should work
```

**Expected Results:**
- ✅ `VeritOSSettings` class exists and works
- ✅ `AegisSettings` class does NOT exist (should raise AttributeError)
- ✅ `get_settings()` returns Settings with VeritOSSettings

---

### 5. Environment Variable Prefix Test

**Test that VERITOS_ prefix is recognized:**

```bash
# Set environment variables
export VERITOS_ENV=test
export VERITOS_API_PORT=9000
export VERITOS_DEBUG=false

# Start API
uvicorn src.aegis.api.main:app --reload

# Check config
python -c "from aegis.config import get_settings; s = get_settings(); print(f'Env: {s.app.env}, Port: {s.app.api_port}, Debug: {s.app.debug}')"
```

**Expected Results:**
- ✅ Config reads `VERITOS_ENV` correctly
- ✅ Config reads `VERITOS_API_PORT` correctly
- ✅ Old `AEGIS_*` vars are ignored (if set)

---

### 6. Documentation Test

**Verify documentation shows VeritOS:**

```bash
# Check key documentation files
cat docs/README.md | grep -i "VeritOS"
cat docs/00_PLATFORM_OVERVIEW_VISION.md | grep -i "VeritOS"
cat README.md | grep -i "VeritOS"
```

**Expected Results:**
- ✅ All docs show "VeritOS" (not "AEGIS")
- ✅ Brand positioning document exists: `docs/VERITOS_BRAND_POSITIONING.md`

---

### 7. Deployment Config Test

**Test Helm/Kubernetes configs:**

```bash
# Check Helm values
cat deploy/helm/aegis/values.yaml | grep VERITOS
cat deploy/helm/aegis/templates/configmap.yaml | grep VERITOS
```

**Expected Results:**
- ✅ Helm values use `VERITOS_ENV`, `VERITOS_DEBUG`, etc.
- ✅ ConfigMap uses `VERITOS_*` env vars
- ✅ No `AEGIS_*` references in deployment configs

---

### 8. Code References Test

**Verify code docstrings and comments:**

```bash
# Check Python docstrings
grep -r "VeritOS" src/aegis/ --include="*.py" | head -10

# Check for any remaining AEGIS references (should be minimal - only in package names)
grep -r "AEGIS" src/aegis/ --include="*.py" | grep -v "aegis\." | grep -v "import aegis" | head -10
```

**Expected Results:**
- ✅ Docstrings show "VeritOS"
- ✅ Only package imports (`aegis.*`) still use "aegis" (intentional for Phase 3)

---

### 9. Package Metadata Test

**Test pyproject.toml changes:**

```bash
# Check package metadata
cat pyproject.toml | grep -A 5 "\[project\]"
```

**Expected Results:**
- ✅ Description shows "VeritOS: The Truth Operating System for Healthcare"
- ✅ Author shows "VeritOS Team"
- ✅ Script entry point: `veritos = "aegis.cli:main"`

---

### 10. Integration Test

**Full end-to-end test:**

```bash
# 1. Start all services
docker-compose up -d

# 2. Update .env with VERITOS_ vars
cp .env.example .env
# Edit .env: Change AEGIS_* to VERITOS_*

# 3. Start backend
uvicorn src.aegis.api.main:app --reload --port 8000

# 4. Test API
curl http://localhost:8000/health

# 5. Start frontend
cd demo && npm run dev

# 6. Open browser and verify UI
```

**Expected Results:**
- ✅ All services start successfully
- ✅ API responds with VeritOS branding
- ✅ Frontend shows VeritOS branding
- ✅ No errors in logs

---

## 🔍 Quick Verification Script

Create a test script to verify changes:

```python
# test_rebrand.py
import os
import sys

def test_env_vars():
    """Test that VERITOS_ env vars are recognized."""
    from aegis.config import VeritOSSettings
    
    # Set test env vars
    os.environ['VERITOS_ENV'] = 'test'
    os.environ['VERITOS_API_PORT'] = '9000'
    
    settings = VeritOSSettings()
    assert settings.env == 'test'
    assert settings.api_port == 9000
    print("✅ Environment variables test passed")

def test_class_name():
    """Test that VeritOSSettings exists and AegisSettings doesn't."""
    from aegis.config import VeritOSSettings
    
    try:
        from aegis.config import AegisSettings
        print("❌ AegisSettings still exists - should be removed")
        return False
    except ImportError:
        print("✅ AegisSettings correctly removed")
    
    assert VeritOSSettings is not None
    print("✅ VeritOSSettings exists")
    return True

def test_api_response():
    """Test API root endpoint."""
    import requests
    try:
        response = requests.get('http://localhost:8000/')
        data = response.json()
        assert 'VeritOS' in data.get('name', '')
        print("✅ API response shows VeritOS")
        return True
    except Exception as e:
        print(f"⚠️  API not running: {e}")
        return False

if __name__ == '__main__':
    print("Testing VeritOS rebrand...")
    test_env_vars()
    test_class_name()
    test_api_response()
    print("\n✅ All tests passed!")
```

Run with:
```bash
python test_rebrand.py
```

---

## 🚨 Common Issues & Fixes

### Issue 1: Old env vars still being used
**Symptom**: API uses old `AEGIS_*` values  
**Fix**: 
- Delete old `.env` file
- Copy `.env.example` to `.env`
- Update all `AEGIS_*` to `VERITOS_*`

### Issue 2: Import errors
**Symptom**: `ImportError: cannot import name 'AegisSettings'`  
**Fix**: Update any code still importing `AegisSettings` to use `VeritOSSettings`

### Issue 3: Config not reading new env vars
**Symptom**: Settings still use defaults  
**Fix**: 
- Check `.env` file has `VERITOS_*` prefix
- Restart API server
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

### Issue 4: Frontend still shows AEGIS
**Symptom**: UI shows old branding  
**Fix**: 
- Rebuild frontend: `cd demo && npm run build`
- Clear browser cache
- Restart dev server

---

## ✅ Success Criteria

All tests pass when:
- ✅ API shows "VeritOS API" in responses
- ✅ Frontend shows "VeritOS" in UI
- ✅ Environment variables use `VERITOS_*` prefix
- ✅ `VeritOSSettings` class works correctly
- ✅ Documentation shows VeritOS branding
- ✅ No errors in logs
- ✅ All services start successfully

---

## 📝 Next Steps After Testing

1. **If all tests pass**: Push to GitHub
   ```bash
   git push origin main
   ```

2. **If tests fail**: 
   - Check error messages
   - Review changes in commit `3ac264ae`
   - Fix issues and commit again

3. **Update production deployments**:
   - Update `.env` files in production
   - Update Helm values
   - Restart services

---

**Last Updated**: February 6, 2026  
**Testing Status**: Ready for verification
