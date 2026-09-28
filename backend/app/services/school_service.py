from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.school import School


def resolve_school(
    db: Session,
    question: str
) -> School | None:

    schools = db.query(School).all()

    question_lower = question.lower()

    for school in schools:
        school_name = school.name.lower()

        if school_name in question_lower:
            return school

    return None