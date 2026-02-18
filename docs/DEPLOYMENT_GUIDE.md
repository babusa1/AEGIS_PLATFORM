# VeritOS Deployment Guide

**Complete guide for deploying VeritOS - Docker, Vercel, and Production**

---

## 🎯 Deployment Options

### Option 1: Docker (Local Testing) ✅ Recommended for Testing
- **Best for**: Local development, testing, demos
- **Backend**: FastAPI on Docker
- **Frontend**: Next.js locally or Docker
- **Pros**: Full control, all services, easy testing
- **Cons**: Requires local Docker setup

### Option 2: Vercel (Frontend) + Backend Service ✅ Recommended for Investor Demo
- **Best for**: Investor demos, quick frontend deployment
- **Frontend**: Deploy to Vercel (free tier available)
- **Backend**: Deploy to Railway/Render/AWS (separate)
- **Pros**: Professional URL, fast, easy updates
- **Cons**: Backend needs separate deployment

### Option 3: Full Production (AWS/Kubernetes)
- **Best for**: Production deployments
- **Backend**: AWS ECS/EKS, Railway, Render
- **Frontend**: Vercel, AWS CloudFront
- **Pros**: Scalable, production-ready
- **Cons**: More complex setup

---

## 🐳 Option 1: Docker Deployment (Local Testing)

### Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Wait for services (30-60 seconds)
docker-compose ps

# 3. Initialize database
psql -h localhost -p 5433 -U aegis -d aegis -f scripts/init-db.sql

# 4. Create .env file
cp .env.example .env
# Edit .env with your settings

# 5. Start backend
pip install -e .
uvicorn src.aegis.api.main:app --reload --port 8000

# 6. Start frontend (new terminal)
cd demo
npm install
npm run dev
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

### Testing Checklist

- [ ] All Docker containers running (`docker-compose ps`)
- [ ] API responds: `curl http://localhost:8000/health`
- [ ] Frontend loads: http://localhost:3000
- [ ] Sidebar shows "VeritOS" (not "AEGIS")
- [ ] API docs show "VeritOS API"

---

## 🚀 Option 2: Vercel Deployment (Frontend)

### Prerequisites

- Vercel account (free tier works)
- Backend API deployed somewhere (Railway/Render/AWS)
- GitHub repository connected

### Step 1: Deploy Backend API

**Option A: Railway (Easiest)**

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Deploy
railway up
```

**Option B: Render**

1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn src.aegis.api.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables from `.env.example`

**Option C: AWS (Production)**

- Use AWS ECS/Fargate
- Or AWS Elastic Beanstalk
- Or AWS App Runner

### Step 2: Deploy Frontend to Vercel

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Navigate to demo folder
cd demo

# 3. Deploy
vercel

# 4. Follow prompts:
# - Link to existing project? No
# - Project name: veritos-demo
# - Directory: ./
# - Override settings? No
```

### Step 3: Configure Environment Variables

**In Vercel Dashboard:**

1. Go to your project → Settings → Environment Variables
2. Add:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.com
   ```

**Or via CLI:**
```bash
vercel env add NEXT_PUBLIC_API_URL
# Enter: https://your-backend-url.com
```

### Step 4: Update Frontend API Configuration

Create `demo/.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

Update `demo/src/lib/api.ts` (if exists) or create it:
```typescript
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### Step 5: Update Metadata

Update `demo/src/app/layout.tsx`:
```typescript
export const metadata: Metadata = {
  title: 'VeritOS - Healthcare Intelligence Platform',
  description: 'The Truth Operating System for Healthcare',
}
```

### Step 6: Deploy

```bash
cd demo
vercel --prod
```

**Your frontend will be live at:** `https://veritos-demo.vercel.app`

---

## 📊 Testing Summary

### What Works ✅

1. **Backend API**
   - ✅ FastAPI server runs
   - ✅ Health check endpoint works
   - ✅ API documentation available
   - ✅ All routes functional

2. **Frontend Dashboard**
   - ✅ Next.js app loads
   - ✅ Sidebar navigation works
   - ✅ Dashboard pages render
   - ✅ VeritOS branding visible

3. **Data Moat**
   - ✅ 30+ entity types queryable
   - ✅ Generic entity query API works
   - ✅ Time-series support functional

4. **AI Agents**
   - ✅ Agent endpoints available
   - ✅ Agent execution works
   - ✅ Multi-agent orchestration functional

5. **Integrations**
   - ✅ FHIR/HL7 connectors ready
   - ✅ CDS Hooks integration available
   - ✅ Epic SMART-on-FHIR ready

### What to Test 🔍

1. **API Health**
   ```bash
   curl https://your-api-url.com/health
   ```

2. **Frontend Load**
   - Open deployed URL
   - Check sidebar shows "VeritOS"
   - Navigate through pages

3. **API Integration**
   - Check browser console for API calls
   - Verify no CORS errors
   - Test API endpoints from frontend

---

## 🎯 Investor Demo Deployment Strategy

### Recommended Setup

**Frontend:** Vercel (Free tier)
- URL: `https://veritos-demo.vercel.app`
- Fast, professional, easy to update

**Backend:** Railway (Free tier) or Render
- URL: `https://veritos-api.railway.app`
- Easy deployment, auto-scaling

**Demo Data:** Pre-populated
- Use sample data scripts
- Show real functionality

### Quick Deploy Script

```bash
#!/bin/bash
# deploy-demo.sh

echo "🚀 Deploying VeritOS Demo..."

# 1. Deploy backend
echo "Deploying backend..."
cd aegis
railway up

# 2. Deploy frontend
echo "Deploying frontend..."
cd demo
vercel --prod

echo "✅ Deployment complete!"
echo "Frontend: https://veritos-demo.vercel.app"
echo "Backend: Check Railway dashboard"
```

---

## 🔧 Troubleshooting

### Frontend can't connect to backend

**Issue:** CORS errors or connection refused

**Fix:**
1. Check `NEXT_PUBLIC_API_URL` is set correctly
2. Verify backend CORS allows frontend domain
3. Check backend is running and accessible

### Environment variables not working

**Issue:** Frontend uses wrong API URL

**Fix:**
1. Check `.env.local` exists in `demo/` folder
2. Restart Vercel deployment
3. Verify env vars in Vercel dashboard

### Backend deployment fails

**Issue:** Build errors or runtime errors

**Fix:**
1. Check `requirements.txt` is complete
2. Verify Python version (3.11+)
3. Check logs in deployment platform

---

## 📝 Pre-Deployment Checklist

- [ ] `.env.example` updated with `VERITOS_*` vars
- [ ] Frontend metadata updated to VeritOS
- [ ] API URL configured correctly
- [ ] CORS configured for frontend domain
- [ ] Database initialized (if needed)
- [ ] Sample data loaded (for demo)
- [ ] All tests passing locally
- [ ] Documentation updated

---

## 🎉 Post-Deployment

### Verify Deployment

1. **Backend:**
   ```bash
   curl https://your-api-url.com/health
   curl https://your-api-url.com/
   ```

2. **Frontend:**
   - Open deployed URL
   - Check console for errors
   - Test navigation
   - Verify API calls work

3. **Integration:**
   - Test API endpoints from frontend
   - Verify data loads correctly
   - Check for CORS issues

---

**Last Updated**: February 6, 2026  
**Status**: Ready for deployment
