"""Proof registry: best-effort Postgres-backed evidence records (no LLM, no execution)."""

from .models import ProofRegistryRecordCreate, ProofRegistryRecordOut, ProofRegistryStatusResponse
from .service import (
    get_latest_proof_record,
    get_proof_registry_status,
    list_proof_records,
    save_proof_record,
)

__all__ = [
    "ProofRegistryRecordCreate",
    "ProofRegistryRecordOut",
    "ProofRegistryStatusResponse",
    "get_proof_registry_status",
    "save_proof_record",
    "list_proof_records",
    "get_latest_proof_record",
]

