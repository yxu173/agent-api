from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import os
from logging import getLogger

from api.routes.agents import agents_router
from api.routes.health import health_router
from api.routes.playground import playground_router

logger = getLogger(__name__)

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(agents_router)
v1_router.include_router(playground_router)

# Create a separate router for file downloads
download_router = APIRouter(prefix="/downloads", tags=["Downloads"])

@download_router.get("/excel/{session_id}")
async def download_excel_file(session_id: str):
    """
    Download the processed Excel file for a specific session.
    
    Args:
        session_id: The session ID to download the file for
        
    Returns:
        The Excel file as a downloadable response
    """
    file_path = f"tmp/session_keywords_{session_id}.xlsx"
    
    logger.info(f"Download request for session {session_id}, file path: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Excel file not found for session {session_id}"
        )
    
    logger.info(f"File found, serving: {file_path}")
    
    return FileResponse(
        path=file_path,
        filename=f"keywords_analysis_{session_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Include the download router in the main v1 router
v1_router.include_router(download_router)
