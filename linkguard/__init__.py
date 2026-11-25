"""linkguard package."""

from .api import (
    check_components,
    check_hardlink,
    inside,
    is_link,
    link_batch,
    real_path,
    safe_write,
    validate_policy,
)

__all__ = [
    "real_path",
    "is_link",
    "check_components",
    "check_hardlink",
    "inside",
    "safe_write",
    "validate_policy",
    "link_batch",
]