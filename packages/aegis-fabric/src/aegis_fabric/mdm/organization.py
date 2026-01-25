"""Organization Master Data Management"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Organization:
    id: str
    name: str
    org_type: str  # hospital, clinic, payer, lab
    npi: str | None = None
    tax_id: str | None = None
    parent_id: str | None = None
    addresses: list[dict] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)
    active: bool = True


class OrganizationMDM:
    """Organization Master Data Management."""
    
    def __init__(self):
        self._orgs: dict[str, Organization] = {}
        self._npi_index: dict[str, str] = {}
        self._tax_index: dict[str, str] = {}
    
    def register(self, org: Organization) -> str:
        """Register or update an organization."""
        self._orgs[org.id] = org
        if org.npi:
            self._npi_index[org.npi] = org.id
        if org.tax_id:
            self._tax_index[org.tax_id] = org.id
        return org.id
    
    def lookup_by_npi(self, npi: str) -> Organization | None:
        oid = self._npi_index.get(npi)
        return self._orgs.get(oid) if oid else None
    
    def lookup_by_tax_id(self, tax_id: str) -> Organization | None:
        oid = self._tax_index.get(tax_id)
        return self._orgs.get(oid) if oid else None
    
    def get_children(self, parent_id: str) -> list[Organization]:
        """Get child organizations."""
        return [o for o in self._orgs.values() if o.parent_id == parent_id]
    
    def search(self, name: str | None = None, org_type: str | None = None) -> list[Organization]:
        results = list(self._orgs.values())
        if name:
            results = [o for o in results if name.lower() in o.name.lower()]
        if org_type:
            results = [o for o in results if o.org_type == org_type]
        return results
