import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.school import School
from app.schemas.document import DocumentResponse


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload/{school_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
def upload_document(
    school_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Check whether school exists
        school = db.get(
            School,
            school_id
        )

        if school is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found"
            )

        # Check PDF file
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )

        # Generate unique filename
        unique_filename = (
            f"{uuid.uuid4()}_{file.filename}"
        )

        file_path = os.path.join(
            UPLOAD_DIR,
            unique_filename
        )

        # Save PDF file
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        # Create document record
        document = Document(
            school_id=school_id,
            filename=file.filename,
            file_path=file_path,
            document_type="PDF"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        # Remove uploaded file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document"
        )

    except Exception:
        db.rollback()

        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while uploading document"
        )


    