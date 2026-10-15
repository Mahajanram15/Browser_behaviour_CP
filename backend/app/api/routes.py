from typing import Optional, Any, Dict, List
from fastapi import APIRouter, Request, status, HTTPException, Depends, Query

from backend.app.core.database import get_db
from backend.app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionEndRequest,
    SessionEndResponse,
)
from backend.app.schemas.behavior import (
    BehaviorBatchRequest,
    BehaviorBatchResponse,
)
from backend.app.schemas.api_log import (
    ApiRequestCreate,
    ApiRequestResponse,
)
from backend.app.schemas.risk import (
    RiskResponse,
    ExplanationResponse,
)
from backend.app.schemas.dashboard import (
    DashboardStatsResponse,
)
from backend.app.schemas.mock_domain import (
    MOCK_PRODUCTS,
    ProductItem,
    ProductListResponse,
    ProductDetailResponse,
    SearchResponse,
    SearchFilterResponse,
    CatalogResponse,
    CartItemRequest,
    CartItemResponse,
    CheckoutVerifyRequest,
    CheckoutVerifyResponse,
)
from backend.app.services.session_service import session_service
from backend.app.services.risk_service import risk_service

router = APIRouter(prefix="/api", tags=["Behavioral Integrity API"])

# ------------------------------------------------------------------------------
# 1. Session Lifecycle Endpoints
# ------------------------------------------------------------------------------
@router.post("/session/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    req: SessionStartRequest,
    request: Request,
    db: Optional[Any] = Depends(get_db)
):
    """
    Initializes a new tracking session and returns a bound session ID and telemetry configuration.
    Accepts collection metadata (collection_mode, task_id, label) for research dataset collection.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await session_service.create_session(req, client_ip, db=db)

@router.post("/session/end", response_model=SessionEndResponse, status_code=status.HTTP_200_OK)
async def end_session(
    req: SessionEndRequest,
    db: Optional[Any] = Depends(get_db)
):
    """
    Terminates an active session, computes summary statistics, triggers feature extraction, and finalizes scoring.
    """
    return await session_service.end_session(
        session_id=req.session_id,
        end_reason=req.end_reason or "USER_EXIT",
        collection_mode=req.collection_mode,
        automation_condition=req.automation_condition,
        participant_id=req.participant_id,
        task_id=req.task_id,
        label=req.label,
        db=db
    )

# ------------------------------------------------------------------------------
# 2. Telemetry Ingestion Endpoints
# ------------------------------------------------------------------------------
@router.post("/behavior/events", response_model=BehaviorBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_behavior_events(
    req: BehaviorBatchRequest,
    db: Optional[Any] = Depends(get_db)
):
    """
    Ingests batched client behavioral dynamics (mouse, keystroke timing metadata, scrolling).
    PRIVACY COMPLIANCE: Zero raw keystroke characters or input values accepted.
    """
    return await session_service.record_events(req, db=db)

@router.post("/api-requests", response_model=ApiRequestResponse, status_code=status.HTTP_201_CREATED)
async def log_api_request(
    req: ApiRequestCreate,
    db: Optional[Any] = Depends(get_db)
):
    """
    Ingests backend API access log to enable cross-layer behavioral correlation.
    Validates bound session, enforces privacy parameters, and tracks per-session sequence numbers.
    """
    return await session_service.record_api_request(req, db=db)

# ------------------------------------------------------------------------------
# 3. Risk & Explainability Endpoints
# ------------------------------------------------------------------------------
@router.get("/risk/{session_id}", response_model=RiskResponse, status_code=status.HTTP_200_OK)
async def get_session_risk(session_id: str):
    """
    Retrieves the multi-signal behavioral risk score breakdown and policy decision for a session.
    """
    return await risk_service.get_risk_score(session_id)

@router.get("/explanation/{session_id}", response_model=ExplanationResponse, status_code=status.HTTP_200_OK)
async def get_session_explanation(session_id: str):
    """
    Retrieves SHAP feature contributions and triggered security rules explaining the risk score.
    """
    return await risk_service.get_explanation(session_id)

# ------------------------------------------------------------------------------
# 4. Security Dashboard Endpoints
# ------------------------------------------------------------------------------
@router.get("/dashboard/stats", response_model=DashboardStatsResponse, status_code=status.HTTP_200_OK)
async def get_dashboard_stats():
    """
    Returns aggregated fleet statistics, risk distribution, and flagged sessions for the analyst UI.
    """
    return await risk_service.get_dashboard_stats()

# ------------------------------------------------------------------------------
# 5. Research Dataset Collection Endpoints
# ------------------------------------------------------------------------------
@router.get("/dataset/summary", status_code=status.HTTP_200_OK)
async def get_dataset_summary():
    """
    Returns summary statistics on collected sessions (human vs automated counts, task distribution).
    """
    return session_service.get_dataset_summary()

@router.post("/dataset/export", status_code=status.HTTP_200_OK)
async def export_dataset():
    """
    Triggers export of recorded sessions into ml/data/features.csv and ml/data/metadata.csv.
    """
    return session_service.export_dataset()

# ------------------------------------------------------------------------------
# 6. Mock Application Domain Endpoints (Controlled Research Experiments)
# NOTE: These are lightweight, deterministic demonstration endpoints for
# Experiment B (TASK_01, TASK_02, TASK_03). They simulate application HTTP traffic
# without persisting data or modifying research datasets.
# ------------------------------------------------------------------------------

@router.get("/products", response_model=ProductListResponse, status_code=status.HTTP_200_OK)
async def list_products(
    category: Optional[str] = Query(None, description="Optional category filter (e.g. 'laptops')"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Returns a deterministic paginated list of mock products.
    Optionally accepts category and page query parameters.
    """
    items = list(MOCK_PRODUCTS.values())
    if category:
        cat_lower = category.strip().lower()
        items = [p for p in items if p["category"].lower() == cat_lower]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]

    return ProductListResponse(
        products=[ProductItem(**p) for p in paginated_items],
        total=total,
        page=page,
        page_size=page_size,
        category=category
    )

@router.get("/products/details", response_model=ProductDetailResponse, status_code=status.HTTP_200_OK)
async def get_product_details(
    id: str = Query(..., min_length=1, max_length=64, description="Unique product ID")
):
    """
    Returns mock product details for a validated product ID.
    Returns 404 if the product is not found.
    """
    prod = MOCK_PRODUCTS.get(id)
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{id}' not found"
        )
    return ProductDetailResponse(**prod)

@router.get("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_products(
    q: str = Query(..., min_length=1, max_length=128, description="Search query string"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return")
):
    """
    Returns deterministic mock search results for query parameter 'q'.
    """
    q_lower = q.strip().lower()
    matches = [
        p for p in MOCK_PRODUCTS.values()
        if q_lower in p["name"].lower()
        or q_lower in p["category"].lower()
        or q_lower in p["description"].lower()
    ]
    sliced = matches[:limit]
    return SearchResponse(
        query=q,
        results=[ProductItem(**p) for p in sliced],
        total_results=len(matches),
        limit=limit
    )

@router.get("/search/filter", response_model=SearchFilterResponse, status_code=status.HTTP_200_OK)
async def filter_search_products(
    filter: str = Query(..., min_length=1, max_length=64, description="Filter category or keyword"),
    sort: str = Query("relevance", description="Sort order: relevance, price_asc, price_desc, rating, name_asc")
):
    """
    Accepts validated filter and sort parameters and returns deterministic results.
    """
    allowed_sorts = {"relevance", "price_asc", "price_desc", "rating", "name_asc"}
    sort_clean = sort.strip().lower()
    if sort_clean not in allowed_sorts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort parameter '{sort}'. Allowed options: {sorted(list(allowed_sorts))}"
        )

    f_lower = filter.strip().lower()
    matches = [
        p for p in MOCK_PRODUCTS.values()
        if f_lower in p["category"].lower()
        or f_lower in p["name"].lower()
        or f_lower in p["description"].lower()
    ]

    # Deterministic sorting
    if sort_clean == "price_asc":
        matches = sorted(matches, key=lambda x: x["price"])
    elif sort_clean == "price_desc":
        matches = sorted(matches, key=lambda x: x["price"], reverse=True)
    elif sort_clean == "rating":
        matches = sorted(matches, key=lambda x: x["rating"], reverse=True)
    elif sort_clean == "name_asc":
        matches = sorted(matches, key=lambda x: x["name"])
    # "relevance" preserves canonical catalog ordering

    return SearchFilterResponse(
        filter=filter,
        sort=sort_clean,
        results=[ProductItem(**p) for p in matches],
        total_results=len(matches)
    )

@router.get("/catalog", response_model=CatalogResponse, status_code=status.HTTP_200_OK)
async def get_catalog(
    category: Optional[str] = Query(None, description="Optional category focus")
):
    """
    Returns a fixed catalog overview with available categories and featured products.
    """
    categories = sorted(list({p["category"] for p in MOCK_PRODUCTS.values()}))
    items = list(MOCK_PRODUCTS.values())
    if category:
        cat_lower = category.strip().lower()
        items = [p for p in items if p["category"].lower() == cat_lower]

    featured = items[:4]
    return CatalogResponse(
        category=category,
        categories=categories,
        featured_products=[ProductItem(**p) for p in featured],
        total_catalog_items=len(MOCK_PRODUCTS)
    )

@router.post("/cart/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_cart_item(req: CartItemRequest):
    """
    Accepts validated JSON payload (item_id, positive quantity) and returns a mock success response.
    Does not mutate persistent database state.
    """
    if req.item_id not in MOCK_PRODUCTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{req.item_id}' not found in catalog"
        )
    return CartItemResponse(
        status="ADDED",
        item_id=req.item_id,
        quantity=req.quantity,
        message=f"Added {req.quantity} of '{MOCK_PRODUCTS[req.item_id]['name']}' to mock cart"
    )

@router.post("/checkout/verify", response_model=CheckoutVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_checkout(req: CheckoutVerifyRequest):
    """
    Accepts validated JSON payload (shipping_method, currency) and returns mock verification response.
    """
    allowed_methods = {"standard", "express", "overnight", "pickup"}
    method_clean = req.shipping_method.strip().lower()
    if method_clean not in allowed_methods:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid shipping_method '{req.shipping_method}'. Allowed: {sorted(list(allowed_methods))}"
        )

    allowed_currencies = {"USD", "EUR", "GBP", "CAD", "JPY"}
    curr_clean = req.currency.strip().upper()
    if curr_clean not in allowed_currencies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid currency code '{req.currency}'. Supported demo currencies: {sorted(list(allowed_currencies))}"
        )

    return CheckoutVerifyResponse(
        status="VERIFIED",
        shipping_method=method_clean,
        currency=curr_clean,
        is_valid=True,
        message="Mock checkout parameters verified for research demonstration"
    )

