from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.health_check import HealthCheck
from app.schemas.check import StatsResponse

router = APIRouter(prefix="/api")


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    total, successful, average = db.execute(
        select(
            func.count(HealthCheck.id),
            func.coalesce(func.sum(case((HealthCheck.status == "up", 1), else_=0)), 0),
            func.avg(HealthCheck.response_time_ms),  # NULLs (no response) are ignored
        )
    ).one()
    return StatsResponse(
        total_checks=total,
        successful_checks=successful,
        failed_checks=total - successful,
        average_response_time_ms=round(average, 2) if average is not None else None,
    )
