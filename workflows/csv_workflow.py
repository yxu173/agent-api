import asyncio
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
from textwrap import dedent
import json
import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.workflow.v2.types import StepInput, StepOutput
from agno.workflow.v2.workflow import Workflow
from pydantic import BaseModel, Field


class KeywordEvaluation(BaseModel):
    keyword: str = Field(..., description="The keyword being evaluated.")
    reason: str = Field(..., description="The reason for inclusion or exclusion.")


class SEOKeywordAnalysis(BaseModel):
    audience_analysis: str = Field(..., description="Detailed statement of target audience analysis and relevant characteristics.")
    valuable_keywords: List[KeywordEvaluation] = Field(..., description="List of valuable keywords and reasons.")


class CSVProcessingResult(BaseModel):
    valuable_keywords_found: int = Field(..., description="The total number of valuable keywords found.")
    output_path: str = Field(..., description="The path to the output Excel file.")
    processed_chunks: int = Field(..., description="The number of chunks processed.")


def create_csv_analysis_agent(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create an agent specialized in analyzing CSV keyword data."""
    return Agent(
        name="CSV Keyword Analysis Agent",
        agent_id="csv_keyword_analysis_agent",
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
        '''),
        storage=SqliteStorage(table_name="csv_keyword_analysis_agent", db_file="tmp/csv_keyword_analysis_agent.db"),
        response_model=SEOKeywordAnalysis,
        use_json_mode=True,
        debug_mode=debug_mode,
        stream=False,
    )


def prepare_csv_chunk_for_analysis(step_input: StepInput) -> StepOutput:
    """Prepare CSV chunk data for analysis by the AI agent."""
    chunk_data = step_input.message
    
    # Extract chunk information from the input
    # The input should contain the CSV chunk data
    return StepOutput(
        content=dedent(f"""\
        Please analyze the following keywords from the CSV chunk:
        
        {chunk_data}
        
        Please provide a structured analysis of these keywords according to the SEO criteria.
        """)
    )


def accumulate_analysis_results(step_input: StepInput) -> StepOutput:
    """Accumulate analysis results in a session-specific Excel file."""
    analysis_result = step_input.previous_step_content
    
    # Extract the valuable keywords from the analysis
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


def create_session_based_csv_workflow(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create a CSV processing workflow that accumulates results across multiple runs."""
    
    # Create the analysis agent
    analysis_agent = create_csv_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow with session-based accumulation
    workflow = Workflow(
        name="CSV Session-Based Analysis Workflow",
        description="Process CSV files containing keywords and analyze them for SEO value with session-based accumulation",
        storage=SqliteStorage(
            table_name="csv_session_workflow",
            db_file="tmp/csv_session_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            prepare_csv_chunk_for_analysis,
            analysis_agent,
            accumulate_analysis_results,
            save_session_results,
        ],
    )
    
    return workflow


async def process_csv_file_with_session_workflow(
    input_file_path: str,
    output_file_path: str,
    keyword_column: str = 'keyword',
    category_column: str = 'category',
    chunk_size: int = 100,
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> CSVProcessingResult:
    """
    Process a CSV file using Agno workflow v2 with session-based file creation.
    
    Args:
        input_file_path: Path to the input CSV file
        output_file_path: Path to save the output CSV file
        keyword_column: Name of the column containing keywords
        category_column: Name of the column containing categories
        chunk_size: Number of rows to process in each chunk
        model_id: OpenAI model ID to use
        user_id: User ID for the agent
        session_id: Session ID for the agent
    
    Returns:
        CSVProcessingResult with processing statistics
    """
    
    # Read the CSV file
    try:
        df = pd.read_csv(input_file_path)
    except FileNotFoundError:
        raise ValueError(f"File not found: {input_file_path}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    if keyword_column not in df.columns:
        raise ValueError(f"Keyword column '{keyword_column}' not found in the CSV file.")
    if category_column not in df.columns:
        raise ValueError(f"Category column '{category_column}' not found in the CSV file.")

    # Create the session-based workflow
    session_workflow = create_session_based_csv_workflow(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=True
    )

    # Process the CSV in chunks
    total_rows = len(df)
    processed_chunks = 0

    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk_df = df.iloc[start:end]
        processed_chunks += 1

        # Prepare chunk data for analysis
        keywords_with_category = chunk_df[[keyword_column, category_column]].to_dict('records')
        
        chunk_message = f"Please analyze the following keywords (chunk {processed_chunks} of {(total_rows + chunk_size - 1) // chunk_size}):\n"
        for item in keywords_with_category:
            chunk_message += f"- Keyword: {item[keyword_column]}, Category: {item[category_column]}\n"

        # Run the workflow for this chunk
        try:
            result = await session_workflow.arun(chunk_message)
            print(f"Processed chunk {processed_chunks}/{total_rows // chunk_size + 1}")
            
        except Exception as e:
            print(f"Warning: Error processing chunk {start}-{end}: {e}")
            continue

    # Get the session Excel file path
    session_id = session_id or 'default'
    session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
    
    # Count the total keywords from the session file
    total_keywords = 0
    if os.path.exists(session_excel_file):
        try:
            df = pd.read_excel(session_excel_file)
            total_keywords = len(df)
        except:
            total_keywords = 0

    return CSVProcessingResult(
        valuable_keywords_found=total_keywords,
        output_path=session_excel_file,
        processed_chunks=processed_chunks
    )


def create_csv_workflow_for_playground(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create a CSV processing workflow for the playground interface with session-based file creation."""
    
    # Create the analysis agent
    analysis_agent = create_csv_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow with session-based accumulation
    workflow = Workflow(
        name="CSV Keyword Analysis Workflow",
        description="Process CSV files containing keywords and analyze them for SEO value with session-based output. Each message in the same session will add keywords to the same Excel file.",
        storage=SqliteStorage(
            table_name="csv_playground_workflow",
            db_file="tmp/csv_playground_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            prepare_csv_chunk_for_analysis,
            analysis_agent,
            accumulate_analysis_results,
        ],
    )
    
    return workflow


def create_playground_csv_workflow_with_session(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create a playground CSV workflow that properly handles session-based accumulation."""
    
    # Create the analysis agent
    analysis_agent = create_csv_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
    
    # Create the workflow with session-based accumulation
    workflow = Workflow(
        name="CSV Playground Session Workflow",
        description="Process keywords and accumulate results in session-specific Excel file. Each message adds to the same file.",
        storage=SqliteStorage(
            table_name="csv_playground_session_workflow",
            db_file="tmp/csv_playground_session_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            prepare_csv_chunk_for_analysis,
            analysis_agent,
            accumulate_analysis_results,
        ],
    )
    
    return workflow


# Example usage function
async def main():
    """Example usage of the CSV workflow."""
    input_file = "/home/yxu/INFORMATIONAL.xlsx"
    output_file = "output_valuable_keywords.xlsx"
    
    result = await process_csv_file_with_session_workflow(
        input_file_path=input_file,
        output_file_path=output_file,
        keyword_column='keyword',
        category_column='category',
        chunk_size=100,
        model_id="o4-mini"
    )
    
    print(f"Processing complete!")
    print(f"Valuable keywords found: {result.valuable_keywords_found}")
    print(f"Output saved to: {result.output_path}")
    print(f"Chunks processed: {result.processed_chunks}")


if __name__ == "__main__":
    asyncio.run(main()) 