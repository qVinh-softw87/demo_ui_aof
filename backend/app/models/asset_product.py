from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssetClass(StrEnum):
    CASH = "CASH"
    GOLD = "GOLD"
    SILVER = "SILVER"
    DEPOSIT = "DEPOSIT"
    EQUITY = "EQUITY"
    ETF = "ETF"
    BOND_FUND = "BOND_FUND"
    GOVERNMENT_BOND_REFERENCE = "GOVERNMENT_BOND_REFERENCE"


class AllocationRuleType(StrEnum):
    FIXED_RETURN = "FIXED_RETURN"
    WHOLE_BALANCE_TIER = "WHOLE_BALANCE_TIER"
    MARGINAL_BAND = "MARGINAL_BAND"
    DISCRETE_UNIT = "DISCRETE_UNIT"
    PIECEWISE_COST = "PIECEWISE_COST"


class QualifyingBalanceScope(StrEnum):
    PER_CONTRACT = "PER_CONTRACT"
    TOTAL_NEW_MONEY = "TOTAL_NEW_MONEY"
    BANK_RELATIONSHIP = "BANK_RELATIONSHIP"
    CUSTOMER_AUM = "CUSTOMER_AUM"


class RightsStatus(StrEnum):
    APPROVED = "APPROVED"
    RESTRICTED = "RESTRICTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class ValueProvenance(StrEnum):
    LICENSED_FEED = "LICENSED_FEED"
    OFFICIAL_API = "OFFICIAL_API"
    MANUAL_VERIFIED = "MANUAL_VERIFIED"
    USER_REPORTED = "USER_REPORTED"
    DERIVED = "DERIVED"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class RoundingRule(StrEnum):
    NONE = "NONE"
    VND_1K = "VND_1K"
    VND_10K = "VND_10K"
    VND_100K = "VND_100K"
    VND_1M = "VND_1M"
    WHOLE_UNIT = "WHOLE_UNIT"
    BOARD_LOT_100 = "BOARD_LOT_100"


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]


class AllocationSegment(BaseModel):
    """Feasible allocation segment for amount-dependent products."""

    model_config = ConfigDict(extra="forbid")

    lower_bound: float = Field(ge=0)
    upper_bound: float | None = Field(default=None, gt=0)
    return_rate: float | None = Field(
        default=None,
        description="Annualized expected return/rate as decimal, e.g. 0.052 for 5.2%.",
    )
    cost: float = Field(default=0, ge=0)
    condition: str | None = None

    @model_validator(mode="after")
    def upper_must_exceed_lower(self) -> "AllocationSegment":
        if self.upper_bound is not None and self.upper_bound <= self.lower_bound:
            raise ValueError("upper_bound must be greater than lower_bound")
        return self


class UncertaintyBounds(BaseModel):
    """Optional uncertainty interval attached to user-reported or derived data."""

    model_config = ConfigDict(extra="forbid")

    lower: float | None = None
    upper: float | None = None
    confidence_level: float | None = Field(default=None, ge=0, le=1)
    note: str | None = None


class AssetProduct(BaseModel):
    """Canonical product schema shared by all asset agents and the optimizer."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    asset_class: AssetClass
    provider: str
    product_name: str
    source_reference: str
    data_timestamp: datetime

    buy_price: float | None = Field(default=None, ge=0)
    sell_price: float | None = Field(default=None, ge=0)
    expected_return: float = Field(description="Annualized expected return as decimal.")
    volatility: float = Field(ge=0, description="Annualized volatility as decimal.")
    liquidity_score: int = Field(ge=0, le=100)

    minimum_investment: float = Field(ge=0)
    maximum_investment: float | None = Field(default=None, gt=0)
    transaction_cost: float = Field(default=0, ge=0)
    lockup_period: int = Field(default=0, ge=0, description="Lockup period in days.")
    early_exit_penalty: float = Field(default=0, ge=0)

    eligibility_conditions: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    timing_score: int | None = Field(default=None, ge=0, le=100)
    data_confidence: int = Field(ge=0, le=100)
    max_weight_hint: float | None = Field(default=None, ge=0, le=1)
    execution_instruction: str

    product_base_id: str | None = None
    allocation_rule_type: AllocationRuleType
    allocation_segments: list[AllocationSegment] = Field(default_factory=list)
    qualifying_balance_scope: QualifyingBalanceScope
    rounding_rule: RoundingRule
    repricing_required: bool = False

    source_registry_id: str
    rights_status: RightsStatus
    value_provenance: ValueProvenance
    verification_status: VerificationStatus
    uncertainty_bounds: UncertaintyBounds | None = None

    @field_validator("product_id", "provider", "product_name", "source_reference", "source_registry_id")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def validate_amount_dependent_segments(self) -> "AssetProduct":
        amount_dependent_rules = {
            AllocationRuleType.WHOLE_BALANCE_TIER,
            AllocationRuleType.MARGINAL_BAND,
            AllocationRuleType.PIECEWISE_COST,
        }
        if self.allocation_rule_type in amount_dependent_rules and not self.allocation_segments:
            raise ValueError("amount-dependent products must include allocation_segments")

        if self.maximum_investment is not None and self.maximum_investment < self.minimum_investment:
            raise ValueError("maximum_investment must be greater than or equal to minimum_investment")

        if self.value_provenance == ValueProvenance.USER_REPORTED and self.uncertainty_bounds is None:
            raise ValueError("USER_REPORTED data must include uncertainty_bounds")

        return self

    @property
    def is_production_eligible(self) -> bool:
        return self.rights_status == RightsStatus.APPROVED
