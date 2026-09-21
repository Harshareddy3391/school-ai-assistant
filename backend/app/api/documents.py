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
from app.models.document import Document, DocumentChunk
from app.models.school import School
from app.schemas.document import DocumentResponse
from app.services.pdf_service import extract_text_from_pdf
from app.rag.chunking import split_text_into_chunks
from app.services.embedding_service import generate_embeddings


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
    file_path = None

    try:
        # 1. Check school
        school = db.get(
            School,
            school_id
        )

        if school is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found"
            )

        # 2. Check PDF
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )

        # 3. Generate unique filename
        unique_filename = (
            f"{uuid.uuid4()}_{file.filename}"
        )

        file_path = os.path.join(
            UPLOAD_DIR,
            unique_filename
        )

        # 4. Save PDF
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        # 5. Extract text
        pages = extract_text_from_pdf(
            file_path
        )

        if not pages:
            os.remove(file_path)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from PDF"
            )

        # 6. Create chunks
        chunks = split_text_into_chunks(
            pages
        )

        if not chunks:
            os.remove(file_path)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create text chunks"
            )

        # 7. Generate embeddings
        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        embeddings = generate_embeddings(
            texts
        )

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Number of embeddings does not match number of chunks"
            )

        # 8. Create document
        document = Document(
            school_id=school_id,
            filename=file.filename,
            file_path=file_path,
            document_type="PDF"
        )

        db.add(document)

        # Generate document ID before creating chunks
        db.flush()

        # 9. Save chunks + embeddings
        for chunk, embedding in zip(
            chunks,
            embeddings
        ):
            document_chunk = DocumentChunk(
                document_id=document.id,
                school_id=school_id,
                content=chunk["content"],
                page_number=chunk["page_number"],
                embedding=embedding
            )

            db.add(document_chunk)

        # 10. Commit everything
        db.commit()

        # 11. Refresh document
        db.refresh(document)

        print(
            f"PDF processed successfully: "
            f"{len(pages)} pages, "
            f"{len(chunks)} chunks, "
            f"{len(embeddings)} embeddings"
        )

        return document

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document, chunks, and embeddings"
        )

    except Exception:
        db.rollback()

        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process PDF"
        )