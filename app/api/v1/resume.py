"""Resume upload and management endpoints."""
from __future__ import annotations

import logging
from io import BytesIO

import fitz  # PyMuPDF
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy import select

from app.db.base import async_session
from app.db.models.user import User
from app.deps import get_current_user
from app.tasks.resume_tasks import embed_resume_background

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF.
    
    Args:
        pdf_bytes: PDF file contents as bytes
    
    Returns:
        Extracted text
    
    Raises:
        ValueError: If PDF cannot be read
    """
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text() + "\n"
        
        pdf_document.close()
        return text
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}") from e


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Upload and process a resume PDF.
    
    Accepts a PDF file, extracts text, stores it in the database,
    and queues semantic embedding for job ranking.
    
    Args:
        file: PDF file upload
        user: Current authenticated user
    
    Returns:
        Success message with resume info
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file contents
        contents = await file.read()
        
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Extract text
        resume_text = _extract_text_from_pdf(contents)
        
        if not resume_text or len(resume_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Resume text too short or empty")
        
        # Store resume text in database
        async with async_session() as session:
            user_record = await session.get(User, user.id)
            if not user_record:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_record.resume_text = resume_text
            user_record.resume_path = f"uploaded/{user.id}/{file.filename}"
            await session.commit()
            logger.info(f"Stored resume for user {user.id}: {len(resume_text)} chars")
        
        # Queue embedding as background task
        embed_resume_background.delay(str(user.id), resume_text)
        logger.info(f"Queued resume embedding for user {user.id}")
        
        return {
            "status": "success",
            "message": "Resume uploaded and queued for processing",
            "filename": file.filename,
            "chars": len(resume_text),
        }
    
    except ValueError as e:
        logger.error(f"Resume extraction error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error uploading resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing resume") from e
