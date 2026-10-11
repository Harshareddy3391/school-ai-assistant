
import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.school import SchoolKnowledge
from app.schemas.document import DocumentUploadResponse
from app.services.pdf_service import extract_text_from_pdf
from app.rag.chunking import split_text_into_chunks
from app.services.embedding_service import generate_embeddings


router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload/{school_id}",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    school_id: int,
    file: UploadFile = File(...),
    school_name: str | None = Form(None),
    city: str | None = Form(None),
    state: str | None = Form(None),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    website: str | None = Form(None),
    db: Session = Depends(get_db),
):
    file_path = None

    try:
        # 1. Validate the school ID and uploaded file.
        if school_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="school_id must be a positive integer.",
            )

        if (
            file.content_type != "application/pdf"
            or not file.filename
            or not file.filename.lower().endswith(".pdf")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed.",
            )

        safe_filename = os.path.basename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            while content := file.file.read(1024 * 1024):
                buffer.write(content)

        # 2. Look for existing metadata for this school.
        existing = db.execute(
            select(
                SchoolKnowledge.school_name,
                SchoolKnowledge.city,
                SchoolKnowledge.state,
                SchoolKnowledge.address,
                SchoolKnowledge.phone,
                SchoolKnowledge.email,
                SchoolKnowledge.website,
            )
            .where(SchoolKnowledge.school_id == school_id)
            .limit(1)
        ).first()

        if existing:
            details = {
                "school_name": existing.school_name,
                "city": existing.city,
                "state": existing.state,
                "address": existing.address,
                "phone": existing.phone,
                "email": existing.email,
                "website": existing.website,
            }
        else:
            # A new school needs its metadata on the first upload.
            if not school_name or not school_name.strip():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "For a new school, provide school_name and "
                        "city in the upload form."
                    ),
                )

            details = {
                "school_name": school_name.strip(),
                "city": city,
                "state": state,
                "address": address,
                "phone": phone,
                "email": email,
                "website": website,
            }

        # 3. Extract PDF text.
        pages = extract_text_from_pdf(file_path)

        if not pages:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF.",
            )

        # 4. Split the text into chunks.
        chunks = split_text_into_chunks(pages)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="Could not create text chunks from the PDF.",
            )

        # 5. Generate embeddings.
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        # 6. Save school metadata and document chunks.
        rows = []

        for chunk, embedding in zip(chunks, embeddings):
            rows.append(
                SchoolKnowledge(
                    school_id=school_id,
                    school_name=details["school_name"],
                    city=details["city"],
                    state=details["state"],
                    address=details["address"],
                    phone=details["phone"],
                    email=details["email"],
                    website=details["website"],
                    document_id=None,
                    pdf_filename=safe_filename,
                    pdf_url=None,
                    content=chunk["content"],
                    page_number=chunk["page_number"],
                    embedding=embedding,
                    metadata_json={
                        "source": safe_filename,
                    },
                )
            )

        db.add_all(rows)
        db.commit()

        return DocumentUploadResponse(
            message="PDF processed successfully.",
            school_id=school_id,
            school_name=details["school_name"],
            pdf_filename=safe_filename,
            chunks_created=len(chunks),
            embeddings_created=len(embeddings),
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Database error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Failed to save PDF chunks and embeddings.",
        )

    except Exception as exc:
        db.rollback()
        print(f"PDF processing error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Failed to process the PDF.",
        )

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        file.file.close()
