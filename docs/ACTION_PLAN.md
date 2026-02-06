# AEGIS Platform - Prioritized Action Plan
**Created:** February 6, 2026  
**Timeline:** Next 4 Weeks

---

## 🎯 GOAL: Demo-Ready Platform

**Target:** Working local demo with real data flowing through the system by Week 2, AWS demo by Week 4.

---

## WEEK 1: Fix What's Broken (Phase 0)

### Day 1-2: Verify & Fix Data Flow

#### Task 1.1: End-to-End Data Flow Test
**Owner:** Backend Engineer  
**Effort:** 4 hours  
**Priority:** P0

**Steps:**
1. Start Docker Compose: `docker-compose up -d`
2. Load sample data: `python scripts/load_sample_data.py --patients 5`
3. Call Patient 360 API: `GET /api/v1/patients/{patient_id}`
4. Verify response includes:
   - Patient demographics ✅
   - Conditions ✅
   - Medications ✅
   - Encounters ✅
   - Claims ✅
   - Vitals ✅
   - Risk scores ✅

**Expected Issues:**
- Repositories may return empty arrays
- Database connections may fail
- Graph queries may not work

**Fix Strategy:**
- Check `get_patient_repo()` returns real repository (not mock)
- Verify PostgreSQL connection pool initialized
- Check graph client connects to JanusGraph
- Add logging to trace data flow

**Acceptance Criteria:**
- [ ] Patient 360 returns complete data for at least 1 patient
- [ ] All sections populated (not empty arrays)
- [ ] Risk scores calculated (not 0.0)

---

#### Task 1.2: Fix Repository Wiring
**Owner:** Backend Engineer  
**Effort:** 4 hours  
**Priority:** P0

**Problem:** Repositories may fall back to mocks when DB unavailable.

**Steps:**
1. Check `src/aegis/api/routes/patients.py` line 322: `repo = await get_patient_repo(request)`
2. Verify `get_patient_repo()` implementation
3. Ensure PostgreSQL pool initialized in `api/main.py`
4. Add error handling for DB connection failures
5. Remove mock fallbacks (or make them explicit)

**Files to Check:**
- `src/aegis/api/routes/patients.py`
- `src/aegis/db/clients.py`
- `src/aegis/api/main.py`

**Acceptance Criteria:**
- [ ] Repositories connect to real PostgreSQL
- [ ] No silent fallbacks to mocks
- [ ] Clear error messages if DB unavailable

---

#### Task 1.3: Verify Risk Score Calculation
**Owner:** Backend Engineer  
**Effort:** 2 hours  
**Priority:** P0

**Steps:**
1. Test with patient having:
   - Age > 65
   - Diabetes (E11)
   - Heart Failure (I50)
   - 5+ medications
2. Verify risk score > 0.0
3. Check risk level classification (low/medium/high)

**Files:**
- `src/aegis/db/postgres_repo.py` line 235 (`_calculate_risk_scores`)
- `src/aegis/api/routes/patients.py` line 209 (`_calculate_risk_scores`)

**Acceptance Criteria:**
- [ ] Risk scores calculated correctly
- [ ] Risk levels assigned properly
- [ ] Risk factors listed

---

### Day 3-4: Testing & Documentation

#### Task 1.4: Add End-to-End Tests
**Owner:** QA/Backend Engineer  
**Effort:** 6 hours  
**Priority:** P0

**Create:** `tests/test_e2e_patient_360.py`

```python
async def test_patient_360_end_to_end():
    """Test complete Patient 360 flow."""
    # 1. Load sample patient
    # 2. Call API
    # 3. Verify all sections
    # 4. Check risk scores
    pass
```

**Acceptance Criteria:**
- [ ] Test passes with real database
- [ ] All Patient 360 sections verified
- [ ] Test runs in CI/CD

---

#### Task 1.5: Create .env.example Documentation
**Owner:** DevOps  
**Effort:** 1 hour  
**Priority:** P1

**Verify:** `.env.example` exists and is complete

**Add to README:**
```markdown
## Environment Variables

Copy `.env.example` to `.env` and configure:

- `POSTGRES_URL`: PostgreSQL connection string
- `JANUSGRAPH_URL`: JanusGraph Gremlin endpoint
- `OPENSEARCH_URL`: OpenSearch endpoint
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka brokers
- `LLM_PROVIDER`: mock, bedrock, openai, anthropic
- `AWS_ACCESS_KEY_ID`: For Bedrock (if using)
```

**Acceptance Criteria:**
- [ ] `.env.example` has all required variables
- [ ] README explains configuration

---

### Day 5: Demo Data Enhancement

#### Task 1.6: Enhance Sample Data Script
**Owner:** Data Engineer  
**Effort:** 4 hours  
**Priority:** P1

**Enhance:** `scripts/load_sample_data.py`

**Add:**
- [ ] 20-50 realistic patients
- [ ] Complete conditions (10+ per patient)
- [ ] Medications (5-10 per patient)
- [ ] Lab results (recent + historical)
- [ ] Claims with denials
- [ ] Vitals (BP, weight, etc.)
- [ ] Encounters (inpatient, outpatient, ED)

**Acceptance Criteria:**
- [ ] Script generates 20+ patients
- [ ] Each patient has complete profile
- [ ] Data is realistic (not random)
- [ ] Can load in < 30 seconds

---

## WEEK 2: Local Demo Ready (Phase 1)

### Day 6-7: Infrastructure Verification

#### Task 2.1: Verify Docker Compose
**Owner:** DevOps  
**Effort:** 2 hours  
**Priority:** P0

**Steps:**
1. Run `docker-compose up -d`
2. Wait for all services healthy
3. Check logs for errors
4. Verify connections:
   - PostgreSQL: `psql -h localhost -p 5433 -U aegis -d aegis`
   - JanusGraph: `curl http://localhost:8182`
   - OpenSearch: `curl http://localhost:9200`
   - Kafka: `kafka-topics --bootstrap-server localhost:9092 --list`
   - Redis: `redis-cli -h localhost -p 6379 ping`

**Acceptance Criteria:**
- [ ] All services start successfully
- [ ] No errors in logs
- [ ] All health checks pass

---

#### Task 2.2: Database Initialization Scripts
**Owner:** Backend Engineer  
**Effort:** 4 hours  
**Priority:** P0

**Create:** `scripts/init-db.sql` (already exists, verify)

**Verify:**
- [ ] Tables created
- [ ] Indexes built
- [ ] Foreign keys set
- [ ] TimescaleDB hypertables created

**Create:** `scripts/init-graph.groovy` (for JanusGraph)

**Acceptance Criteria:**
- [ ] All databases initialized correctly
- [ ] Schema matches models
- [ ] Indexes optimize queries

---

#### Task 2.3: Health Check Endpoints
**Owner:** Backend Engineer  
**Effort:** 2 hours  
**Priority:** P0

**Enhance:** `GET /health` endpoint

**Add checks:**
- [ ] PostgreSQL connection
- [ ] JanusGraph connection
- [ ] OpenSearch connection
- [ ] Kafka connection
- [ ] Redis connection

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "postgres": "healthy",
    "janusgraph": "healthy",
    "opensearch": "healthy",
    "kafka": "healthy",
    "redis": "healthy"
  }
}
```

**Acceptance Criteria:**
- [ ] Health endpoint reports all services
- [ ] Shows connection status
- [ ] Used by monitoring

---

#### Task 2.4: Mock LLM Configuration
**Owner:** AI Engineer  
**Effort:** 3 hours  
**Priority:** P0

**Create:** Mock LLM provider that returns realistic responses

**Location:** `src/aegis/llm/mock.py`

**Features:**
- [ ] Returns structured responses (not errors)
- [ ] Configurable responses via templates
- [ ] Supports common agent queries
- [ ] No API key required

**Usage:**
```python
# .env
LLM_PROVIDER=mock
```

**Acceptance Criteria:**
- [ ] Agents work without API keys
- [ ] Responses are realistic
- [ ] Can demo agent functionality

---

### Day 8-9: Demo Scenarios

#### Task 2.5: Patient 360 Demo
**Owner:** Frontend/Backend  
**Effort:** 4 hours  
**Priority:** P1

**Verify:**
- [ ] Patient 360 endpoint returns complete data
- [ ] Frontend displays all sections
- [ ] Risk scores visible
- [ ] Patient status indicator works

**Demo Script:**
1. Load sample data
2. Navigate to Patient 360
3. Show all sections
4. Explain risk scores
5. Show patient status

**Acceptance Criteria:**
- [ ] Demo works end-to-end
- [ ] All data displays correctly
- [ ] No errors in console

---

#### Task 2.6: Denial Analytics Demo
**Owner:** Backend  
**Effort:** 2 hours  
**Priority:** P1

**Verify:**
- [ ] Denial analytics endpoint works
- [ ] Shows denial patterns
- [ ] Displays trends
- [ ] Generates insights

**Acceptance Criteria:**
- [ ] Demo shows denial patterns
- [ ] Data is realistic
- [ ] Insights are actionable

---

#### Task 2.7: Appeal Generation Demo
**Owner:** AI Engineer  
**Effort:** 4 hours  
**Priority:** P1

**Wire up:** Appeal generation with LLM

**Steps:**
1. Select a denied claim
2. Call appeal generation agent
3. Generate appeal letter
4. Show formatted output

**Acceptance Criteria:**
- [ ] Appeal letters generated
- [ ] Content is relevant
- [ ] Format is professional
- [ ] Works with mock LLM

---

### Day 10: Documentation

#### Task 2.8: Update Documentation
**Owner:** Technical Writer/DevOps  
**Effort:** 4 hours  
**Priority:** P1

**Update:**
- [ ] README.md - Setup instructions
- [ ] Create DEMO_GUIDE.md - Step-by-step demo
- [ ] Document known issues
- [ ] Add troubleshooting section

**Acceptance Criteria:**
- [ ] New developer can follow README
- [ ] Demo guide is clear
- [ ] Known issues documented

---

## WEEK 3-4: AWS Demo Ready (Phase 2)

### Week 3: AWS Infrastructure

#### Task 3.1: Terraform Infrastructure
**Owner:** DevOps  
**Effort:** 8 hours  
**Priority:** P1

**Verify:** `infrastructure/terraform/` exists

**Deploy:**
- [ ] VPC, subnets, security groups
- [ ] RDS PostgreSQL
- [ ] Neptune (or JanusGraph on EC2)
- [ ] OpenSearch domain
- [ ] MSK (Kafka)
- [ ] ElastiCache (Redis)
- [ ] ECS/Fargate cluster

**Acceptance Criteria:**
- [ ] Infrastructure deploys successfully
- [ ] All services accessible
- [ ] Costs within budget

---

#### Task 3.2: AWS Secrets Manager
**Owner:** DevOps  
**Effort:** 4 hours  
**Priority:** P1

**Configure:**
- [ ] Database credentials
- [ ] API keys (LLM providers)
- [ ] OAuth secrets (Epic, etc.)
- [ ] Encryption keys

**Acceptance Criteria:**
- [ ] Secrets stored securely
- [ ] Application reads from Secrets Manager
- [ ] No secrets in code/config

---

#### Task 3.3: Application Deployment
**Owner:** DevOps  
**Effort:** 8 hours  
**Priority:** P1

**Deploy:**
- [ ] ECS/Fargate task definition
- [ ] Application Load Balancer
- [ ] Auto-scaling configuration
- [ ] CloudWatch logging

**Acceptance Criteria:**
- [ ] Application runs in AWS
- [ ] Health checks pass
- [ ] Logs visible in CloudWatch

---

#### Task 3.4: Domain + HTTPS
**Owner:** DevOps  
**Effort:** 4 hours  
**Priority:** P1

**Configure:**
- [ ] Route 53 domain
- [ ] ACM certificate
- [ ] ALB HTTPS listener
- [ ] DNS records

**Acceptance Criteria:**
- [ ] https://demo.aegis-platform.com works
- [ ] SSL certificate valid
- [ ] No mixed content warnings

---

### Week 4: Authentication & Production Basics

#### Task 4.1: Cognito User Pool
**Owner:** Backend Engineer  
**Effort:** 4 hours  
**Priority:** P1

**Create:**
- [ ] Cognito user pool
- [ ] App client
- [ ] User groups (admin, clinician, patient)
- [ ] Password policy

**Acceptance Criteria:**
- [ ] Users can register/login
- [ ] JWT tokens validated
- [ ] Groups work correctly

---

#### Task 4.2: Login Page
**Owner:** Frontend Engineer  
**Effort:** 6 hours  
**Priority:** P1

**Create:**
- [ ] Login form
- [ ] Cognito integration
- [ ] Token storage
- [ ] Redirect after login

**Acceptance Criteria:**
- [ ] Users can log in
- [ ] Tokens stored securely
- [ ] Redirects work

---

#### Task 4.3: Demo User Accounts
**Owner:** DevOps  
**Effort:** 2 hours  
**Priority:** P1

**Create:**
- [ ] Admin user
- [ ] Clinician user
- [ ] Patient user (if needed)

**Acceptance Criteria:**
- [ ] Demo accounts created
- [ ] Credentials documented
- [ ] Can log in and use system

---

#### Task 4.4: CloudWatch Logs & Alarms
**Owner:** DevOps  
**Effort:** 4 hours  
**Priority:** P1

**Configure:**
- [ ] Application logging to CloudWatch
- [ ] Log groups and streams
- [ ] Alarms for errors
- [ ] Alarms for API downtime

**Acceptance Criteria:**
- [ ] Logs visible in CloudWatch
- [ ] Alarms trigger on errors
- [ ] Notifications configured

---

#### Task 4.5: Backup Strategy
**Owner:** DevOps  
**Effort:** 4 hours  
**Priority:** P1

**Configure:**
- [ ] RDS automated backups
- [ ] Neptune snapshots
- [ ] Backup retention policy
- [ ] Restore testing

**Acceptance Criteria:**
- [ ] Backups automated
- [ ] Retention policy set
- [ ] Can restore from backup

---

## 📊 SUCCESS METRICS

### Week 1 (Phase 0)
- ✅ All repositories return real data
- ✅ Patient 360 works end-to-end
- ✅ Risk scores calculated correctly
- ✅ End-to-end tests pass

### Week 2 (Phase 1)
- ✅ Docker Compose works perfectly
- ✅ Demo data loads successfully
- ✅ All demo scenarios work
- ✅ Mock LLM enables agent demos

### Week 3-4 (Phase 2)
- ✅ Application deployed to AWS
- ✅ HTTPS domain working
- ✅ Users can log in
- ✅ Demo accessible to partners

---

## 🚨 RISKS & MITIGATION

### Risk 1: Database Connections Fail
**Mitigation:** Test locally first, verify connection strings, add retry logic

### Risk 2: Sample Data Not Realistic
**Mitigation:** Use real FHIR examples, validate against schema

### Risk 3: AWS Deployment Delays
**Mitigation:** Start early, use existing Terraform, test incrementally

### Risk 4: Integration Testing Fails
**Mitigation:** Mock external services first, test integrations separately

---

## 📞 ESCALATION

**Blockers:** Escalate immediately to tech lead  
**Questions:** Use Slack/Teams channel  
**Status Updates:** Daily standup, weekly report

---

**Last Updated:** February 6, 2026  
**Next Review:** End of Week 1
