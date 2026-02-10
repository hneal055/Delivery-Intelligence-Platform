from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
from datetime import datetime

from src.backend.models.sql_models import DispatchJob, Driver, Package, DriverAvailability
from src.backend.models.domain import DispatchJobCreate
import uuid

class DispatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, job_data: DispatchJobCreate) -> DispatchJob:
        new_job = DispatchJob(
            **job_data.model_dump(exclude_unset=True),
            id=str(uuid.uuid4())
        )
        self.db.add(new_job)
        await self.db.commit()
        await self.db.refresh(new_job)
        return new_job

    async def get_job(self, job_id: str) -> Optional[DispatchJob]:
        result = await self.db.execute(select(DispatchJob).where(DispatchJob.id == job_id))
        return result.scalars().first()

    async def get_all_jobs(self, status: Optional[str] = None) -> List[DispatchJob]:
        query = select(DispatchJob)
        if status:
            query = query.where(DispatchJob.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_job_status(self, job_id: str, status: str) -> Optional[DispatchJob]:
        job = await self.get_job(job_id)
        if not job:
            return None
        
        job.status = status
        if status == "completed":
            job.completed_at = datetime.utcnow()
            
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def assign_driver(self, job_id: str, driver_id: str) -> Optional[DispatchJob]:
        job = await self.get_job(job_id)
        if not job:
            return None
            
        driver_result = await self.db.execute(select(Driver).where(Driver.id == driver_id))
        driver = driver_result.scalars().first()
        if not driver:
            raise ValueError("Driver not found")

        job.driver_id = driver_id
        job.status = "assigned"
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def set_availability(self, driver_id: str, date: datetime, is_available: bool, start: str, end: str):
        # Check existing
        result = await self.db.execute(
            select(DriverAvailability).where(
                DriverAvailability.driver_id == driver_id,
                DriverAvailability.date == date
            )
        )
        avail = result.scalars().first()
        
        if avail:
            avail.is_available = is_available
            avail.start_time = start
            avail.end_time = end
        else:
            avail = DriverAvailability(
                driver_id=driver_id,
                date=date,
                is_available=is_available,
                start_time=start,
                end_time=end
            )
            self.db.add(avail)
            
        await self.db.commit()
        return avail

