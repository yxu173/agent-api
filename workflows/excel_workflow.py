import asyncio
import base64
import pandas as pd
import os
import re
from typing import List, Optional, Dict, Any
from textwrap import dedent
from pathlib import Path

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.workflow.v2.types import StepInput, StepOutput
from agno.workflow.v2.workflow import Workflow
from pydantic import BaseModel, Field


class KeywordEvaluation(BaseModel):
    keyword: str = Field(..., description="The keyword being evaluated.")
    reason: str = Field(..., description="The reason for inclusion or exclusion.")


class ExcelChunkAnalysis(BaseModel):
    audience_analysis: str = Field(..., description="Detailed statement of target audience analysis and relevant characteristics.")
    valuable_keywords: List[KeywordEvaluation] = Field(..., description="List of valuable keywords and reasons.")


class ExcelProcessingResult(BaseModel):
    valuable_keywords_found: int = Field(..., description="The total number of valuable keywords found.")
    output_path: str = Field(..., description="The path to the output Excel file.")
    processed_chunks: int = Field(..., description="The number of chunks processed.")


def create_excel_analysis_agent(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create an agent specialized in analyzing Excel data chunks."""
    return Agent(
        name="Excel Keyword Analysis Agent",
        agent_id="excel_keyword_analysis_agent",
        model=OpenAIChat(id=model_id),
        user_id=user_id,
        session_id=session_id,
        instructions=dedent('''
            You are a Seasoned SEO professional specializing in keyword analysis, At the same time you are an expert content creator (these previous two personalities should work in harmony and compatibility), Your task is objectively evaluating keywords for optimal SEO segments, and given complete keyword lists. Choose Keywords that are valuable and useful to readers., as these selected keywords will be used to create informative blog articles.

            Ensure that all evaluations are made solely based on the provided criteria without introducing any personal opinions or assumptions.
            ________________________________________________________________
            The user will provide a message containing the keywords to analyze and their category.
            The niche for all keywords is "Herbalism".
            ________________________________________________________________
            First: analyze the keywords carefully to understand its context and its intent ( informational - commercial - Navigational - Transactional ), to determine the target audience whether it is (beginners OR intermediates OR experts) for the keywords.
            ________________________________________________________________
            **Now,follow the following criteria to choose the valuable keywords:**
            1-Give all Keywords the same level of attention.
            *Note:Keywords can be a sentence, a command, or a question. Never base your analysis on this.*

            2-As You are a SEO expert, Consider multiple perspectives before applying the criteria to choose valuable Keywords and then apply the following criteria in order to choose the valuable Keywords:
            - Keywords must be grammatically and linguistically correct.
            - Valuable Keywords provide deep information yet remain accessible to non-specialists.
            -Valuable Keywords offer practical solutions or scientific benefits.
            - A valuable Keyword is one that can be understood independently, even if presented alone.

            3- Also, as you are a content creator,review each keyword to make sure that:
            -Is it scalable for in-depth content?
            -Does it provide real solutions to the user?
            -Does it maintain clarity and coherence in isolation?
            -Does it provide useful information rather than superficial information?
            - Is it just an informational intention?

            4-After that, Cross-reference the keyword against established industry guidelines and case studies to ensure that its value is consistent across various expert perspectives ( SEO expert and content creators ).

            5-whether category is (beginners OR intermediates OR experts),You should Exclude any keyword that requires a level above the intermediates level to understand.
            ________________________________________________________________
            **Important instructions and considerations:**
            1. Do not include personal opinions regarding the audience 's interests, desires, or perspectives.
            Also "Avoid over‐elaboration or speculative reasoning: focus only on the given criteria without philosophical digressions."
            2. Maintain a professional and objective tone throughout the analysis.
            3. Strictly follow the provided standards without deviation.
            4. Do not make assumptions about a keyword's depth or complexity; treat all keywords equally without any bias to any each.
            5. Do not add any extra emphasis or formatting to the keywords.
            7. Disregard search volume when evaluating keywords.
            8. Ensure that excluded keywords are only listed in the second table, not in the first.
            9. Ensure every keyword is evaluated and appears in one of the two tables (none are neglected).
            10. Scientific abbreviations are acceptable in both upper and lower case.
            11. Keywords that are trivially simple and cannot support in-depth content should be excluded, but if a straightforward keyword can still yield robust, beneficial content, keep it.
            12. If two keywords are ≥ 80 % similar, keep the clearer phrasing and the other similar in the excluded table.
            12. Exclude any non-English keywords.
            ________________________________________________________________
            **Remember that the two personas ( the SEO expert and expert content creator ), must work in integration and harmony, without any distractions, contradictions, or objections.**
            ________________________________________________________________
            IMPORTANT: Only select keywords that are a single word (no spaces, not a phrase, not a question, not a sentence). Exclude any keyword that is not a single word. For both valuable and excluded keywords, the 'keyword' field must contain only a single word.
            ________________________________________________________________
            **Several lists of keywords will be provided in the same chat, so you are required to deal with each list completely independently to avoid confusion or merging or comparing between the lists.**
            
            DEBUG: When you receive keywords, analyze them and return the structured response. If you don't receive keywords, return an error message.
        '''),
        storage=SqliteStorage(table_name="excel_analysis_agent", db_file="tmp/excel_analysis_agent.db"),
        response_model=ExcelChunkAnalysis,
        use_json_mode=True,
        debug_mode=debug_mode,
        stream=False,
    )


def base64_to_excel_step(step_input: StepInput) -> StepOutput:
    """Convert base64 string to Excel file or handle direct keywords."""
    input_message = step_input.message
    print(f"DEBUG: Received input of length: {len(input_message)}")
    
    # Clean up the input message - remove timestamps and extra formatting
    cleaned_message = clean_base64_input(input_message)
    print(f"DEBUG: Cleaned input length: {len(cleaned_message)}")
    
    # Check if input looks like base64 (contains only base64 characters and is longer than typical keywords)
    import re
    base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    
    # If input looks like base64 and is longer than 100 characters, treat as base64
    if len(cleaned_message) > 100 and base64_pattern.match(cleaned_message.strip()):
        print(f"DEBUG: Input appears to be base64, length: {len(cleaned_message)}")
        
        # Create temporary file path with default session
        session_id = 'default'
        excel_file_path = f"tmp/input_excel_{session_id}.xlsx"
        
        # Ensure tmp directory exists
        os.makedirs("tmp", exist_ok=True)
        
        try:
            # Decode base64 string
            excel_data = base64.b64decode(cleaned_message)
            print(f"DEBUG: Decoded base64 to {len(excel_data)} bytes")
            
            # Save to file
            with open(excel_file_path, 'wb') as f:
                f.write(excel_data)
            
            print(f"DEBUG: Saved Excel file to: {excel_file_path}")
            
            return StepOutput(
                content=f"EXCEL_FILE_PATH:{excel_file_path}"
            )
        except Exception as e:
            print(f"DEBUG: Error converting base64 to Excel file: {e}")
            return StepOutput(
                content=f"Error converting base64 to Excel file: {e}"
            )
    else:
        # Input appears to be direct keywords, create a simple Excel file
        print(f"DEBUG: Input appears to be direct keywords, creating Excel file")
        
        # Create temporary file path with default session
        session_id = 'default'
        excel_file_path = f"tmp/input_excel_{session_id}.xlsx"
        
        # Ensure tmp directory exists
        os.makedirs("tmp", exist_ok=True)
        
        try:
            # Parse the keywords from the input
            lines = cleaned_message.strip().split('\n')
            keywords_data = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Keyword\tRelevance\tCategory'):
                    # Split by tab or comma
                    parts = line.split('\t') if '\t' in line else line.split(',')
                    if len(parts) >= 1:
                        keyword = parts[0].strip()
                        category = parts[2].strip() if len(parts) >= 3 else 'general'
                        if keyword and keyword.lower() not in ['nan', 'none', '']:
                            keywords_data.append({
                                'keyword': keyword,
                                'category': category
                            })
            
            if keywords_data:
                # Create DataFrame and save to Excel
                df = pd.DataFrame(keywords_data)
                df.to_excel(excel_file_path, index=False)
                print(f"DEBUG: Created Excel file with {len(keywords_data)} keywords")
                
                return StepOutput(
                    content=f"EXCEL_FILE_PATH:{excel_file_path}"
                )
            else:
                print(f"DEBUG: No valid keywords found in direct input")
                return StepOutput(
                    content="No valid keywords found in the input. Please provide keywords in the format: 'keyword\tcategory' or as a base64 encoded Excel file."
                )
                
        except Exception as e:
            print(f"DEBUG: Error creating Excel file from direct input: {e}")
            return StepOutput(
                content=f"Error creating Excel file from direct input: {e}"
            )


def clean_base64_input(input_text: str) -> str:
    """Clean base64 input by removing timestamps and extra formatting."""
    lines = input_text.strip().split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        
        # Skip timestamp lines (lines that start with date/time pattern)
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line):
            continue
        
        # Skip lines that are just whitespace or formatting
        if re.match(r'^\s*$', line):
            continue
        
        # Extract base64 content from lines that might have extra formatting
        # Look for base64 characters in the line
        base64_chars = re.findall(r'[A-Za-z0-9+/=]+', line)
        if base64_chars:
            # Join all base64 parts found in the line
            cleaned_lines.append(''.join(base64_chars))
    
    # Join all cleaned lines
    return ''.join(cleaned_lines)


def prepare_excel_chunk_step(step_input: StepInput) -> StepOutput:
    """Prepare Excel chunk data for keyword analysis."""
    # Extract file path from previous step's message
    message = step_input.message
    print(f"DEBUG: prepare_excel_chunk_step received message: {message[:100]}...")
    
    if message.startswith("EXCEL_FILE_PATH:"):
        excel_file_path = message.split(":", 1)[1]
        print(f"DEBUG: Extracted Excel file path: {excel_file_path}")
    else:
        print(f"DEBUG: Message does not start with EXCEL_FILE_PATH: {message[:100]}...")
        return StepOutput(
            content="Error: No Excel file path received from previous step"
        )
    
    session_id = 'default'
    
    try:
        df = pd.read_excel(excel_file_path)
        print(f"DEBUG: Excel file loaded with {len(df)} rows and columns: {list(df.columns)}")
        
        keyword_column = None
        category_column = None
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['keyword', 'term', 'phrase', 'word']):
                keyword_column = col
            elif any(cat in col_lower for cat in ['category', 'type', 'class', 'group']):
                category_column = col
        
        if not keyword_column:
            keyword_column = df.columns[0]
        
        if not category_column:
            category_column = 'category'
            df[category_column] = 'general'
        
        print(f"DEBUG: Using keyword column: '{keyword_column}', category column: '{category_column}'")
        
        keywords_with_category = []
        for _, row in df.iterrows():
            keyword = str(row[keyword_column]).strip()
            category = str(row[category_column]).strip()
            if keyword and keyword.lower() not in ['nan', 'none', '']:
                keywords_with_category.append({
                    'keyword': keyword,
                    'category': category
                })
        
        print(f"DEBUG: Extracted {len(keywords_with_category)} valid keywords")
        
        if keywords_with_category:
            keywords_text = "Please analyze the following keywords from the Excel file:\n\n"
            for item in keywords_with_category:
                keywords_text += f"- Keyword: {item['keyword']}, Category: {item['category']}\n"
            
            print(f"DEBUG: Sending to AI agent: {keywords_text[:200]}...")
            print(f"DEBUG: Total keywords to analyze: {len(keywords_with_category)}")
            print(f"DEBUG: First few keywords: {keywords_with_category[:3]}")
            
            return StepOutput(
                content=keywords_text
            )
        else:
            print("DEBUG: No valid keywords found in Excel file")
            return StepOutput(
                content="No keywords found in the Excel file. Please ensure the file contains valid keyword data in the expected format."
            )
        
    except Exception as e:
        print(f"DEBUG: Error in prepare_excel_chunk_step: {e}")
        return StepOutput(
            content=f"Error preparing Excel chunk: {e}"
        )


def debug_agent_input_step(step_input: StepInput) -> StepOutput:
    """Debug step to see what the agent receives."""
    print(f"DEBUG: Agent input step received message: {step_input.message[:500]}...")
    print(f"DEBUG: Agent input step message length: {len(step_input.message)}")
    
    if step_input.message.startswith("Error:") or step_input.message.startswith("No keywords") or step_input.message.startswith("No valid keywords"):
        print(f"DEBUG: Detected error message, skipping AI agent")
        return StepOutput(
            content="The input could not be processed. Please ensure you provide either:\n1. A base64 encoded Excel file with keywords\n2. Direct keywords in the format: 'keyword\tcategory'"
        )
    
    return StepOutput(content=step_input.message)


def accumulate_analysis_results(step_input: StepInput) -> StepOutput:
    """Accumulate analysis results in a session-specific Excel file."""
    analysis_result = step_input.previous_step_content
    print(f"DEBUG: Received analysis result type: {type(analysis_result)}")
    print(f"DEBUG: Analysis result content: {analysis_result}")
    
    if isinstance(analysis_result, str) and (analysis_result.startswith("The input could not be processed") or 
                                            analysis_result.startswith("No keywords") or 
                                            analysis_result.startswith("No valid keywords")):
        print(f"DEBUG: Received error message, not processing analysis results")
        return StepOutput(
            content=analysis_result
        )
    
    if hasattr(analysis_result, 'valuable_keywords'):
        valuable_keywords = analysis_result.valuable_keywords
    else:
        # Handle case where the result might be a string or other format
        valuable_keywords = []
    
    # Convert to list of dictionaries for Excel storage
    keywords_data = []
    for keyword_eval in valuable_keywords:
        keywords_data.append({
            'keyword': keyword_eval.keyword,
            'reason': keyword_eval.reason
        })
    
    # Get session ID from the workflow context or use a default
    session_id = 'default'
    if hasattr(step_input, 'workflow_state') and step_input.workflow_state:
        session_id = step_input.workflow_state.get('session_id', 'default')
    
    # Create session-specific Excel file
    session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
    os.makedirs("tmp", exist_ok=True)
    
    # Load existing results from Excel file
    existing_keywords = []
    if os.path.exists(session_excel_file):
        try:
            existing_df = pd.read_excel(session_excel_file)
            existing_keywords = existing_df.to_dict('records')
        except:
            existing_keywords = []
    
    # Add new keywords
    existing_keywords.extend(keywords_data)
    
    # Save updated results to Excel file
    if existing_keywords:
        df = pd.DataFrame(existing_keywords)
        df.to_excel(session_excel_file, index=False)
    
    return StepOutput(
        content=f"Successfully processed {len(keywords_data)} valuable keywords from this chunk. Total accumulated in session: {len(existing_keywords)} keywords. File: {session_excel_file}"
    )


def save_session_results(step_input: StepInput) -> StepOutput:
    """Finalize the session Excel file and provide download link."""
    # Get session ID from the workflow context
    session_id = 'default'
    if hasattr(step_input, 'workflow_state') and step_input.workflow_state:
        session_id = step_input.workflow_state.get('session_id', 'default')
    
    # Check the session Excel file
    session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
    session_keywords = []
    
    if os.path.exists(session_excel_file):
        try:
            df = pd.read_excel(session_excel_file)
            session_keywords = df.to_dict('records')
        except:
            session_keywords = []
    
    if session_keywords:
        return StepOutput(
            content=f"Session complete! Successfully processed {len(session_keywords)} total valuable keywords. Your Excel file is ready: {session_excel_file}"
        )
    else:
        return StepOutput(
            content="Session complete! No valuable keywords found in this session."
        )


def create_excel_workflow(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create an Excel processing workflow using Agno workflow v2."""
    
    # Create the analysis agent
    analysis_agent = create_excel_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow
    workflow = Workflow(
        name="Excel Keyword Processing Workflow",
        description="Process base64 Excel files containing keywords and analyze them for SEO value",
        storage=SqliteStorage(
            table_name="excel_processing_workflow",
            db_file="tmp/excel_processing_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            base64_to_excel_step,
            prepare_excel_chunk_step,
            debug_agent_input_step,
            analysis_agent,
            accumulate_analysis_results,
            save_session_results,
        ],
    )
    
    return workflow


def create_playground_excel_workflow(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create an Excel processing workflow for the playground interface."""
    
    # Create the analysis agent
    analysis_agent = create_excel_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow
    workflow = Workflow(
        name="Excel Keyword Analysis Workflow",
        description="Process base64 Excel files or direct keywords and analyze them for SEO value. Each message processes keywords from the Excel file.",
        storage=SqliteStorage(
            table_name="excel_playground_workflow",
            db_file="tmp/excel_playground_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            base64_to_excel_step,
            prepare_excel_chunk_step,
            debug_agent_input_step,
            analysis_agent,
            accumulate_analysis_results,
        ],
    )
    
    return workflow


def create_session_based_excel_workflow(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create an Excel processing workflow that accumulates results across multiple runs."""
    
    # Create the analysis agent
    analysis_agent = create_excel_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow with session-based accumulation
    workflow = Workflow(
        name="Excel Session-Based Analysis Workflow",
        description="Process base64 Excel files containing keywords and analyze them for SEO value with session-based accumulation",
        storage=SqliteStorage(
            table_name="excel_session_workflow",
            db_file="tmp/excel_session_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            base64_to_excel_step,
            prepare_excel_chunk_step,
            debug_agent_input_step,
            analysis_agent,
            accumulate_analysis_results,
            save_session_results,
        ],
    )
    
    return workflow


async def process_base64_excel_complete(
    base64_string: str,
    chunk_size: int = 100,
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ExcelProcessingResult:
    """
    Process base64 Excel file completely using workflow.
    
    Args:
        base64_string: Base64 encoded Excel file
        chunk_size: Number of columns to process in each chunk
        model_id: OpenAI model ID to use
        user_id: User ID for the agent
        session_id: Session ID for the agent
    
    Returns:
        ExcelProcessingResult with processing information
    """
    
    # Create the workflow
    workflow = create_excel_workflow(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=True
    )
    
    result = await workflow.arun(base64_string)
    
    session_id = session_id or 'default'
    session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
    
    valuable_keywords_found = 0
    processed_chunks = 0
    
    if os.path.exists(session_excel_file):
        try:
            df = pd.read_excel(session_excel_file)
            valuable_keywords_found = len(df)
            processed_chunks = 1  # Since we're processing one file at a time
        except:
            pass
    
    return ExcelProcessingResult(
        valuable_keywords_found=valuable_keywords_found,
        output_path=session_excel_file,
        processed_chunks=processed_chunks
    )

async def main():
    """Example usage of the Excel workflow."""
    base64_excel = "base64_encoded_excel_file_content_here"
    
    result = await process_base64_excel_complete(
        base64_string=base64_excel,
        chunk_size=100,
        model_id="o4-mini",
        session_id="test_session"
    )
    
    print(f"Processing complete!")
    print(f"Valuable keywords found: {result.valuable_keywords_found}")
    print(f"Processed chunks: {result.processed_chunks}")
    print(f"Output saved to: {result.output_path}")


if __name__ == "__main__":
    asyncio.run(main())