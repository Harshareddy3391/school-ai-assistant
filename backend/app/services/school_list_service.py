
from sqlalchemy.orm import Session

from app.models.school import SchoolKnowledge


def get_schools_by_city(
    db: Session,
    city: str,
) -> list[dict]:

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
        .filter(SchoolKnowledge.city.ilike(city))
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
