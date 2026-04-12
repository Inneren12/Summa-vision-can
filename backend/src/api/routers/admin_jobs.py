from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from src.core.database import get_db
from src.models.job import Job, JobStatus
from src.repositories.job_repository import JobRepository
from src.schemas.events import EventType

router = APIRouter(prefix="/api/v1/admin/jobs", tags=["admin_jobs"])

class JobResponse(BaseModel):
    id: str
    job_type: str
    status: JobStatus
    payload_json: str
    result_json: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int
    max_attempts: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by: Optional[str] = None
    dedupe_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int

@router.get("", response_model=JobListResponse)
async def list_jobs(
    job_type: Optional[str] = None,
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = JobRepository(db)
    items = await repo.list_jobs(job_type=job_type, status=status_filter, limit=limit)

    stmt = select(func.count()).select_from(Job)
    if job_type is not None:
        stmt = stmt.where(Job.job_type == job_type)
    if status_filter is not None:
        stmt = stmt.where(Job.status == status_filter)

    total = await db.scalar(stmt) or 0

    res_items = []
    for item in items:
        item_dict = {
            "id": str(item.id),
            "job_type": item.job_type,
            "status": item.status,
            "payload_json": item.payload_json,
            "result_json": item.result_json,
            "error_code": item.error_code,
            "error_message": item.error_message,
            "attempt_count": item.attempt_count,
            "max_attempts": item.max_attempts,
            "created_at": item.created_at,
            "started_at": item.started_at,
            "finished_at": item.finished_at,
            "created_by": item.created_by,
            "dedupe_key": item.dedupe_key,
        }
        res_items.append(JobResponse.model_validate(item_dict))

    return JobListResponse(items=res_items, total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    repo = JobRepository(db)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    item_dict = {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "payload_json": job.payload_json,
        "result_json": job.result_json,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "created_by": job.created_by,
        "dedupe_key": job.dedupe_key,
    }
    return JobResponse.model_validate(item_dict)


class RetryJobResponse(BaseModel):
    job_id: str

@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED, response_model=RetryJobResponse)
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    repo = JobRepository(db)
    job = await repo.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")

    if job.attempt_count >= job.max_attempts:
        raise HTTPException(status_code=409, detail="Job has exhausted retry attempts")

    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JobStatus.QUEUED,
            error_code=None,
            error_message=None,
            started_at=None,
            finished_at=None,
            attempt_count=job.attempt_count + 1,
        )
    )

    from src.services.audit import AuditWriter
    audit = AuditWriter(db)
    await audit.log_event(
        event_type=EventType.JOB_CREATED,
        entity_type="job",
        entity_id=str(job_id),
        metadata={
            "action": "retry",
            "attempt_count": job.attempt_count + 1,
            "max_attempts": job.max_attempts
        },
        actor="admin_api"
    )

    await db.flush()

    return RetryJobResponse(job_id=str(job.id))
