#!/usr/bin/env python3
"""
AEGIS End-to-End Test Suite

Verifies the complete Docker → API → DB flow:
1. Docker services are running
2. Database connections work
3. API endpoints respond correctly
4. Data flows from ingestion to query

Run: python scripts/e2e_test.py
"""

import asyncio
import sys
import httpx
import asyncpg
from datetime import datetime


# Configuration
API_BASE = "http://localhost:8001"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "aegis",
    "password": "aegis_dev_password",
    "database": "aegis",
}
OPENSEARCH_URL = "http://localhost:9200"
REDIS_URL = "redis://localhost:6379"
JANUSGRAPH_URL = "http://localhost:8182"


class TestResult:
    def __init__(self, name: str, passed: bool, message: str, duration_ms: int = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration_ms = duration_ms
    
    def __str__(self):
        icon = "✅" if self.passed else "❌"
        return f"{icon} {self.name}: {self.message} ({self.duration_ms}ms)"


async def test_api_health() -> TestResult:
    """Test 1: API Health Check"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE}/health")
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    "API Health",
                    True,
                    f"Status: {data.get('status', 'unknown')}",
                    duration
                )
            else:
                return TestResult(
                    "API Health",
                    False,
                    f"HTTP {response.status_code}",
                    duration
                )
    except Exception as e:
        return TestResult("API Health", False, f"Connection failed: {e}", 0)


async def test_postgres_connection() -> TestResult:
    """Test 2: PostgreSQL Connection"""
    start = datetime.now()
    try:
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        patient_count = await conn.fetchval("SELECT COUNT(*) FROM patients")
        
        await conn.close()
        duration = int((datetime.now() - start).total_seconds() * 1000)
        
        return TestResult(
            "PostgreSQL",
            True,
            f"Connected. {patient_count} patients in DB",
            duration
        )
    except Exception as e:
        return TestResult("PostgreSQL", False, f"Connection failed: {e}", 0)


async def test_postgres_seed_data() -> TestResult:
    """Test 3: Verify Seed Data Exists"""
    start = datetime.now()
    try:
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        
        counts = {}
        tables = ["patients", "conditions", "medications", "encounters", "claims", "denials"]
        
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            counts[table] = count
        
        await conn.close()
        duration = int((datetime.now() - start).total_seconds() * 1000)
        
        # Check minimum counts
        if counts["patients"] >= 20 and counts["conditions"] >= 10 and counts["denials"] >= 5:
            summary = ", ".join([f"{k}:{v}" for k, v in counts.items()])
            return TestResult("Seed Data", True, summary, duration)
        else:
            return TestResult("Seed Data", False, f"Insufficient data: {counts}", duration)
    
    except Exception as e:
        return TestResult("Seed Data", False, f"Query failed: {e}", 0)


async def test_api_patients() -> TestResult:
    """Test 4: Patient List API"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE}/v1/patients")
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("total", 0)
                patients = data.get("patients", [])
                return TestResult(
                    "Patient API",
                    count > 0,
                    f"Found {count} patients" if count > 0 else "No patients returned",
                    duration
                )
            else:
                return TestResult("Patient API", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("Patient API", False, f"Request failed: {e}", 0)


async def test_patient_360() -> TestResult:
    """Test 5: Patient 360 View API"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First get a patient ID
            list_response = await client.get(f"{API_BASE}/v1/patients")
            if list_response.status_code != 200:
                return TestResult("Patient 360", False, "Could not list patients", 0)
            
            patients = list_response.json().get("patients", [])
            if not patients:
                return TestResult("Patient 360", False, "No patients to test", 0)
            
            patient_id = patients[0].get("id")
            
            # Get 360 view
            response = await client.get(f"{API_BASE}/v1/patients/{patient_id}")
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                sections = []
                if data.get("patient"): sections.append("patient")
                if data.get("conditions"): sections.append("conditions")
                if data.get("medications"): sections.append("meds")
                if data.get("encounters"): sections.append("encounters")
                if data.get("claims"): sections.append("claims")
                if data.get("risk_scores"): sections.append("risk")
                if data.get("patient_status"): sections.append("status")
                
                return TestResult(
                    "Patient 360",
                    len(sections) >= 5,
                    f"Sections: {', '.join(sections)}",
                    duration
                )
            else:
                return TestResult("Patient 360", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("Patient 360", False, f"Request failed: {e}", 0)


async def test_denials_api() -> TestResult:
    """Test 6: Denials API"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE}/v1/denials")
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("total", 0)
                return TestResult(
                    "Denials API",
                    count > 0,
                    f"Found {count} denials",
                    duration
                )
            else:
                return TestResult("Denials API", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("Denials API", False, f"Request failed: {e}", 0)


async def test_denial_analytics() -> TestResult:
    """Test 7: Denial Analytics API"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE}/v1/denials/analytics")
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total_denied_amount", 0)
                return TestResult(
                    "Denial Analytics",
                    True,
                    f"Total denied: ${total:,.2f}",
                    duration
                )
            else:
                return TestResult("Denial Analytics", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("Denial Analytics", False, f"Request failed: {e}", 0)


async def test_ml_denial_prediction() -> TestResult:
    """Test 8: ML Denial Prediction"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            test_claim = {
                "claim": {
                    "id": "test-001",
                    "claim_type": "professional",
                    "diagnoses": ["M54.5", "G89.29"],
                    "lines": [
                        {"cpt": "99215", "charge": 250},
                        {"cpt": "97110", "charge": 75}
                    ],
                    "payer_type": "commercial",
                    "has_prior_auth": False,
                    "in_network": True,
                }
            }
            
            response = await client.post(
                f"{API_BASE}/v1/ml/predict/denial",
                json=test_claim
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                prob = data.get("denial_probability", 0)
                level = data.get("risk_level", "unknown")
                return TestResult(
                    "ML Prediction",
                    True,
                    f"Risk: {level} ({prob*100:.1f}%)",
                    duration
                )
            else:
                return TestResult("ML Prediction", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("ML Prediction", False, f"Request failed: {e}", 0)


async def test_phi_detection() -> TestResult:
    """Test 9: PHI Detection"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/security/phi/detect",
                json={
                    "text": "Patient John Smith, SSN 123-45-6789, DOB 01/15/1980",
                    "sensitivity": "high"
                }
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get("match_count", 0)
                types = data.get("phi_types", [])
                return TestResult(
                    "PHI Detection",
                    matches > 0,
                    f"Found {matches} PHI: {', '.join(types)}",
                    duration
                )
            else:
                return TestResult("PHI Detection", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("PHI Detection", False, f"Request failed: {e}", 0)


async def test_rag_ingest() -> TestResult:
    """Test 10: RAG Ingestion"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/rag/ingest/text",
                json={
                    "text": "Medicare covers physical therapy when ordered by a physician. Prior authorization may be required for extended treatment.",
                    "title": "E2E Test Policy",
                    "source": "e2e_test"
                }
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                chunks = data.get("chunks_created", 0)
                return TestResult(
                    "RAG Ingest",
                    chunks > 0,
                    f"Created {chunks} chunks",
                    duration
                )
            else:
                return TestResult("RAG Ingest", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("RAG Ingest", False, f"Request failed: {e}", 0)


async def test_opensearch() -> TestResult:
    """Test 11: OpenSearch Connection"""
    start = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENSEARCH_URL)
            duration = int((datetime.now() - start).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", {}).get("number", "unknown")
                return TestResult("OpenSearch", True, f"Version {version}", duration)
            else:
                return TestResult("OpenSearch", False, f"HTTP {response.status_code}", duration)
    except Exception as e:
        return TestResult("OpenSearch", False, f"Connection failed: {e}", 0)


async def test_redis() -> TestResult:
    """Test 12: Redis Connection"""
    start = datetime.now()
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(REDIS_URL)
        pong = await client.ping()
        await client.close()
        
        duration = int((datetime.now() - start).total_seconds() * 1000)
        return TestResult("Redis", pong, "Connected", duration)
    except ImportError:
        return TestResult("Redis", False, "redis package not installed", 0)
    except Exception as e:
        return TestResult("Redis", False, f"Connection failed: {e}", 0)


async def run_all_tests():
    """Run all E2E tests"""
    print("\n" + "=" * 60)
    print("AEGIS End-to-End Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Infrastructure", [
            test_api_health,
            test_postgres_connection,
            test_opensearch,
            test_redis,
        ]),
        ("Data Layer", [
            test_postgres_seed_data,
        ]),
        ("API Endpoints", [
            test_api_patients,
            test_patient_360,
            test_denials_api,
            test_denial_analytics,
        ]),
        ("AI/ML Features", [
            test_ml_denial_prediction,
            test_phi_detection,
            test_rag_ingest,
        ]),
    ]
    
    all_results = []
    
    for category, test_funcs in tests:
        print(f"\n📋 {category}")
        print("-" * 40)
        
        for test_func in test_funcs:
            result = await test_func()
            all_results.append(result)
            print(f"   {result}")
    
    # Summary
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n   ✅ Passed: {passed}/{total}")
    print(f"   ❌ Failed: {failed}/{total}")
    
    if failed == 0:
        print("\n   🎉 All tests passed! Platform is ready for demos.\n")
        return 0
    else:
        print(f"\n   ⚠️  {failed} test(s) failed. Check the issues above.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
