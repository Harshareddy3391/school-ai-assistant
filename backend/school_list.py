from app.core.database import SessionLocal
from app.services.school_list_service import get_schools_by_city


db = SessionLocal()

schools = get_schools_by_city(
    db=db,
    city="Chennai"
)

for school in schools:
    print(
        school.id,
        "|",
        school.name,
        "|",
        school.city,
        "|",
        school.phone
    )

db.close()
