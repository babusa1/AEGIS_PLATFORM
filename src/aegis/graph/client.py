"""
Graph Database Client

Gremlin client for Neptune/JanusGraph with connection pooling and retry logic.
Falls back to mock data when no database is available.
"""

from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from aegis.config import get_settings

logger = structlog.get_logger(__name__)

# Try to import gremlin - may not be available in all environments
try:
    from gremlin_python.driver import client, serializer
    from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
    from gremlin_python.process.anonymous_traversal import traversal
    from gremlin_python.process.graph_traversal import GraphTraversalSource
    GREMLIN_AVAILABLE = True
except ImportError:
    GREMLIN_AVAILABLE = False
    logger.warning("gremlinpython not available, using mock graph client")


class GraphClient:
    """
    Gremlin graph database client.
    
    Supports both Neptune and JanusGraph (for local development).
    Falls back to mock mode when no database is available.
    
    Usage:
        async with GraphClient() as client:
            result = await client.execute("g.V().count()")
    """
    
    def __init__(self):
        self.settings = get_settings().graph_db
        self._client = None
        self._g = None
        self._mock_mode = False
        self._mock_data = MockGraphData()
    
    @property
    def connection_url(self) -> str:
        """Get the Gremlin connection URL."""
        return self.settings.connection_url
    
    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode
    
    async def connect(self) -> None:
        """Establish connection to the graph database."""
        if not GREMLIN_AVAILABLE:
            logger.warning("Gremlin not available, using mock mode")
            self._mock_mode = True
            return
        
        try:
            logger.info(
                "Connecting to graph database",
                url=self.connection_url,
            )
            
            self._client = client.Client(
                self.connection_url,
                "g",
                message_serializer=serializer.GraphSONSerializersV3d0(),
            )
            
            # Also create a traversal source for fluent API
            connection = DriverRemoteConnection(
                self.connection_url,
                "g",
            )
            self._g = traversal().withRemote(connection)
            
            # Test connection
            self._client.submit("g.V().limit(1).count()").all().result()
            
            logger.info("Connected to graph database")
            
        except Exception as e:
            logger.warning("Failed to connect to graph database, using mock mode", error=str(e))
            self._mock_mode = True
            self._client = None
            self._g = None
    
    async def disconnect(self) -> None:
        """Close the graph database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._g = None
            logger.info("Disconnected from graph database")
    
    async def __aenter__(self) -> "GraphClient":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
    
    @property
    def g(self) -> GraphTraversalSource:
        """Get the Gremlin traversal source for fluent queries."""
        if self._g is None:
            raise RuntimeError("Graph client not connected. Call connect() first.")
        return self._g
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def execute(self, query: str, bindings: dict[str, Any] | None = None) -> list[Any]:
        """
        Execute a Gremlin query string.
        
        Args:
            query: Gremlin query string
            bindings: Optional parameter bindings
            
        Returns:
            List of results
        """
        # Use mock data if in mock mode
        if self._mock_mode:
            return self._mock_data.execute_mock(query, bindings or {})
        
        if self._client is None:
            raise RuntimeError("Graph client not connected. Call connect() first.")
        
        logger.debug("Executing Gremlin query", query=query[:100])
        
        try:
            result_set = self._client.submit(query, bindings or {})
            results = result_set.all().result()
            return results
        except Exception as e:
            logger.error("Gremlin query failed", query=query[:100], error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check if the graph database is healthy."""
        if self._mock_mode:
            return True
        try:
            result = await self.execute("g.V().limit(1).count()")
            return True
        except Exception:
            return False


# Singleton instance for the application
_graph_client: GraphClient | None = None


async def get_graph_client() -> GraphClient:
    """Get the singleton graph client instance."""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphClient()
        await _graph_client.connect()
    return _graph_client


async def close_graph_client() -> None:
    """Close the singleton graph client."""
    global _graph_client
    if _graph_client is not None:
        await _graph_client.disconnect()
        _graph_client = None


# =============================================================================
# Mock Data for Demo/Development
# =============================================================================

class MockGraphData:
    """
    Provides realistic mock data when no graph database is available.
    This enables demos without running JanusGraph.
    """
    
    def __init__(self):
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample patient data with 20 patients."""
        # Patient data
        patient_data = [
            ("John", "Smith", "1958-03-15", "male", "Boston"),
            ("Mary", "Johnson", "1965-07-22", "female", "Cambridge"),
            ("Robert", "Williams", "1972-11-08", "male", "Somerville"),
            ("Patricia", "Brown", "1980-01-30", "female", "Newton"),
            ("Michael", "Davis", "1955-09-12", "male", "Brookline"),
            ("Jennifer", "Miller", "1968-04-18", "female", "Quincy"),
            ("William", "Wilson", "1950-12-03", "male", "Medford"),
            ("Elizabeth", "Moore", "1975-08-25", "female", "Arlington"),
            ("David", "Taylor", "1962-06-14", "male", "Watertown"),
            ("Barbara", "Anderson", "1978-02-09", "female", "Waltham"),
            ("Richard", "Thomas", "1948-11-22", "male", "Malden"),
            ("Susan", "Jackson", "1983-09-30", "female", "Revere"),
            ("Joseph", "White", "1970-05-07", "male", "Chelsea"),
            ("Margaret", "Harris", "1959-01-19", "female", "Everett"),
            ("Charles", "Martin", "1945-07-28", "male", "Lynn"),
            ("Dorothy", "Garcia", "1988-03-12", "female", "Salem"),
            ("Thomas", "Martinez", "1967-10-05", "male", "Peabody"),
            ("Lisa", "Robinson", "1973-12-17", "female", "Beverly"),
            ("Daniel", "Clark", "1952-08-21", "male", "Gloucester"),
            ("Nancy", "Rodriguez", "1981-04-03", "female", "Marblehead"),
        ]
        
        self.patients = []
        for i, (first, last, dob, gender, city) in enumerate(patient_data, 1):
            self.patients.append({
                "id": [f"patient-{i:03d}"], "mrn": [f"MRN{1000+i:06d}"], "tenant_id": ["default"],
                "given_name": [first], "family_name": [last], "birth_date": [dob],
                "gender": [gender], "phone": [f"555-{100+i:03d}-{1000+i:04d}"],
                "email": [f"{first.lower()}.{last.lower()}@email.com"],
                "address_city": [city], "address_state": ["MA"]
            })
        
        # Generate encounters for all patients
        self.encounters = {}
        enc_id = 1
        for i in range(1, 21):
            pid = f"patient-{i:03d}"
            self.encounters[pid] = []
            # Each patient gets 1-3 encounters
            num_enc = (i % 3) + 1
            for j in range(num_enc):
                month = ((i + j) % 12) + 1
                self.encounters[pid].append({
                    "encounter": {
                        "id": f"enc-{enc_id:03d}",
                        "type": [["outpatient", "inpatient", "emergency"][j % 3]],
                        "status": ["finished"],
                        "admit_date": [f"2024-{month:02d}-{(i % 28) + 1:02d}"],
                        "discharge_date": [f"2024-{month:02d}-{(i % 28) + 2:02d}"]
                    },
                    "diagnoses": [{"code": "E11.9", "display": "Type 2 Diabetes"}] if i % 3 == 0 else [],
                    "procedures": [{"code": "99213", "display": "Office Visit"}] if j == 0 else []
                })
                enc_id += 1
        
        # Generate claims
        self.claims = {}
        claim_id = 1
        for i in range(1, 21):
            pid = f"patient-{i:03d}"
            self.claims[pid] = []
            # Some patients have denied claims
            status = "denied" if i % 5 == 0 else "paid"
            billed = 1000 + (i * 100)
            paid = 0 if status == "denied" else billed * 0.8
            self.claims[pid].append({
                "claim": {
                    "id": f"claim-{claim_id:03d}",
                    "claim_number": [f"CLM-2024-{claim_id:03d}"],
                    "type": ["professional"],
                    "status": [status],
                    "billed_amount": [billed],
                    "paid_amount": [paid]
                },
                "denials": [{"reason_code": ["CO-4"], "reason": "Service not covered"}] if status == "denied" else []
            })
            claim_id += 1
        
        # Common medications
        med_options = [
            ("Metformin 500mg", "860975", "twice daily"),
            ("Lisinopril 10mg", "314076", "once daily"),
            ("Amlodipine 5mg", "197361", "once daily"),
            ("Atorvastatin 20mg", "310798", "once daily"),
            ("Omeprazole 20mg", "312961", "once daily"),
            ("Aspirin 81mg", "198440", "once daily"),
        ]
        
        self.medications = {}
        med_id = 1
        for i in range(1, 21):
            pid = f"patient-{i:03d}"
            self.medications[pid] = []
            # Each patient gets 1-4 medications
            num_meds = (i % 4) + 1
            for j in range(num_meds):
                med = med_options[(i + j) % len(med_options)]
                self.medications[pid].append({
                    "id": f"med-{med_id:03d}",
                    "code": med[1],
                    "display": med[0],
                    "status": "active",
                    "dosage": med[2]
                })
                med_id += 1
        
        # Common conditions
        cond_options = [
            ("E11.9", "Type 2 Diabetes Mellitus"),
            ("I10", "Essential Hypertension"),
            ("E78.5", "Hyperlipidemia"),
            ("J45.909", "Asthma"),
            ("N18.3", "Chronic Kidney Disease Stage 3"),
            ("I50.9", "Heart Failure"),
            ("J44.9", "COPD"),
            ("F32.9", "Major Depressive Disorder"),
        ]
        
        self.conditions = {}
        cond_id = 1
        for i in range(1, 21):
            pid = f"patient-{i:03d}"
            self.conditions[pid] = []
            # Each patient gets 1-4 conditions based on age/profile
            num_conds = (i % 4) + 1
            for j in range(num_conds):
                cond = cond_options[(i + j) % len(cond_options)]
                self.conditions[pid].append({
                    "id": f"cond-{cond_id:03d}",
                    "code": cond[0],
                    "display": cond[1],
                    "status": "active"
                })
                cond_id += 1
    
    def _extract_patient_id(self, query: str, bindings: dict) -> str:
        """Extract patient_id from query or bindings."""
        # First check bindings
        if "patient_id" in bindings:
            return bindings["patient_id"]
        
        # Try to extract from query string (e.g., g.V('patient-001'))
        import re
        match = re.search(r"g\.V\(['\"]?(patient-\d+)['\"]?\)", query)
        if match:
            return match.group(1)
        
        # Default
        return "patient-001"
    
    def execute_mock(self, query: str, bindings: dict) -> list:
        """Execute a mock query and return sample data."""
        query_lower = query.lower()
        
        # Extract patient_id for queries that need it
        patient_id = self._extract_patient_id(query, bindings)
        
        # Patient list query
        if "haslabel('patient')" in query_lower and "valuemap" in query_lower:
            if patient_id != "patient-001" or "patient_id" in bindings:
                # Single patient lookup
                for p in self.patients:
                    if p["id"][0] == patient_id:
                        return [p]
                return []
            return self.patients
        
        # Single patient by ID (g.V(patient_id).valueMap)
        if "g.v(" in query_lower and "valuemap" in query_lower:
            for p in self.patients:
                if p["id"][0] == patient_id:
                    return [p]
            return []
        
        # Patient count
        if "haslabel('patient')" in query_lower and "count()" in query_lower:
            return [len(self.patients)]
        
        # Patient 360 - encounters
        if "has_encounter" in query_lower or "out('has_encounter')" in query_lower.replace(" ", ""):
            return self.encounters.get(patient_id, [])
        
        # Claims
        if "billed_for" in query_lower:
            return self.claims.get(patient_id, [])
        
        # Medications
        if "has_medication" in query_lower:
            return self.medications.get(patient_id, [])
        
        # Conditions
        if "has_condition" in query_lower:
            return self.conditions.get(patient_id, [])
        
        # Denied claims
        if "status" in query_lower and "denied" in query_lower:
            denied = []
            for pid, claims in self.claims.items():
                for c in claims:
                    if c["claim"].get("status", [""])[0] == "denied":
                        denied.append(c)
            return denied
        
        # Default: empty result
        logger.debug("Mock query returned empty", query=query[:80])
        return []
