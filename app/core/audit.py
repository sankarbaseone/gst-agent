from abc import ABC, abstractmethod
from typing import List
from app.schemas.audit import AuditLogEntry
import logging

logger = logging.getLogger(__name__)

class AuditRepository(ABC):
    @abstractmethod
    def save(self, entry: AuditLogEntry):
        pass

    @abstractmethod
    def get_all(self) -> List[AuditLogEntry]:
        pass

class InMemoryAuditRepository(AuditRepository):
    def __init__(self):
        self._storage: List[AuditLogEntry] = []

    def save(self, entry: AuditLogEntry):
        # Append-only, immutable by design (pydantic models are mutable by default but we generally treat them as such in store)
        self._storage.append(entry)
        logger.info(f"Audit Logged: {entry.json()}")

    def get_all(self) -> List[AuditLogEntry]:
        return list(self._storage)

# Global Accessor
audit_repo = InMemoryAuditRepository()
