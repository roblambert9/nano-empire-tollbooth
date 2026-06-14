"""nano_empire_tollbooth — Monetize any Python function with one decorator."""

from .rails import RAILS, RailAdapter, get_rail
from .settlement import SettlementResult, settle
from .license import (
    LicenseClaim,
    describe_license,
    issue_license,
    make_keypair,
    verify_license,
)
from .pro import (
    get_license,
    license_claim,
    license_status,
    pro_enabled,
    set_license,
    tier,
)
from .tollbooth import (
    SettlementStatus,
    TollRecord,
    Tollbooth,
    TollboothConfig,
    TollboothMode,
    create_tollbooth,
    get_tollbooth,
    get_usage,
    monetize,
    reset_tollbooth,
    reset_usage,
)

__all__ = [
    "RAILS", "RailAdapter", "get_rail", "SettlementResult", "settle",
    "SettlementStatus",
    "TollRecord",
    "Tollbooth",
    "TollboothConfig",
    "TollboothMode",
    "create_tollbooth",
    "get_tollbooth",
    "get_usage",
    "monetize",
    "reset_tollbooth",
    "reset_usage",
    "set_license",
    "get_license",
    "license_claim",
    "license_status",
    "pro_enabled",
    "tier",
    "LicenseClaim",
    "verify_license",
    "issue_license",
    "make_keypair",
    "describe_license",
]

__version__ = "0.3.0"
