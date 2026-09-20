from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolResponse


router = APIRouter(
    prefix="/schools",
    tags=["Schools"]
)


@router.post(
    "/",
    response_model=SchoolResponse,
    status_code=status.HTTP_201_CREATED
)
def create_school(
    school_data: SchoolCreate,
    db: Session = Depends(get_db)
):
    try:
        school = School(
            **school_data.model_dump()
        )

        db.add(school)
        db.commit()
        db.refresh(school)

        return school

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create school"
        )