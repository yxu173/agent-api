import base64
import pandas as pd
import io
import os
from typing import List, Optional, Dict, Any
from textwrap import dedent
from pathlib import Path

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from pydantic import BaseModel, Field


class ExcelChunkResult(BaseModel):
    chunk_number: int = Field(..., description="The chunk number being processed")
    total_chunks: int = Field(..., description="Total number of chunks")
    processed_columns: List[str] = Field(..., description="List of column names processed in this chunk")
    analysis_result: str = Field(..., description="AI analysis result for this chunk")
    status: str = Field(..., description="Status of the processing")


class ExcelProcessingResult(BaseModel):
    input_file_path: str = Field(..., description="Path to the input Excel file")
    output_file_path: str = Field(..., description="Path to the output Excel file")
    total_columns: int = Field(..., description="Total number of columns processed")
    total_chunks: int = Field(..., description="Total number of chunks processed")
    processing_status: str = Field(..., description="Overall processing status")


def get_excel_processor_agent(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create an agent specialized in processing Excel files from base64 input."""
    return Agent(
        name="Excel Processor Agent",
        agent_id="excel_processor_agent",
        model=OpenAIChat(id=model_id),
        user_id=user_id,
        session_id=session_id,
        instructions=dedent('''
            You are an Excel data analysis expert. Your task is to analyze Excel file data that has been converted from base64 format.
            
            When you receive Excel data, you should:
            1. Analyze the structure and content of the data
            2. Identify patterns, trends, and insights
            3. Provide meaningful analysis of the data
            4. Suggest potential improvements or observations
            5. Format your response in a clear, structured manner
            
            The data you receive will be in chunks of up to 100 columns from an Excel file. Each chunk represents a portion of the original file.
            
            Provide analysis that includes:
            - Data structure overview
            - Key insights and patterns
            - Potential data quality issues
            - Recommendations for data processing
            - Summary of findings
            
            Be thorough but concise in your analysis.
        '''),
        storage=SqliteStorage(table_name="excel_processor_agent", db_file="tmp/excel_processor_agent.db"),
        response_model=ExcelChunkResult,
        use_json_mode=True,
        debug_mode=debug_mode,
        stream=False,
    )


def base64_to_excel_file(base64_string: str, output_path: str) -> str:
    """Convert base64 string to Excel file and save it."""
    try:
        # Decode base64 string
        excel_data = base64.b64decode(base64_string)
        
        # Save to file
        with open(output_path, 'wb') as f:
            f.write(excel_data)
        
        return output_path
    except Exception as e:
        raise ValueError(f"Error converting base64 to Excel file: {e}")


def process_excel_in_chunks(
    excel_file_path: str,
    chunk_size: int = 100,
    output_file_path: str = None
) -> ExcelProcessingResult:
    """
    Process Excel file in chunks of specified column size.
    
    Args:
        excel_file_path: Path to the input Excel file
        chunk_size: Number of columns to process in each chunk
        output_file_path: Path for the output Excel file
    
    Returns:
        ExcelProcessingResult with processing information
    """
    
    # Read the Excel file
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")
    
    # Get column names
    columns = df.columns.tolist()
    total_columns = len(columns)
    
    # Calculate number of chunks
    total_chunks = (total_columns + chunk_size - 1) // chunk_size
    
    # Initialize results storage
    all_results = []
    
    # Process each chunk
    for i in range(0, total_columns, chunk_size):
        chunk_columns = columns[i:i + chunk_size]
        chunk_df = df[chunk_columns]
        
        # Create chunk result
        chunk_result = {
            'chunk_number': (i // chunk_size) + 1,
            'total_chunks': total_chunks,
            'processed_columns': chunk_columns,
            'data_sample': chunk_df.head().to_dict('records'),
            'column_count': len(chunk_columns)
        }
        
        all_results.append(chunk_result)
    
    # Save results to output Excel file
    if output_file_path is None:
        output_file_path = f"tmp/excel_processing_results_{os.path.basename(excel_file_path)}"
    
    # Create a DataFrame with the results
    results_df = pd.DataFrame(all_results)
    results_df.to_excel(output_file_path, index=False)
    
    return ExcelProcessingResult(
        input_file_path=excel_file_path,
        output_file_path=output_file_path,
        total_columns=total_columns,
        total_chunks=total_chunks,
        processing_status="completed"
    )


async def process_base64_excel_with_agent(
    base64_string: str,
    chunk_size: int = 100,
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True
) -> ExcelProcessingResult:
    """
    Process base64 Excel file using AI agent in chunks.
    
    Args:
        base64_string: Base64 encoded Excel file
        chunk_size: Number of columns to process in each chunk
        model_id: OpenAI model ID to use
        user_id: User ID for the agent
        session_id: Session ID for the agent
        debug_mode: Whether to enable debug mode
    
    Returns:
        ExcelProcessingResult with processing information
    """
    
    # Create temporary input file path
    input_file_path = f"tmp/input_excel_{session_id or 'default'}.xlsx"
    output_file_path = f"tmp/output_excel_{session_id or 'default'}.xlsx"
    
    # Ensure tmp directory exists
    os.makedirs("tmp", exist_ok=True)
    
    # Convert base64 to Excel file
    excel_file_path = base64_to_excel_file(base64_string, input_file_path)
    
    # Create the agent
    agent = get_excel_processor_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Read the Excel file
    df = pd.read_excel(excel_file_path)
    columns = df.columns.tolist()
    total_columns = len(columns)
    total_chunks = (total_columns + chunk_size - 1) // chunk_size
    
    # Process each chunk with the agent
    all_analysis_results = []
    
    for i in range(0, total_columns, chunk_size):
        chunk_columns = columns[i:i + chunk_size]
        chunk_df = df[chunk_columns]
        
        # Prepare data for agent analysis
        chunk_data = {
            'chunk_number': (i // chunk_size) + 1,
            'total_chunks': total_chunks,
            'columns': chunk_columns,
            'data_sample': chunk_df.head().to_dict('records'),
            'data_shape': chunk_df.shape
        }
        
        # Create message for agent
        message = f"""
        Please analyze the following Excel data chunk:
        
        Chunk {chunk_data['chunk_number']} of {chunk_data['total_chunks']}
        Columns: {chunk_data['columns']}
        Data Shape: {chunk_data['data_shape']}
        
        Sample Data:
        {chunk_data['data_sample']}
        
        Please provide a comprehensive analysis of this data chunk.
        """
        
        # Get agent response
        try:
            response = await agent.arun(message)
            all_analysis_results.append(response)
        except Exception as e:
            print(f"Error processing chunk {chunk_data['chunk_number']}: {e}")
            continue
    
    # Save all results to output Excel file
    results_data = []
    for result in all_analysis_results:
        results_data.append({
            'chunk_number': result.chunk_number,
            'total_chunks': result.total_chunks,
            'processed_columns': ', '.join(result.processed_columns),
            'analysis_result': result.analysis_result,
            'status': result.status
        })
    
    results_df = pd.DataFrame(results_data)
    results_df.to_excel(output_file_path, index=False)
    
    return ExcelProcessingResult(
        input_file_path=input_file_path,
        output_file_path=output_file_path,
        total_columns=total_columns,
        total_chunks=total_chunks,
        processing_status="completed"
    ) 