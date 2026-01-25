"""Provider Master Data Management"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Provider:
    id: str
    npi: str
    first_name: str
    last_name: str
    credentials: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    dea_number: str | None = None
    state_licenses: dict[str, str] = field(default_factory=dict)
    taxonomy_codes: list[str] = field(default_factory=list)
    active: bool = True


class ProviderMDM:
    """
    Provider Master Data Management.
    
    Manages provider golden records with NPI validation.
    """
    
    def __init__(self):
        self._providers: dict[str, Provider] = {}
        self._npi_index: dict[str, str] = {}
    
    def register(self, provider: Provider) -> str:
        """Register or update a provider."""
        # Check for existing by NPI
        existing_id = self._npi_index.get(provider.npi)
        if existing_id and existing_id != provider.id:
            # Merge with existing
            self._merge(existing_id, provider)
            return existing_id
        
        self._providers[provider.id] = provider
        self._npi_index[provider.npi] = provider.id
        return provider.id
    
    def lookup_by_npi(self, npi: str) -> Provider | None:
        """Look up provider by NPI."""
        provider_id = self._npi_index.get(npi)
        return self._providers.get(provider_id) if provider_id else None
    
    def search(self, name: str | None = None, specialty: str | None = None) -> list[Provider]:
        """Search providers."""
        results = list(self._providers.values())
        
        if name:
            name_lower = name.lower()
            results = [p for p in results if 
                      name_lower in p.first_name.lower() or 
                      name_lower in p.last_name.lower()]
        
        if specialty:
            results = [p for p in results if specialty in p.specialties]
        
        return results
    
    def _merge(self, existing_id: str, new: Provider):
        """Merge provider records."""
        existing = self._providers[existing_id]
        
        # Merge specialties
        for spec in new.specialties:
            if spec not in existing.specialties:
                existing.specialties.append(spec)
        
        # Merge organizations
        for org in new.organizations:
            if org not in existing.organizations:
                existing.organizations.append(org)
        
        # Update licenses
        existing.state_licenses.update(new.state_licenses)
