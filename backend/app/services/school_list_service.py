from sqlalchemy.orm import Session
from app.models.school import School


def get_schools_by_city(
    db: Session,
    city: str
) -> list[School]:

    schools = (
        db.query(School)
        .filter(School.city.ilike(city))
        .order_by(School.name)
        .all()
    )

    return schools