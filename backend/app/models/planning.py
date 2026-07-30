from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.asset_product import AssetClass


class LegalOperatingMode(StrEnum):
    RESEARCH_EDUCATION = "RESEARCH_EDUCATION"
    LICENSED_ADVISORY = "LICENSED_ADVISORY"
    BLOCKED = "BLOCKED"


class OutputReleaseType(StrEnum):
    COMPARE_ONLY = "COMPARE_ONLY"
    ADVISORY_SELECTED = "ADVISORY_SELECTED"
    BLOCKED = "BLOCKED"


class RiskCapacity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FinancialGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    target_amount: int = Field(ge=0)
    horizon_months: int = Field(ge=1, le=600)
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    flexibility: Literal["FIXED", "ADJUSTABLE", "FLEXIBLE"] = "ADJUSTABLE"


class ScenarioStyle(StrEnum):
    CAPITAL_PRESERVATION = "CAPITAL_PRESERVATION"
    BALANCED = "BALANCED"
    GROWTH = "GROWTH"


class LegalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    licensed_entity_verified: bool = False
    advisory_contract_verified: bool = False
    responsible_advisor_verified: bool = False

    @property
    def advisory_complete(self) -> bool:
        return (
            self.licensed_entity_verified
            and self.advisory_contract_verified
            and self.responsible_advisor_verified
        )


class UserFinancialProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(default="demo-user", min_length=1)
    display_name: str = Field(default="Nhà đầu tư demo", min_length=1)
    age: int = Field(default=30, ge=18, le=100)
    occupation: str = Field(default="Nhân viên văn phòng", min_length=1, max_length=160)
    marital_status: Literal["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"] = "SINGLE"
    dependents: int = Field(default=0, ge=0, le=20)
    employment_stability: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    monthly_income: int = Field(default=0, ge=0)
    total_assets: int = Field(ge=0)
    cash_savings: int = Field(default=0, ge=0)
    emergency_reserve: int = Field(ge=0)
    near_term_liabilities: int = Field(ge=0)
    monthly_expenses: int = Field(default=0, ge=0)
    total_debt: int = Field(default=0, ge=0)
    monthly_debt_payment: int = Field(default=0, ge=0)
    insurance_coverage: int = Field(default=0, ge=0)
    goal: str = Field(default="Tăng trưởng tài sản có kiểm soát", min_length=1)
    horizon_months: int = Field(ge=1, le=600)
    goals: list[FinancialGoal] = Field(default_factory=list, max_length=10)
    risk_tolerance: RiskCapacity = RiskCapacity.MEDIUM
    risk_capacity: RiskCapacity
    max_acceptable_drawdown: float = Field(default=0.15, ge=0.01, le=0.80)
    liquidity_need: int = Field(
        default=0,
        ge=0,
        description="Số tiền cần có khả năng rút trong liquidity_need_months.",
    )
    liquidity_need_months: int = Field(default=6, ge=1, le=120)
    max_product_count: int = Field(default=8, ge=1, le=20)
    max_financial_apps: int = Field(default=3, ge=1, le=20)
    monitoring_frequency: Literal["DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"] = "MONTHLY"
    lockup_tolerance_months: int = Field(default=12, ge=0, le=120)
    excluded_asset_classes: list[AssetClass] = Field(default_factory=list)
    customer_segments: list[str] = Field(default_factory=lambda: ["retail"])

    @model_validator(mode="after")
    def validate_capital(self) -> "UserFinancialProfile":
        committed = self.emergency_reserve + self.near_term_liabilities
        if committed > self.total_assets:
            raise ValueError("Quỹ dự phòng và nghĩa vụ gần hạn không được vượt tổng tài sản.")
        if self.liquidity_need > self.total_assets - committed:
            raise ValueError("Nhu cầu thanh khoản không được vượt vốn khả dụng.")
        return self

    @property
    def investable_capital(self) -> int:
        return self.total_assets - self.emergency_reserve - self.near_term_liabilities


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: UserFinancialProfile
    requested_mode: LegalOperatingMode = LegalOperatingMode.RESEARCH_EDUCATION
    legal_evidence: LegalEvidence = Field(default_factory=LegalEvidence)
    scenario_count: int = Field(default=3, ge=2, le=3)


class FinancialPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_assets: int
    emergency_reserve: int
    near_term_liabilities: int
    investable_capital: int
    immediate_liquidity_bucket: int
    medium_term_bucket: int
    long_term_capacity: int
    assumptions: list[str]


class EligibilityDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    asset_class: AssetClass
    eligible: bool
    reason_codes: list[str]
    reasons: list[str]


class UniverseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible_count: int
    rejected_count: int
    eligible_by_asset_class: dict[str, int]
    decisions: list[EligibilityDecision]


class SelectionStatus(StrEnum):
    SELECTED_INTERNAL = "SELECTED_INTERNAL"
    ELIGIBLE_NOT_SELECTED = "ELIGIBLE_NOT_SELECTED"
    REJECTED = "REJECTED"


class ProductSelectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str | None = None
    provider: str | None = None
    asset_class: AssetClass
    status: SelectionStatus
    reason_codes: list[str]
    reasons: list[str]
    expected_return: float | None = None
    volatility: float | None = None
    liquidity_score: int | None = None
    minimum_investment: float | None = None
    lockup_period_days: int | None = None
    data_timestamp: datetime | None = None


class ResolveIteration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=1, le=3)
    state_signature: str
    repricing_required_products: list[str]
    mismatch_products: list[str]
    cycle_detected: bool
    status: Literal["STABLE", "RESOLVE_REQUIRED", "CYCLE_DETECTED", "MAX_ITERATIONS"]


class BoundedResolveTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(default=3, ge=1, le=3)
    iterations: list[ResolveIteration]
    converged: bool
    cycle_detected: bool


class ProductAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str
    provider: str
    asset_class: AssetClass
    amount: int
    weight: float
    expected_return_rate: float
    expected_return_amount: int
    transaction_cost_amount: int
    liquidity_score: int
    reference_price: float | None = Field(default=None, ge=0)
    estimated_units: int | None = Field(default=None, ge=0)
    lot_size: int | None = Field(default=None, ge=1)
    selected_segment: str | None = None
    execution_instruction: str
    source_reference: str
    data_timestamp: datetime
    reason_codes: list[str] = Field(default_factory=list)


class AssetClassAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_class: AssetClass
    amount: int
    weight: float
    expected_return_amount: int
    transaction_cost_amount: int


class StressResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    estimated_change_amount: int
    estimated_change_pct: float
    assumptions: str


class RiskMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annualized_volatility: float
    var_95_amount: int
    cvar_95_amount: int
    sharpe_ratio: float | None
    concentration_hhi: float
    largest_asset_class_weight: float
    liquidity_score: float
    risk_ceiling: float
    within_risk_ceiling: bool
    stress_tests: list[StressResult]


class ComplexityBreakdown(BaseModel):
    """Auditable components of the operational-complexity objective."""

    model_config = ConfigDict(extra="forbid")

    distinct_provider_count: int = Field(ge=0)
    distinct_product_count: int = Field(ge=0)
    fragment_product_count: int = Field(ge=0)
    distinct_maturity_count: int = Field(ge=0)
    smallest_allocation_amount: int = Field(default=0, ge=0)
    smallest_allocation_pct: float = Field(default=0, ge=0, le=1)


class PortfolioScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    name: str
    style: ScenarioStyle
    objective_description: str
    investable_capital: int
    allocated_amount: int
    residual_cash: int
    expected_return_amount: int
    expected_return_rate: float
    total_cost_amount: int
    product_allocations: list[ProductAllocation]
    asset_class_allocations: list[AssetClassAllocation]
    risk_metrics: RiskMetrics
    operational_complexity_score: float = Field(ge=0, le=100)
    complexity_breakdown: ComplexityBreakdown
    complexity_config_version: str = Field(min_length=1, max_length=120)
    fragmentation_warning: bool
    complexity_resolve_count: int = Field(default=0, ge=0, le=3)
    complexity_return_delta_amount: int = 0
    complexity_return_delta_rate: float = 0
    complexity_excluded_product_ids: list[str] = Field(default_factory=list)
    selection_decisions: list[ProductSelectionDecision] = Field(default_factory=list)
    trade_offs: list[str]
    solver_status: str
    solve_time_ms: int


class InfeasibilityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_infeasible: bool
    conflicting_constraints: list[str] = Field(default_factory=list)
    safe_fallback: str | None = None


class FullCalculationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    calculated_at: datetime
    legal_operating_mode: LegalOperatingMode
    data_snapshot: str
    model_version: str
    financial_plan: FinancialPlan
    universe: UniverseSummary
    selection_decisions: list[ProductSelectionDecision]
    scenarios: list[PortfolioScenario]
    infeasibility: InfeasibilityReport
    bounded_resolve: BoundedResolveTrace
    pipeline_trace: list[str]
    assumptions: list[str]
    warnings: list[str]


class AllocationExplanation(BaseModel):
    """Deterministic, policy-safe explanation for an asset-class allocation."""

    model_config = ConfigDict(extra="forbid")

    asset_class: AssetClass
    product_id: str | None = None
    product_name: str | None = None
    provider: str | None = None
    amount: int = Field(default=0, ge=0)
    weight: float = Field(default=0, ge=0, le=1)
    expected_return_rate: float = 0
    expected_return_amount: int = 0
    transaction_cost_amount: int = Field(default=0, ge=0)
    liquidity_score: float = Field(default=0, ge=0, le=100)
    portfolio_role: str = Field(min_length=1, max_length=500)
    allocation_reason: str = Field(min_length=1, max_length=1_000)
    limiting_factor: str = Field(min_length=1, max_length=700)
    change_trigger: str = Field(min_length=1, max_length=700)
    expected_return_and_risk: str = Field(default="", max_length=1_500)
    cost_and_liquidity: str = Field(default="", max_length=1_200)
    execution_conditions: list[str] = Field(default_factory=list)
    adverse_scenario: str = Field(default="", max_length=1_200)
    data_evidence: list[str] = Field(default_factory=list)
    result_sensitive_assumptions: list[str] = Field(default_factory=list)


class MonitoringTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_type: Literal[
        "ADDITIONAL_CAPITAL",
        "WITHDRAWAL_REQUEST",
        "GOAL_OR_HORIZON_CHANGE",
        "RISK_PROFILE_CHANGE",
        "MATERIAL_PRODUCT_DATA_CHANGE",
        "PORTFOLIO_DRIFT",
        "USER_REQUEST",
    ]
    trigger_condition: str
    current_reference: str
    action: str


class WithdrawalOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_type: Literal[
        "USE_CASH",
        "BREAK_DEPOSIT",
        "SELL_HIGH_LIQUIDITY_ASSETS",
        "PROPORTIONAL_SALE",
    ]
    title: str
    available_amount: int = Field(ge=0)
    estimated_cost: str
    portfolio_impact: str
    conditions: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, le=10)


class DepositImplementationDetail(BaseModel):
    """Released deposit implementation detail; compare-only, not an execution order."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    bank: str
    product_name: str
    tenor_months: int | None = Field(default=None, ge=1)
    amount: int = Field(ge=0)
    weight: float = Field(ge=0, le=1)
    annual_rate: float
    annual_interest_amount: int
    term_interest_amount: int | None = None
    maturity_amount: int | None = None
    transaction_cost_amount: int = Field(ge=0)
    liquidity_score: int = Field(ge=0, le=100)
    selected_segment: str | None = None
    conditions: list[str] = Field(default_factory=list)
    why_selected: str
    source_reference: str
    data_timestamp: datetime


class ReleasedScenario(BaseModel):
    """Scenario shape after policy selection.

    asset_class_allocations and product_allocations are copied verbatim from fields
    already produced by the optimizer. The policy layer never recomputes amounts.
    """

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    name: str
    style: ScenarioStyle
    recommendation_role: Literal["RECOMMENDED", "ALTERNATIVE"] | None = None
    objective_description: str
    investable_capital: int
    expected_return_amount: int
    expected_return_rate: float
    total_cost_amount: int
    allocations: list[AssetClassAllocation | ProductAllocation]
    allocation_explanations: list[AllocationExplanation] = Field(default_factory=list)
    allocation_granularity: Literal["ASSET_CLASS", "PRODUCT"]
    risk_metrics: RiskMetrics
    operational_complexity_score: float = Field(ge=0, le=100)
    complexity_breakdown: ComplexityBreakdown
    complexity_config_version: str = Field(min_length=1, max_length=120)
    fragmentation_warning: bool
    complexity_resolve_count: int = Field(default=0, ge=0, le=3)
    complexity_return_delta_amount: int = 0
    complexity_return_delta_rate: float = 0
    selection_decisions: list[ProductSelectionDecision] = Field(default_factory=list)
    trade_offs: list[str]
    monitoring_triggers: list[MonitoringTrigger] = Field(default_factory=list)
    withdrawal_options: list[WithdrawalOption] = Field(default_factory=list)
    source_summary: list[str] = Field(default_factory=list)
    assumptions_that_change_result: list[str] = Field(default_factory=list)
    deposit_implementation: list[DepositImplementationDetail] = Field(default_factory=list)


class ReleasedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    released_at: datetime
    legal_operating_mode: LegalOperatingMode
    output_release_type: OutputReleaseType
    data_snapshot: str
    model_version: str
    financial_plan: FinancialPlan | None = None
    scenarios: list[ReleasedScenario] = Field(default_factory=list)
    universe: UniverseSummary | None = None
    selection_decisions: list[ProductSelectionDecision] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_message: str | None = None
    human_confirmation_required: bool = True


class ExplanationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reasoning: list[str]
    source_reference: list[str] = Field(default_factory=list)
    warning: list[str] = Field(default_factory=list)
    confidence: int = Field(default=75, ge=0, le=100)
    generated_by: Literal[
        "OPENAI_STRUCTURED_OUTPUT",
        "GROQ_STRUCTURED_OUTPUT",
        "OLLAMA_STRUCTURED_OUTPUT",
        "DETERMINISTIC_FALLBACK",
    ] = "DETERMINISTIC_FALLBACK"


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    released_output: ReleasedOutput
    explanation: ExplanationPayload


class ChatHistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1_200)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str | None = None
    message: str = Field(min_length=1, max_length=1_000)
    active_scenario_id: str | None = None
    conversation_history: list[ChatHistoryTurn] = Field(
        default_factory=list,
        max_length=8,
    )


class ChatAnswerSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=1_500)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    intent: str
    message: str
    replanning_required: bool
    proposed_profile_changes: dict[str, Any] = Field(default_factory=dict)
    replanned_recommendation: RecommendationResponse | None = None
    focused_scenario_id: str | None = None
    sections: list[ChatAnswerSection] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    generated_by: Literal[
        "OPENAI_STRUCTURED_OUTPUT",
        "GROQ_STRUCTURED_OUTPUT",
        "OLLAMA_STRUCTURED_OUTPUT",
        "DETERMINISTIC_FALLBACK",
        "DATA_REGISTRY",
    ] = "DETERMINISTIC_FALLBACK"


class ConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    confirmed: bool
    note: str | None = Field(default=None, max_length=500)
