from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress
import logging
import sqlite3
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.app.api.auth import router as auth_router
from backend.app.core.auth import UserContext, get_current_user, require_admin
from backend.app.core.config import get_settings
from backend.app.core.middleware import security_and_observability_middleware
from backend.app.data.mock_asset_products import load_mock_asset_products
from backend.app.db.repository import (
    create_auth_user,
    fetch_advisory_authorization,
    fetch_auth_user_by_id,
    fetch_recommendation,
    fetch_user_profile,
    list_chat_messages,
    list_audit_logs,
    list_user_recommendations,
    save_chat_message,
    save_confirmation,
    upsert_advisory_authorization,
    upsert_user_profile,
)
from backend.app.db import (
    fetch_asset_product,
    fetch_asset_products,
    get_connection,
    initialize_database,
    upsert_asset_products,
)
from backend.app.models import (
    AdvisoryAuthorizationStatus,
    AdvisoryAuthorizationUpdate,
    AssetClass,
    AssetProduct,
    ChatRequest,
    ChatResponse,
    ConfirmationRequest,
    FullCalculationOutput,
    LegalEvidence,
    LegalOperatingMode,
    PlanningRequest,
    RecommendationResponse,
    ReleasedOutput,
    UserFinancialProfile,
)
from backend.app.services.chat import interpret_follow_up, resolve_scenario_id
from backend.app.services.compliance import apply_output_policy
from backend.app.services.deposit_comparison import (
    SUPPORTED_SEGMENTS,
    SUPPORTED_TENORS,
    compare_deposits,
)
from backend.app.services.market_data import market_data_summary, refresh_market_data
from backend.app.services.orchestrator import (
    run_complexity_resolve,
    run_planning_pipeline,
)
from backend.app.services.reports import generate_recommendation_pdf


settings = get_settings()
logger = logging.getLogger("monopoly.main")


async def _market_data_refresh_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(refresh_market_data)
        except Exception:
            logger.exception("Background market-data refresh failed")
        await asyncio.sleep(settings.market_data_refresh_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    if not settings.auth_required and fetch_auth_user_by_id("demo-user") is None:
        create_auth_user(
            user_id="demo-user",
            email="demo@local.invalid",
            display_name="Nhà đầu tư demo",
            password_hash="disabled-local-demo-account",
            password_salt="disabled-local-demo-salt",
            role="admin",
        )
    if not fetch_asset_products(approved_only=False):
        upsert_asset_products(load_mock_asset_products(settings.data_dir))
    market_task = (
        asyncio.create_task(_market_data_refresh_loop())
        if settings.market_data_auto_refresh
        else None
    )
    try:
        yield
    finally:
        if market_task is not None:
            market_task.cancel()
            with suppress(asyncio.CancelledError):
                await market_task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production-oriented system for coupled multi-asset planning, compliance-aware "
        "release policy and released-schema-only explanation."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(security_and_observability_middleware)
app.include_router(auth_router)


def _authorize_recommendation(stored: dict[str, Any], user: UserContext) -> None:
    if user.role != "admin" and stored["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem kết quả này.")


@app.get("/health")
def health() -> dict[str, Any]:
    data = market_data_summary()
    return {
        "status": "ok",
        "app_version": settings.app_version,
        "environment": settings.environment,
        "auth_required": settings.auth_required,
        "allow_registration": settings.allow_registration,
        "default_legal_operating_mode": settings.default_legal_operating_mode,
        "model_version": settings.model_version,
        "llm_status": "connected" if settings.llm_configured else "fallback",
        "llm_provider": settings.active_llm_provider,
        "llm_model": settings.active_llm_model,
        "openai_status": "connected" if settings.openai_api_key else "fallback",
        "openai_model": settings.openai_model,
        "data_status": data["mode"],
        "data_snapshot": data["snapshot_id"],
        "data_sources_connected": data["connected_sources"],
        "data_sources_total": data["total_sources"],
        "data_last_updated": data["last_refresh_at"],
    }


@app.get("/ready")
def readiness() -> dict[str, str | list[str]]:
    failures: list[str] = []
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        failures.append("database")
    if (
        settings.environment == "production"
        and settings.auth_required
        and (
            settings.auth_secret == "development-only-change-me-before-production"
            or len(settings.auth_secret) < 32
        )
    ):
        failures.append("auth_secret")
    if failures:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks_failed": failures},
        )
    return {
        "status": "ready",
        "checks": ["database", "configuration"],
    }


@app.get("/api/v1/data-sources")
def data_sources(
    _: UserContext = Depends(get_current_user),
) -> dict[str, Any]:
    return market_data_summary()


@app.post("/api/v1/admin/data-sources/refresh")
def refresh_data_sources(
    _: UserContext = Depends(require_admin),
) -> dict[str, Any]:
    return refresh_market_data()


def _advisory_status(
    user: UserContext,
) -> AdvisoryAuthorizationStatus:
    authorization = fetch_advisory_authorization(user.user_id)
    authorized = all(
        authorization[field]
        for field in (
            "licensed_entity_verified",
            "advisory_contract_verified",
            "responsible_advisor_verified",
        )
    )
    return AdvisoryAuthorizationStatus(
        **authorization,
        authorized=authorized,
        can_manage=user.role == "admin",
    )


@app.get(
    "/api/v1/advisory/status",
    response_model=AdvisoryAuthorizationStatus,
)
def advisory_status(
    user: UserContext = Depends(get_current_user),
) -> AdvisoryAuthorizationStatus:
    return _advisory_status(user)


@app.put(
    "/api/v1/admin/advisory/status",
    response_model=AdvisoryAuthorizationStatus,
)
def update_advisory_status(
    update: AdvisoryAuthorizationUpdate,
    user: UserContext = Depends(require_admin),
) -> AdvisoryAuthorizationStatus:
    upsert_advisory_authorization(
        user_id=user.user_id,
        verified_by=user.user_id,
        **update.model_dump(),
    )
    return _advisory_status(user)


@app.get("/api/v1/products", response_model=list[AssetProduct])
def list_products(
    asset_class: AssetClass | None = Query(default=None),
    approved_only: bool = Query(default=True),
) -> list[dict]:
    return fetch_asset_products(asset_class=asset_class, approved_only=approved_only)


@app.get("/api/v1/products/{product_id}", response_model=AssetProduct)
def get_product(product_id: str) -> dict:
    product = fetch_asset_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/v1/deposits/compare")
def compare_deposit_rates(
    amount: int = Query(ge=1_000_000),
    tenor_months: int = Query(default=12),
    customer_segment: str = Query(default="retail"),
    _: UserContext = Depends(get_current_user),
) -> dict[str, Any]:
    if tenor_months not in SUPPORTED_TENORS:
        raise HTTPException(
            status_code=422,
            detail=f"Kỳ hạn hợp lệ: {', '.join(map(str, SUPPORTED_TENORS))} tháng.",
        )
    normalized_segment = customer_segment.strip().lower()
    if normalized_segment not in SUPPORTED_SEGMENTS:
        raise HTTPException(
            status_code=422,
            detail="Phân khúc hợp lệ: retail, priority hoặc private.",
        )
    return compare_deposits(
        amount=amount,
        tenor_months=tenor_months,
        customer_segment=normalized_segment,
    )


@app.post("/api/v1/admin/seed-mock-products")
def seed_mock_products(
    _: UserContext = Depends(require_admin),
) -> dict[str, int | str]:
    products = load_mock_asset_products(settings.data_dir)
    count = upsert_asset_products(products)
    return {
        "status": "seeded",
        "product_count": count,
        "data_snapshot": "MOCK_ASSET_PRODUCT_2026Q3",
    }


def _default_profile(user: UserContext) -> UserFinancialProfile:
    return UserFinancialProfile(
            user_id=user.user_id,
            display_name=user.display_name,
            age=32,
            occupation="Chuyên viên công nghệ",
            marital_status="MARRIED",
            dependents=1,
            employment_stability="HIGH",
            monthly_income=55_000_000,
            total_assets=650_000_000,
            cash_savings=180_000_000,
            emergency_reserve=90_000_000,
            near_term_liabilities=40_000_000,
            monthly_expenses=25_000_000,
            total_debt=120_000_000,
            monthly_debt_payment=8_000_000,
            insurance_coverage=500_000_000,
            goal="Tích lũy mua nhà và tăng trưởng tài sản trong 7 năm",
            horizon_months=84,
            goals=[
                {
                    "goal_id": "home",
                    "name": "Tích lũy mua nhà",
                    "target_amount": 1_500_000_000,
                    "horizon_months": 84,
                    "priority": "HIGH",
                    "flexibility": "ADJUSTABLE",
                }
            ],
            risk_tolerance="MEDIUM",
            risk_capacity="MEDIUM",
            max_acceptable_drawdown=0.15,
            liquidity_need=60_000_000,
            liquidity_need_months=6,
            max_product_count=6,
            max_financial_apps=3,
            monitoring_frequency="MONTHLY",
            lockup_tolerance_months=12,
        )


@app.get("/api/v1/demo/default-request", response_model=PlanningRequest)
def default_planning_request(
    user: UserContext = Depends(get_current_user),
) -> PlanningRequest:
    if not isinstance(user, UserContext):
        user = get_current_user()
    return PlanningRequest(
        profile=fetch_user_profile(user.user_id) or _default_profile(user)
    )


@app.get("/api/v1/me/profile", response_model=UserFinancialProfile)
def get_my_profile(
    user: UserContext = Depends(get_current_user),
) -> UserFinancialProfile:
    return fetch_user_profile(user.user_id) or _default_profile(user)


@app.put("/api/v1/me/profile", response_model=UserFinancialProfile)
def update_my_profile(
    profile: UserFinancialProfile,
    user: UserContext = Depends(get_current_user),
) -> UserFinancialProfile:
    owned_profile = profile.model_copy(
        update={"user_id": user.user_id, "display_name": user.display_name}
    )
    upsert_user_profile(PlanningRequest(profile=owned_profile))
    return owned_profile


@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
def create_recommendation(
    request: PlanningRequest,
    user: UserContext = Depends(get_current_user),
) -> RecommendationResponse:
    if request.profile.user_id != user.user_id:
        request = request.model_copy(
            update={
                "profile": request.profile.model_copy(
                    update={
                        "user_id": user.user_id,
                        "display_name": user.display_name,
                    }
                )
            }
        )
    if request.requested_mode == LegalOperatingMode.LICENSED_ADVISORY:
        authorization = fetch_advisory_authorization(user.user_id)
        request = request.model_copy(
            update={
                "legal_evidence": LegalEvidence(
                    licensed_entity_verified=authorization[
                        "licensed_entity_verified"
                    ],
                    advisory_contract_verified=authorization[
                        "advisory_contract_verified"
                    ],
                    responsible_advisor_verified=authorization[
                        "responsible_advisor_verified"
                    ],
                )
            }
        )
    response, _ = run_planning_pipeline(request)
    return response


@app.get("/api/v1/recommendations/{recommendation_id}")
def get_recommendation(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user),
) -> dict[str, Any]:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    return {
        "released_output": stored["released_output"],
        "explanation": stored["explanation"],
        "status": stored["status"],
        "created_at": stored["created_at"],
    }


@app.get("/api/v1/internal/recommendations/{recommendation_id}")
def get_full_recommendation(
    recommendation_id: str,
    _: UserContext = Depends(require_admin),
) -> dict[str, Any]:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return stored


@app.post(
    "/api/v1/recommendations/{recommendation_id}/scenarios/{scenario_id}/consolidate",
    response_model=RecommendationResponse,
)
def consolidate_scenario(
    recommendation_id: str,
    scenario_id: str,
    user: UserContext = Depends(get_current_user),
) -> RecommendationResponse:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    try:
        response, _ = run_complexity_resolve(stored, scenario_id)
    except ValueError as exc:
        code = str(exc)
        if code == "SCENARIO_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Scenario not found") from exc
        if code == "COMPLEXITY_RESOLVE_LIMIT_REACHED":
            raise HTTPException(
                status_code=409,
                detail="Đã đạt giới hạn gộp tối đa 3 lần cho kịch bản này.",
            ) from exc
        if code == "COMPLEXITY_RESOLVE_INFEASIBLE":
            raise HTTPException(
                status_code=409,
                detail="Không tìm được nghiệm gộp vẫn thỏa risk/liquidity gate.",
            ) from exc
        raise HTTPException(
            status_code=409,
            detail="Kết quả cũ chưa có dữ liệu độ phức tạp; hãy chạy lại phân tích.",
        ) from exc
    return response
@app.get("/api/v1/recommendations/{recommendation_id}/audit")
def get_recommendation_audit(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user),
) -> list[dict[str, Any]]:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    return list_audit_logs(recommendation_id)


@app.get("/api/v1/recommendations/{recommendation_id}/report.pdf")
def export_recommendation_report(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user),
) -> Response:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    released = ReleasedOutput.model_validate(stored["released_output"])
    pdf_bytes = generate_recommendation_pdf(released)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="portfolio-report-{recommendation_id}.pdf"'
            )
        },
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: UserContext = Depends(get_current_user),
) -> ChatResponse:
    stored = (
        fetch_recommendation(request.recommendation_id)
        if request.recommendation_id
        else None
    )
    if request.recommendation_id and stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if stored is not None:
        _authorize_recommendation(stored, user)
        original = PlanningRequest.model_validate(stored["request"])
        released = ReleasedOutput.model_validate(stored["released_output"])
        if (
            not any(
                scenario.deposit_implementation
                for scenario in released.scenarios
            )
            and stored.get("full_output")
        ):
            released = apply_output_policy(
                FullCalculationOutput.model_validate(stored["full_output"])
            )
    else:
        original = PlanningRequest(
            profile=fetch_user_profile(user.user_id) or _default_profile(user)
        )
        released = None
    conversation_history = [
        turn.model_dump()
        for turn in request.conversation_history
    ]
    if not conversation_history and request.recommendation_id:
        conversation_history = [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in list_chat_messages(request.recommendation_id)[-8:]
        ]
    focused_scenario_id = (
        resolve_scenario_id(
            released,
            request.message,
            request.active_scenario_id,
        )
        if released is not None
        else None
    )
    reply, revised = interpret_follow_up(
        original,
        request.message,
        released,
        focused_scenario_id,
        conversation_history,
    )
    reply.focused_scenario_id = focused_scenario_id
    reply.recommendation_id = request.recommendation_id or ""
    message_recommendation_id = request.recommendation_id
    if revised is not None:
        replanned, _ = run_planning_pipeline(revised)
        reply.replanned_recommendation = replanned
        reply.recommendation_id = replanned.released_output.recommendation_id
        message_recommendation_id = replanned.released_output.recommendation_id
        reply.message += (
            f" Mã phương án mới: {replanned.released_output.recommendation_id}."
        )
    if message_recommendation_id:
        save_chat_message(message_recommendation_id, "user", request.message)
        save_chat_message(
            message_recommendation_id,
            "assistant",
            reply.message,
            reply.model_dump(exclude={"replanned_recommendation"}),
        )
    return reply


@app.post("/api/v1/recommendations/{recommendation_id}/confirm")
def confirm_scenario(
    recommendation_id: str,
    confirmation: ConfirmationRequest,
    user: UserContext = Depends(get_current_user),
) -> dict[str, str | bool]:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    scenario_ids = {
        scenario["scenario_id"]
        for scenario in stored["released_output"].get("scenarios", [])
    }
    if confirmation.scenario_id not in scenario_ids:
        raise HTTPException(status_code=400, detail="Scenario does not belong to recommendation")
    confirmation_id = save_confirmation(recommendation_id, confirmation)
    return {
        "confirmation_id": confirmation_id,
        "confirmed": confirmation.confirmed,
        "status": (
            "HUMAN_CONFIRMED_FOR_DEMO_ONLY"
            if confirmation.confirmed
            else "DECLINED"
        ),
    }


@app.get("/api/v1/me/recommendations")
def recommendation_history(
    limit: int = Query(default=30, ge=1, le=100),
    user: UserContext = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return list_user_recommendations(user.user_id, limit=limit)


@app.get("/api/v1/recommendations/{recommendation_id}/messages")
def conversation_history(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user),
) -> list[dict[str, Any]]:
    stored = fetch_recommendation(recommendation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    _authorize_recommendation(stored, user)
    return list_chat_messages(recommendation_id)


if settings.frontend_dist.exists():
    assets_dir = settings.frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(settings.frontend_dist / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa(full_path: str) -> FileResponse:
        candidate = settings.frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(settings.frontend_dist / "index.html")
