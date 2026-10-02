from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.health_check import HealthCheck
from app.schemas.check import CheckListResponse, CheckRequest, CheckResponse
from app.services.checker import perform_check
from app.services.ssrf import UnsafeURLError

router = APIRouter(prefix="/api")


@router.post("/check", response_model=CheckResponse, status_code=201)
def create_check(payload: CheckRequest, db: Session = Depends(get_db)) -> HealthCheck:
    # Never store or echo credentials embedded in a URL (https://user:pass@host/).
    if payload.url.username or payload.url.password:
        raise HTTPException(
            status_code=400, detail="URLs containing a username or password are not allowed"
        )

    url = str(payload.url)
    try:
        outcome = perform_check(url)
    except UnsafeURLError:
        raise HTTPException(status_code=400, detail="URL destination is not allowed")

    record = HealthCheck(
        url=url,
        **asdict(outcome),
        # SQLite has no timezone support: store naive UTC, the schema labels it "Z".
        checked_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(record)
    db.commit()
    return record


@router.get("/checks", response_model=CheckListResponse)
def list_checks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CheckListResponse:
    total = db.scalar(select(func.count()).select_from(HealthCheck)) or 0
    items = db.scalars(
        select(HealthCheck)
        .order_by(HealthCheck.checked_at.desc(), HealthCheck.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return CheckListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/checks/{check_id}", response_model=CheckResponse)
def get_check(check_id: int, db: Session = Depends(get_db)) -> HealthCheck:
    record = db.get(HealthCheck, check_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Check not found")
    return record
