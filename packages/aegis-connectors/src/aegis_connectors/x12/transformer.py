"""
X12 to Graph Transformer
"""

from datetime import datetime
import structlog

from aegis_connectors.x12.parser import ParsedX12

logger = structlog.get_logger(__name__)


class X12Transformer:
    """Transforms X12 transactions to graph vertices/edges."""
    
    def __init__(self, tenant_id: str, source_system: str = "x12"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def transform(self, parsed: ParsedX12) -> tuple[list[dict], list[dict]]:
        """Transform parsed X12 to vertices and edges."""
        vertices = []
        edges = []
        
        if parsed.transaction_type in ("837", "837P", "837I"):
            v, e = self._transform_837(parsed)
            vertices.extend(v)
            edges.extend(e)
        elif parsed.transaction_type == "835":
            v, e = self._transform_835(parsed)
            vertices.extend(v)
            edges.extend(e)
        
        return vertices, edges
    
    def _base_vertex(self, label: str, id_value: str) -> dict:
        return {
            "label": label,
            "id": id_value,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def _transform_837(self, parsed: ParsedX12) -> tuple[list[dict], list[dict]]:
        """Transform 837 claims."""
        vertices = []
        edges = []
        
        for claim in parsed.claims:
            claim_id = f"Claim/{claim['claim_id']}"
            
            claim_vertex = self._base_vertex("Claim", claim_id)
            claim_vertex.update({
                "claim_number": claim["claim_id"],
                "claim_type": "professional",
                "billed_amount": claim.get("total_charge", 0),
                "status": "submitted",
                "service_date": claim.get("service_date"),
            })
            vertices.append(claim_vertex)
            
            # Diagnoses
            for i, dx in enumerate(claim.get("diagnoses", [])):
                if dx.get("code"):
                    dx_id = f"Diagnosis/{claim['claim_id']}-{i}"
                    dx_vertex = self._base_vertex("Diagnosis", dx_id)
                    dx_vertex.update({
                        "code": dx["code"],
                        "sequence": i + 1,
                    })
                    vertices.append(dx_vertex)
                    
                    edges.append({
                        "label": "HAS_DIAGNOSIS",
                        "from_label": "Claim",
                        "from_id": claim_id,
                        "to_label": "Diagnosis",
                        "to_id": dx_id,
                        "tenant_id": self.tenant_id,
                    })
            
            # Service lines
            for i, svc in enumerate(claim.get("services", [])):
                svc_id = f"ClaimLine/{claim['claim_id']}-{i}"
                svc_vertex = self._base_vertex("ClaimLine", svc_id)
                svc_vertex.update({
                    "procedure_code": svc.get("procedure_code"),
                    "charge": svc.get("charge", 0),
                    "units": svc.get("units", 1),
                })
                vertices.append(svc_vertex)
                
                edges.append({
                    "label": "HAS_LINE",
                    "from_label": "Claim",
                    "from_id": claim_id,
                    "to_label": "ClaimLine",
                    "to_id": svc_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges
    
    def _transform_835(self, parsed: ParsedX12) -> tuple[list[dict], list[dict]]:
        """Transform 835 remittances."""
        vertices = []
        edges = []
        
        for remit in parsed.remittances:
            claim_id = f"Claim/{remit['claim_id']}"
            payment_id = f"Payment/{remit['claim_id']}"
            
            payment_vertex = self._base_vertex("ClaimPayment", payment_id)
            payment_vertex.update({
                "claim_id": remit["claim_id"],
                "status_code": remit.get("status_code"),
                "billed_amount": remit.get("total_charge", 0),
                "paid_amount": remit.get("paid_amount", 0),
                "patient_responsibility": remit.get("patient_responsibility", 0),
            })
            vertices.append(payment_vertex)
            
            edges.append({
                "label": "HAS_PAYMENT",
                "from_label": "Claim",
                "from_id": claim_id,
                "to_label": "ClaimPayment",
                "to_id": payment_id,
                "tenant_id": self.tenant_id,
            })
            
            # Adjustments
            for i, adj in enumerate(remit.get("adjustments", [])):
                adj_id = f"Adjustment/{remit['claim_id']}-{i}"
                adj_vertex = self._base_vertex("ClaimAdjustment", adj_id)
                adj_vertex.update({
                    "group_code": adj.get("group_code"),
                    "reason_code": adj.get("reason_code"),
                    "amount": adj.get("amount", 0),
                })
                vertices.append(adj_vertex)
                
                edges.append({
                    "label": "HAS_ADJUSTMENT",
                    "from_label": "ClaimPayment",
                    "from_id": payment_id,
                    "to_label": "ClaimAdjustment",
                    "to_id": adj_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges
