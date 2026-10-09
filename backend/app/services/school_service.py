
from sqlalchemy.orm import Session

from app.models.school import SchoolKnowledge


def resolve_school(
    db: Session,
    question: str,
) -> SchoolKnowledge | None:

    question_lower = question.lower()

    schools = (
        db.query(
            SchoolKnowledge.school_id,
            SchoolKnowledge.school_name,
        )
        .distinct()
        .all()
    )

    for school in schools:
        school_name = school.school_name.lower()

        if school_name in question_lower:
            return (
                db.query(SchoolKnowledge)
                .filter(
                    SchoolKnowledge.school_id == school.school_id
                )
                .first()
            )

    return None
