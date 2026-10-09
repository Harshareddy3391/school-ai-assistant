
import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
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


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

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
    db: Session = Depends(get_db),
):
    file_path = None

    try:
        # 1. Find an existing school in the combined table.
        school = db.execute(
            select(SchoolKnowledge.school_id)
            .where(SchoolKnowledge.school_id == school_id)
            .limit(1)
        ).first()

        if school is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "School not found in school_knowledge. "
                    "Insert the school's initial details first."
                ),
            )

        # 2. Validate the uploaded file.
        if (
            file.content_type != "application/pdf"
            or not file.filename
            or not file.filename.lower().endswith(".pdf")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed.",
            )

        # 3. Save the PDF with a unique filename.
        safe_filename = os.path.basename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            while content := file.file.read(1024 * 1024):
                buffer.write(content)

        # 4. Extract text and create chunks.
        pages = extract_text_from_pdf(file_path)

        if not pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from the PDF.",
            )

        chunks = split_text_into_chunks(pages)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create text chunks from the PDF.",
            )

        # 5. Generate embeddings.
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        # 6. Load the school's details.
        school_details = db.execute(
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

        if school_details is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School details could not be found.",
            )

        # 7. Insert one row per chunk into school_knowledge.
        rows = []

        for chunk, embedding in zip(chunks, embeddings):
            rows.append(
                SchoolKnowledge(
                    school_id=school_id,
                    school_name=school_details.school_name,
                    city=school_details.city,
                    state=school_details.state,
                    address=school_details.address,
                    phone=school_details.phone,
                    email=school_details.email,
                    website=school_details.website,
                    document_id=None,
                    pdf_filename=safe_filename,
                    pdf_url=None,
                    content=chunk["content"],
                    page_number=chunk["page_number"],
                    embedding=embedding,
                    metadata_json={},
                )
            )

        db.add_all(rows)
        db.commit()

        return DocumentUploadResponse(
            message="PDF processed successfully.",
            school_id=school_id,
            school_name=school_details.school_name,
            pdf_filename=safe_filename,
            chunks_created=len(chunks),
            embeddings_created=len(embeddings),
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save PDF chunks and embeddings.",
        )

    except Exception as exc:
        db.rollback()
        print(f"PDF processing error: {exc}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the PDF.",
        )

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        file.file.close()
