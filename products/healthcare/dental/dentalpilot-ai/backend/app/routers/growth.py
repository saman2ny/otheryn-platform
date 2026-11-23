from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.models.healthcare import (
    AuditEvent,
    ClinicBranch,
    ClinicReview,
    LocalListingAudit,
    MarketingCampaign,
)
from app.schemas.healthcare import (
    ClinicReviewCreate,
    ClinicReviewDraftUpdate,
    ClinicReviewResponse,
    LocalListingAuditResponse,
    LocalListingAuditUpsert,
    MarketingCampaignCreate,
    MarketingCampaignResponse,
    MarketingCampaignUpdate,
)

router = APIRouter(prefix="/growth", tags=["clinic-growth"])


def accessible_branch(
    db: DbSession,
    current_user: CurrentUser,
    branch_id: str | None,
    *,
    required: bool = False,
) -> str | None:
    if branch_id is None:
        if required:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A clinic branch is required.")
        return None
    branch = (
        db.query(ClinicBranch)
        .filter(
            ClinicBranch.id == branch_id,
            ClinicBranch.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if branch is None or (
        current_user.role == "staff" and current_user.branch_id != branch_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic branch access denied.")
    return branch.id


def audit(
    db: DbSession,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    branch_id: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=branch_id if branch_id is not None else current_user.branch_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )


def clinic_scoped_query(query, model, current_user: CurrentUser):
    query = query.filter(model.clinic_id == current_user.clinic_id)
    if current_user.role == "staff":
        if current_user.branch_id:
            query = query.filter(
                (model.branch_id == current_user.branch_id) | (model.branch_id.is_(None))
            )
        else:
            query = query.filter(model.branch_id.is_(None))
    return query


@router.get("/local-listings", response_model=list[LocalListingAuditResponse])
def list_local_listings(
    current_user: CurrentUser,
    db: DbSession,
) -> list[LocalListingAudit]:
    query = db.query(LocalListingAudit).filter(
        LocalListingAudit.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff":
        if current_user.branch_id:
            query = query.filter(LocalListingAudit.branch_id == current_user.branch_id)
        else:
            query = query.filter(False)
    return query.order_by(LocalListingAudit.last_reviewed_at.desc()).all()


@router.post(
    "/local-listings",
    response_model=LocalListingAuditResponse,
    status_code=status.HTTP_200_OK,
)
def save_local_listing_audit(
    request: LocalListingAuditUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> LocalListingAudit:
    branch_id = accessible_branch(db, current_user, request.branch_id, required=True)
    listing = (
        db.query(LocalListingAudit)
        .filter(
            LocalListingAudit.clinic_id == current_user.clinic_id,
            LocalListingAudit.branch_id == branch_id,
            LocalListingAudit.platform == request.platform,
        )
        .first()
    )
    creating = listing is None
    if listing is None:
        listing = LocalListingAudit(
            clinic_id=current_user.clinic_id,
            branch_id=branch_id,
            platform=request.platform,
        )
        db.add(listing)
    for field, value in request.model_dump(exclude={"branch_id", "platform"}).items():
        setattr(listing, field, value)
    listing.last_reviewed_at = datetime.now(timezone.utc)
    db.flush()
    audit(
        db,
        current_user,
        "create" if creating else "update",
        "local-listing-audit",
        listing.id,
        branch_id=branch_id,
    )
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/campaigns", response_model=list[MarketingCampaignResponse])
def list_campaigns(
    current_user: CurrentUser,
    db: DbSession,
) -> list[MarketingCampaign]:
    query = clinic_scoped_query(db.query(MarketingCampaign), MarketingCampaign, current_user)
    return query.order_by(MarketingCampaign.created_at.desc()).all()


@router.post(
    "/campaigns",
    response_model=MarketingCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    request: MarketingCampaignCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> MarketingCampaign:
    branch_id = accessible_branch(
        db, current_user, request.branch_id or current_user.branch_id
    )
    campaign = MarketingCampaign(
        clinic_id=current_user.clinic_id,
        **(request.model_dump() | {"branch_id": branch_id}),
    )
    db.add(campaign)
    db.flush()
    audit(
        db,
        current_user,
        "create",
        "marketing-campaign",
        campaign.id,
        branch_id=campaign.branch_id,
    )
    db.commit()
    db.refresh(campaign)
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
def update_campaign(
    campaign_id: str,
    request: MarketingCampaignUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> MarketingCampaign:
    query = clinic_scoped_query(db.query(MarketingCampaign), MarketingCampaign, current_user)
    campaign = query.filter(MarketingCampaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found.")
    allowed = {
        "draft": {"planned"},
        "planned": {"active", "paused"},
        "active": {"paused", "completed"},
        "paused": {"planned", "active"},
        "completed": set(),
    }
    if request.status != campaign.status and request.status not in allowed[campaign.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change campaign status from {campaign.status} to {request.status}.",
        )
    campaign.status = request.status
    audit(
        db,
        current_user,
        "update",
        "marketing-campaign",
        campaign.id,
        branch_id=campaign.branch_id,
    )
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/reviews", response_model=list[ClinicReviewResponse])
def list_reviews(
    current_user: CurrentUser,
    db: DbSession,
) -> list[ClinicReview]:
    query = clinic_scoped_query(db.query(ClinicReview), ClinicReview, current_user)
    return query.order_by(ClinicReview.created_at.desc()).all()


@router.post(
    "/reviews",
    response_model=ClinicReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    request: ClinicReviewCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicReview:
    branch_id = accessible_branch(
        db, current_user, request.branch_id or current_user.branch_id
    )
    review_date = request.review_date
    if review_date and review_date.tzinfo is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Review date must include a timezone.",
        )
    review = ClinicReview(
        clinic_id=current_user.clinic_id,
        **(
            request.model_dump()
            | {
                "branch_id": branch_id,
                "review_date": review_date.astimezone(timezone.utc) if review_date else None,
            }
        ),
    )
    db.add(review)
    db.flush()
    audit(
        db,
        current_user,
        "create",
        "clinic-review",
        review.id,
        branch_id=review.branch_id,
    )
    db.commit()
    db.refresh(review)
    return review


@router.patch("/reviews/{review_id}", response_model=ClinicReviewResponse)
def update_review_draft(
    review_id: str,
    request: ClinicReviewDraftUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicReview:
    query = clinic_scoped_query(db.query(ClinicReview), ClinicReview, current_user)
    review = query.filter(ClinicReview.id == review_id).first()
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found.")
    response_draft = (request.response_draft or "").strip() or None
    review.response_draft = response_draft
    review.response_status = "drafted" if response_draft else "new"
    audit(
        db,
        current_user,
        "draft-response",
        "clinic-review",
        review.id,
        branch_id=review.branch_id,
    )
    db.commit()
    db.refresh(review)
    return review
