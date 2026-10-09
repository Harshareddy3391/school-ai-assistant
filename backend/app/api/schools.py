
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.school import SchoolKnowledge


router = APIRouter(
    prefix="/schools",
    tags=["Schools"],
)


@router.get("/")
def get_schools(db: Session = Depends(get_db)):
    rows = (
        db.query(
            SchoolKnowledge.school_id,
            SchoolKnowledge.school_name,
            SchoolKnowledge.address,
            SchoolKnowledge.city,
            SchoolKnowledge.state,
            SchoolKnowledge.phone,
            SchoolKnowledge.email,
            SchoolKnowledge.website,
        )
        .distinct()
        .order_by(SchoolKnowledge.school_name)
        .all()
    )

    return [
        {
            "id": row.school_id,
            "name": row.school_name,
            "address": row.address,
            "city": row.city,
            "state": row.state,
            "phone": row.phone,
            "email": row.email,
            "website": row.website,
        }
        for row in rows
    ]
