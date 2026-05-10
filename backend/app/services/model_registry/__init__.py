"""Model role registry definitions for ML roles (metadata only; no training or artifact loading)."""

from app.services.model_registry.models import (
    ModelPromotionStatus,
    ModelRoleDefinition,
    ModelValidationRequirements,
)
from app.services.model_registry.registry import (
    get_model_role,
    iter_model_roles,
    list_model_role_keys,
)

__all__ = [
    "ModelPromotionStatus",
    "ModelRoleDefinition",
    "ModelValidationRequirements",
    "get_model_role",
    "iter_model_roles",
    "list_model_role_keys",
]
