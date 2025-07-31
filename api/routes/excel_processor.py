from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import base64
import os

from agents.excel_processor_agent import process_base64_excel_with_agent
from workflows.excel_workflow import process_base64_excel_complete

excel_processor_router = APIRouter(prefix="/excel-processor", tags=["Excel Processor"])


class Base64ExcelRequest(BaseModel):
    base64_string: str = Field(..., description="Base64 encoded Excel file")
    chunk_size: int = Field(default=100, description="Number of columns to process in each chunk")
    model_id: str = Field(default="o4-mini", description="OpenAI model ID to use")
    user_id: Optional[str] = Field(default=None, description="User ID for the agent")
    session_id: Optional[str] = Field(default=None, description="Session ID for the agent")


class ExcelProcessingResponse(BaseModel):
    input_file_path: str
    output_file_path: str
    total_columns: int
    total_chunks: int
    processing_status: str
    message: str


@excel_processor_router.post("/process", response_model=ExcelProcessingResponse)
async def process_excel_file(request: Base64ExcelRequest):
    """
    Process a base64 encoded Excel file in chunks using AI agent.
    
    This endpoint:
    1. Converts base64 string to Excel file
    2. Processes the Excel file in chunks of specified size
    3. Analyzes each chunk with OpenAI o4-mini model
    4. Saves results to a new Excel file
    5. Returns processing information
    """
    try:
        # Validate base64 string
        try:
            base64.b64decode(request.base64_string)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 string: {e}")
        
        # Process the Excel file
        result = await process_base64_excel_with_agent(
            base64_string=request.base64_string,
            chunk_size=request.chunk_size,
            model_id=request.model_id,
            user_id=request.user_id,
            session_id=request.session_id,
            debug_mode=True
        )
        
        return ExcelProcessingResponse(
            input_file_path=result.input_file_path,
            output_file_path=result.output_file_path,
            total_columns=result.total_columns,
            total_chunks=result.total_chunks,
            processing_status=result.processing_status,
            message=f"Successfully processed {result.total_columns} columns in {result.total_chunks} chunks"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {e}")


@excel_processor_router.post("/process-workflow", response_model=ExcelProcessingResponse)
async def process_excel_file_workflow(request: Base64ExcelRequest):
    """
    Process a base64 encoded Excel file using Agno workflow v2.
    
    This endpoint uses the complete workflow approach:
    1. Converts base64 string to Excel file
    2. Processes the Excel file in chunks using workflow steps
    3. Analyzes each chunk with OpenAI o4-mini model
    4. Saves results to a new Excel file
    5. Returns processing information
    """
    try:
        # Validate base64 string
        try:
            base64.b64decode(request.base64_string)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 string: {e}")
        
        # Process the Excel file using workflow
        result = await process_base64_excel_complete(
            base64_string=request.base64_string,
            chunk_size=request.chunk_size,
            model_id=request.model_id,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        return ExcelProcessingResponse(
            input_file_path=result.input_file_path,
            output_file_path=result.output_file_path,
            total_columns=result.total_columns,
            total_chunks=result.total_chunks,
            processing_status=result.processing_status,
            message=f"Successfully processed {result.total_columns} columns in {result.total_chunks} chunks using workflow"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {e}")


@excel_processor_router.get("/health")
async def health_check():
    """Health check endpoint for the Excel processor."""
    return {"status": "healthy", "service": "excel-processor"} 