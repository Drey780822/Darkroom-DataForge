from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from backend.app.database import clear_database

router = APIRouter(prefix="/system", tags=["System"])

class ResetDatabaseRequest(BaseModel):
    clear_files: Optional[bool] = False

class ResetDatabaseResponse(BaseModel):
    status: str
    message: str
    tables_recreated: int
    files_removed: int

@router.post("/reset-database", response_model=ResetDatabaseResponse)
def reset_database_endpoint(payload: Optional[ResetDatabaseRequest] = None):
    """Completely resets the SQLite database and sequences for a fresh start.
    Optionally removes uploaded files and exports.
    """
    clear_files = payload.clear_files if payload else False
    try:
        result = clear_database(clear_files=clear_files)
        return ResetDatabaseResponse(
            status=result["status"],
            message=result["message"],
            tables_recreated=result["tables_recreated"],
            files_removed=result["files_removed"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}",
        )
