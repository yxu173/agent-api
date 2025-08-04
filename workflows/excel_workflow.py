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
from agno.workflow.v2 import Loop
from pydantic import BaseModel, Field

current_row_position = 0


def read_excel_chunk_with_calamine(filename: str, chunk_size: int = 100, reset_position: bool = False) -> tuple[pd.DataFrame, int, int]:
    """
    Read Excel file using CalamineWorkbook and return a chunk of rows from the CATEGORY sheet

    Args:
        filename (str): Path to Excel file
        chunk_size (int): Number of rows to read per chunk (default: 100)
        reset_position (bool): Whether to reset the global position counter (default: False)

    Returns:
        tuple: (DataFrame chunk, start_row, end_row)
    """
    global current_row_position

    if reset_position:
        current_row_position = 0

    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(filename)


            sheet_names = workbook.sheet_names
            print(f"Available sheets: {sheet_names}")

            if "CATEGORY" not in sheet_names:
                print("CATEGORY sheet not found, trying first available sheet...")
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()


            if sheet_data:
                headers = sheet_data[0]
                data = sheet_data[1:]
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, trying pandas with calamine engine...")
            try:
                df = pd.read_excel(filename, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, trying default engine...")
                df = pd.read_excel(filename, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, trying pandas with calamine engine...")
            try:
                df = pd.read_excel(filename, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, trying default engine...")
                df = pd.read_excel(filename, sheet_name="CATEGORY")

        total_rows = len(df)

        if current_row_position >= total_rows:
            print("Reached end of file")
            return pd.DataFrame(), current_row_position, total_rows

        end_row = min(current_row_position + chunk_size, total_rows)

        chunk_df = df.iloc[current_row_position:end_row].copy()

        start_row = current_row_position
        current_row_position = end_row

        print(f"Read chunk: rows {start_row + 1} to {end_row} (chunk size: {len(chunk_df)})")

        return chunk_df, start_row, end_row

    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        try:
            print("Trying fallback to default pandas engine...")
            df = pd.read_excel(filename, sheet_name="CATEGORY")

            total_rows = len(df)
            print(f"Total rows in CATEGORY sheet: {total_rows}")

            if current_row_position >= total_rows:
                print("Reached end of file")
                return pd.DataFrame(), current_row_position, total_rows

            end_row = min(current_row_position + chunk_size, total_rows)
            chunk_df = df.iloc[current_row_position:end_row].copy()

            start_row = current_row_position
            current_row_position = end_row

            print(f"Read chunk with fallback: rows {start_row + 1} to {end_row} (chunk size: {len(chunk_df)})")

            return chunk_df, start_row, end_row

        except Exception as fallback_error:
            print(f"Fallback also failed: {str(fallback_error)}")
            raise Exception(f"Failed to read Excel file CATEGORY sheet: {str(e)}")


def reset_excel_position():
    """Reset the global Excel row position counter."""
    global current_row_position
    current_row_position = 0
    print("Reset Excel position counter to 0")


def get_current_excel_position() -> int:
    """Get the current Excel row position."""
    global current_row_position
    return current_row_position


def has_more_chunks(excel_file_path: str) -> bool:
    """Check if there are more chunks available in the Excel file CATEGORY sheet."""
    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(excel_file_path)

            sheet_names = workbook.sheet_names
            if "CATEGORY" not in sheet_names:
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()

            if sheet_data:
                headers = sheet_data[0]
                data = sheet_data[1:]
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")

        total_rows = len(df)
        current_pos = get_current_excel_position()

        return current_pos < total_rows
    except Exception as e:
        print(f"Error checking for more chunks: {e}")
        return False


def get_excel_file_info(excel_file_path: str) -> dict:
    """Get information about the Excel file CATEGORY sheet."""
    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(excel_file_path)

            sheet_names = workbook.sheet_names
            print(f"Available sheets: {sheet_names}")

            if "CATEGORY" not in sheet_names:
                print("CATEGORY sheet not found, using first available sheet...")
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            print(f"Reading sheet: {sheet_name}")
            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()

            # Convert to DataFrame
            if sheet_data:
                # Use first row as headers
                headers = sheet_data[0]
                data = sheet_data[1:]  # Skip header row
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")

        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'column_names': list(df.columns),
            'current_position': get_current_excel_position(),
            'remaining_rows': len(df) - get_current_excel_position()
        }
    except Exception as e:
        print(f"Error getting Excel file info: {e}")
        return {}


def process_excel_chunk_step(step_input: StepInput) -> StepOutput:
    """Process a single chunk of Excel data (100 rows) and send to AI agent."""
    try:
        session_id = 'default'
        if hasattr(step_input, 'workflow_session_state') and step_input.workflow_session_state:
            session_id = step_input.workflow_session_state.get('session_id', 'default')

        excel_file_path = f"tmp/input_excel_{session_id}.xlsx"

        if not os.path.exists(excel_file_path):
            return StepOutput(
                content="Error: Excel file not found. Please ensure the file was created successfully."
            )

        chunk_df, start_row, end_row = read_excel_chunk_with_calamine(excel_file_path, chunk_size=100)

        if chunk_df.empty:
            return StepOutput(
                content="END_OF_FILE: No more rows to process"
            )

        print(f"Processing chunk: rows {start_row + 1} to {end_row} ({len(chunk_df)} rows)")

        keyword_column = None
        category_column = None

        for col in chunk_df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['keyword', 'term', 'phrase', 'word']):
                keyword_column = col
            elif any(cat in col_lower for cat in ['category', 'type', 'class', 'group']):
                category_column = col

        if not keyword_column:
            keyword_column = chunk_df.columns[0]

        if not category_column:
            category_column = 'category'
            chunk_df[category_column] = 'general'

        keywords_with_category = []
        for _, row in chunk_df.iterrows():
            keyword = str(row[keyword_column]).strip()
            category = str(row[category_column]).strip()
            if keyword and keyword.lower() not in ['nan', 'none', '']:
                keywords_with_category.append({
                    'keyword': keyword,
                    'category': category
                })

        if not keywords_with_category:
            return StepOutput(
                content=f"SKIP_CHUNK: No valid keywords found in rows {start_row + 1} to {end_row}"
            )

        keywords_text = f"Please analyze the following keywords from the Excel file (rows {start_row + 1} to {end_row}):\n\n"
        for item in keywords_with_category:
            keywords_text += f"- Keyword: {item['keyword']}, Category: {item['category']}\n"

        return StepOutput(
            content=keywords_text
        )

    except Exception as e:
        print(f"Error in process_excel_chunk_step: {e}")
        return StepOutput(
            content=f"Error processing Excel chunk: {str(e)}"
        )


def save_chunk_results_step(step_input: StepInput) -> StepOutput:
    """Save AI agent results to session Excel file."""
    try:
        analysis_result = step_input.previous_step_content

        if isinstance(analysis_result, str) and analysis_result.startswith("END_OF_FILE"):
            return StepOutput(
                content="Processing complete: Reached end of file"
            )

        if isinstance(analysis_result, str) and analysis_result.startswith("SKIP_CHUNK"):
            return StepOutput(
                content=f"Skipped chunk: {analysis_result}"
            )

        if hasattr(analysis_result, 'valuable_keywords'):
            valuable_keywords = analysis_result.valuable_keywords
        else:
            valuable_keywords = []

        keywords_data = []
        for keyword_eval in valuable_keywords:
            keywords_data.append({
                'keyword': keyword_eval.keyword,
                'reason': keyword_eval.reason
            })

        session_id = 'default'
        if hasattr(step_input, 'workflow_session_state') and step_input.workflow_session_state:
            session_id = step_input.workflow_session_state.get('session_id', 'default')

        session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"

        # Load existing results
        existing_keywords = []
        if os.path.exists(session_excel_file):
            try:
                existing_df = pd.read_excel(session_excel_file)
                existing_keywords = existing_df.to_dict('records')
            except:
                existing_keywords = []

        # Add new keywords
        existing_keywords.extend(keywords_data)

        # Save updated results
        if existing_keywords:
            df = pd.DataFrame(existing_keywords)
            df.to_excel(session_excel_file, index=False)

        current_pos = get_current_excel_position()
        excel_file_path = f"tmp/input_excel_{session_id}.xlsx"

        if os.path.exists(excel_file_path):
            file_info = get_excel_file_info(excel_file_path)
            total_rows = file_info.get('total_rows', 0)

            if total_rows > 0:
                progress_percentage = (current_pos / total_rows) * 100
                remaining_chunks = (file_info.get('remaining_rows', 0) + 99) // 100

                progress_message = f"Chunk processed: {len(keywords_data)} valuable keywords found. "
                progress_message += f"Total accumulated: {len(existing_keywords)} keywords. "
                progress_message += f"Progress: {progress_percentage:.1f}% ({current_pos}/{total_rows} rows). "
                progress_message += f"Remaining chunks: {remaining_chunks}. "
                progress_message += f"File: {session_excel_file}"

                return StepOutput(
                    content=progress_message
                )

        return StepOutput(
            content=f"Chunk processed: {len(keywords_data)} valuable keywords found. Total accumulated: {len(existing_keywords)} keywords. File: {session_excel_file}"
        )

    except Exception as e:
        print(f"Error in save_chunk_results_step: {e}")
        return StepOutput(
            content=f"Error saving chunk results: {str(e)}"
        )


def accumulate_analysis_results(step_input: StepInput) -> StepOutput:
    """Accumulate analysis results in a session-specific Excel file."""
    analysis_result = step_input.previous_step_content
    print(f"DEBUG: Received analysis result type: {type(analysis_result)}")
    print(f"DEBUG: Analysis result content: {analysis_result}")

    if isinstance(analysis_result, str) and (analysis_result.startswith("The input could not be processed") or
                                            analysis_result.startswith("No keywords") or
                                            analysis_result.startswith("No valid keywords") or
                                            analysis_result.startswith("Reached end of Excel file")):
        print(f"DEBUG: Received error message or end of file, not processing analysis results")
        return StepOutput(
            content=analysis_result
        )

    if hasattr(analysis_result, 'valuable_keywords'):
        valuable_keywords = analysis_result.valuable_keywords
    else:
        valuable_keywords = []

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

    # Get current position and file info for progress tracking
    current_pos = get_current_excel_position()
    excel_file_path = f"tmp/input_excel_{session_id}.xlsx"

    if os.path.exists(excel_file_path):
        file_info = get_excel_file_info(excel_file_path)
        remaining_chunks = (file_info.get('remaining_rows', 0) + 99) // 100  # Calculate remaining chunks

        progress_message = f"Successfully processed {len(keywords_data)} valuable keywords from this chunk. "
        progress_message += f"Total accumulated in session: {len(existing_keywords)} keywords. "
        progress_message += f"Current position: row {current_pos + 1}. "

        if file_info.get('total_rows', 0) > 0:
            progress_percentage = (current_pos / file_info['total_rows']) * 100
            progress_message += f"Progress: {progress_percentage:.1f}% ({current_pos}/{file_info['total_rows']} rows). "
            progress_message += f"Remaining chunks: {remaining_chunks}. "

        progress_message += f"File: {session_excel_file}"

        # Check if we've reached the end of the file
        if current_pos >= file_info.get('total_rows', 0):
            progress_message = f"END_OF_FILE: {progress_message}"

        return StepOutput(
            content=progress_message
        )
    else:
        return StepOutput(
            content=f"Successfully processed {len(keywords_data)} valuable keywords from this chunk. Total accumulated in session: {len(existing_keywords)} keywords. File: {session_excel_file}"
        )


def excel_loop_end_condition(outputs: List[StepOutput]) -> bool:
    """
    End condition for Excel processing loop.
    Returns True to break the loop (end of file), False to continue.
    """
    if not outputs:
        return False

    last_output = outputs[-1]

    if isinstance(last_output.content, str):
        if last_output.content.startswith("END_OF_FILE"):
            print("✅ Excel processing complete - reached end of file")
            return True
        elif last_output.content.startswith("Processing complete"):
            print("✅ Excel processing complete - all chunks processed")
            return True
        elif last_output.content.startswith("Reached end of Excel file"):
            print("✅ Excel processing complete - reached end of file")
            return True

    # Check if we have processed any keywords
    total_keywords = 0
    for output in outputs:
        if isinstance(output.content, str) and "valuable keywords found" in output.content:
            import re
            match = re.search(r'(\d+) valuable keywords found', output.content)
            if match:
                total_keywords += int(match.group(1))

    if total_keywords > 0:
        print(f"✅ Excel processing continuing - processed {total_keywords} keywords so far")
        return False

    print("❌ Excel processing continuing - need more chunks")
    return False


class KeywordEvaluation(BaseModel):
    keyword: str = Field(..., description="The keyword being evaluated.")
    reason: str = Field(..., description="The reason for inclusion or exclusion.")


class ExcelChunkAnalysis(BaseModel):
    audience_analysis: str = Field(..., description="Detailed statement of target audience analysis and relevant characteristics.")
    valuable_keywords: List[KeywordEvaluation] = Field(..., description="List of valuable keywords and reasons.")


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
    try:
        base64_string = step_input.message

        if not base64_string:
            return StepOutput(
                content="Error: No base64 string provided. Please provide a valid base64 encoded Excel file."
            )

        base64_string = base64_string.strip().replace('\n', '').replace('\r', '')

        if not base64_string:
            return StepOutput(
                content="Error: Empty base64 string after cleaning. Please provide a valid base64 encoded Excel file."
            )

        # Validate base64 string format
        try:
            import re
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', base64_string):
                return StepOutput(
                    content="Error: Invalid base64 string format. Please provide a properly encoded base64 string."
                )
        except Exception as e:
            return StepOutput(
                content=f"Error: Failed to validate base64 string format: {str(e)}"
            )

        # Decode base64 to bytes
        try:
            excel_bytes = base64.b64decode(base64_string)
        except Exception as e:
            return StepOutput(
                content=f"Error: Failed to decode base64 string: {str(e)}. Please ensure the base64 string is valid and complete."
            )

        if not excel_bytes:
            return StepOutput(
                content="Error: Decoded base64 string is empty. Please provide a valid Excel file."
            )

        try:
            excel_signatures = [
                b'\x50\x4B\x03\x04',
                b'\xD0\xCF\x11\xE0',
                b'\x09\x08\x10\x00',
            ]

            is_excel_file = any(excel_bytes.startswith(sig) for sig in excel_signatures)
            if not is_excel_file:
                return StepOutput(
                    content="Error: The decoded data does not appear to be a valid Excel file. Please ensure you're providing a base64 encoded Excel file (.xlsx or .xls)."
                )
        except Exception as e:
            print(f"Warning: Could not validate Excel file signature: {e}")

        # Get session ID from workflow session state or generate one
        session_id = 'default'
        if hasattr(step_input, 'workflow_session_state') and step_input.workflow_session_state:
            session_id = step_input.workflow_session_state.get('session_id', 'default')

        excel_file_path = f"tmp/input_excel_{session_id}.xlsx"

        try:
            os.makedirs("tmp", exist_ok=True)
        except Exception as e:
            return StepOutput(
                content=f"Error: Failed to create temporary directory: {str(e)}"
            )

        try:
            with open(excel_file_path, 'wb') as f:
                f.write(excel_bytes)
        except Exception as e:
            return StepOutput(
                content=f"Error: Failed to write Excel file to disk: {str(e)}"
            )

        if not os.path.exists(excel_file_path):
            return StepOutput(
                content="Error: Excel file was not created successfully. Please try again."
            )

        file_size = os.path.getsize(excel_file_path)
        if file_size == 0:
            return StepOutput(
                content="Error: Created Excel file is empty. Please check the original file."
            )

        reset_excel_position()
        print(f"DEBUG: Reset Excel position counter for new file: {excel_file_path}")

        return StepOutput(
            content=f"EXCEL_FILE_PATH:{excel_file_path}"
        )

    except Exception as e:
        return StepOutput(
            content=f"Error: Unexpected error during base64 to Excel conversion: {str(e)}"
        )




def prepare_excel_chunk_step(step_input: StepInput) -> StepOutput:
    """Prepare Excel chunk data for keyword analysis."""
    try:
        message = step_input.previous_step_content
        print(f"DEBUG: prepare_excel_chunk_step received message: {message[:100]}...")

        if not message:
            return StepOutput(
                content="Error: No message received from previous step."
            )

        if message.startswith("EXCEL_FILE_PATH:"):
            excel_file_path = message.split(":", 1)[1].strip()
            print(f"DEBUG: Extracted Excel file path: {excel_file_path}")
        else:
            print(f"DEBUG: Message does not start with EXCEL_FILE_PATH: {message[:100]}...")
            return StepOutput(
                content="Error: No Excel file path received from previous step. Expected message starting with 'EXCEL_FILE_PATH:'"
            )

        if not excel_file_path:
            return StepOutput(
                content="Error: Empty Excel file path received from previous step."
            )

        if not os.path.exists(excel_file_path):
            return StepOutput(
                content=f"Error: Excel file not found at path: {excel_file_path}"
            )

        if not os.access(excel_file_path, os.R_OK):
            return StepOutput(
                content=f"Error: Excel file is not readable: {excel_file_path}"
            )

        file_size = os.path.getsize(excel_file_path)
        if file_size == 0:
            return StepOutput(
                content=f"Error: Excel file is empty: {excel_file_path}"
            )

        session_id = 'default'

        try:
            chunk_df, start_row, end_row = read_excel_chunk_with_calamine(excel_file_path, chunk_size=100)

            if chunk_df.empty:
                return StepOutput(
                    content="Reached end of Excel file. All chunks have been processed."
                )

            print(f"DEBUG: Excel chunk loaded with {len(chunk_df)} rows and columns: {list(chunk_df.columns)}")
            print(f"DEBUG: Processing rows {start_row + 1} to {end_row}")

            keyword_column = None
            category_column = None

            # Find keyword and category columns
            for col in chunk_df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['keyword', 'term', 'phrase', 'word']):
                    keyword_column = col
                elif any(cat in col_lower for cat in ['category', 'type', 'class', 'group']):
                    category_column = col

            if not keyword_column:
                keyword_column = chunk_df.columns[0]
                print(f"DEBUG: No keyword column found, using first column: {keyword_column}")

            if not category_column:
                category_column = 'category'
                chunk_df[category_column] = 'general'
                print(f"DEBUG: No category column found, using default 'general' category")

            print(f"DEBUG: Using keyword column: '{keyword_column}', category column: '{category_column}'")

            keywords_with_category = []
            invalid_rows = []

            for idx, row in chunk_df.iterrows():
                try:
                    keyword = str(row[keyword_column]).strip()
                    category = str(row[category_column]).strip()

                    # Skip empty or invalid keywords
                    if keyword and keyword.lower() not in ['nan', 'none', '']:
                        keywords_with_category.append({
                            'keyword': keyword,
                            'category': category
                        })
                    else:
                        invalid_rows.append(idx + 1)  # +1 for 1-based row numbers
                except Exception as e:
                    print(f"DEBUG: Error processing row {idx + 1}: {e}")
                    invalid_rows.append(idx + 1)

            print(f"DEBUG: Extracted {len(keywords_with_category)} valid keywords from chunk")
            if invalid_rows:
                print(f"DEBUG: Skipped {len(invalid_rows)} invalid rows: {invalid_rows[:10]}...")

            if keywords_with_category:
                keywords_text = f"Please analyze the following keywords from the Excel file (rows {start_row + 1} to {end_row}):\n\n"
                for item in keywords_with_category:
                    keywords_text += f"- Keyword: {item['keyword']}, Category: {item['category']}\n"

                print(f"DEBUG: Sending to AI agent: {keywords_text[:200]}...")
                print(f"DEBUG: Total keywords to analyze: {len(keywords_with_category)}")
                print(f"DEBUG: First few keywords: {keywords_with_category[:3]}")

                return StepOutput(
                    content=keywords_text
                )
            else:
                print("DEBUG: No valid keywords found in Excel chunk")
                return StepOutput(
                    content=f"No valid keywords found in Excel chunk (rows {start_row + 1} to {end_row}). Please ensure the file contains valid keyword data in the expected format. Check that the keyword column contains non-empty values."
                )

        except Exception as e:
            print(f"DEBUG: Error in prepare_excel_chunk_step: {e}")
            return StepOutput(
                content=f"Error preparing Excel chunk: {str(e)}"
            )

    except Exception as e:
        print(f"DEBUG: Unexpected error in prepare_excel_chunk_step: {e}")
        return StepOutput(
            content=f"Error: Unexpected error during Excel preparation: {str(e)}"
        )


def save_session_results(step_input: StepInput) -> StepOutput:
    """Finalize the session Excel file and provide download link."""

    session_id = 'default'
    if hasattr(step_input, 'workflow_session_state') and step_input.workflow_session_state:
        session_id = step_input.workflow_session_state.get('session_id', 'default')

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




def create_loop_excel_workflow(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Workflow:
    """Create a loop-based Excel processing workflow using Agno workflow v2."""

    analysis_agent = create_excel_analysis_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )

    workflow_session_state = {}
    if session_id:
        workflow_session_state['session_id'] = session_id

    workflow = Workflow(
        name="Loop Excel Processing Workflow",
        description="Process Excel file in chunks of 100 rows using loop execution",
        storage=SqliteStorage(
            table_name="excel_loop_workflow",
            db_file="tmp/excel_loop_workflow.db",
            mode="workflow_v2",
        ),
        steps=[
            base64_to_excel_step,
            Loop(
                name="Excel Processing Loop",
                steps=[prepare_excel_chunk_step, analysis_agent, accumulate_analysis_results],
                end_condition=excel_loop_end_condition,
                max_iterations=50,
            ),
            save_session_results,
        ],
        workflow_session_state=workflow_session_state,
    )

    return workflow




async def main():
    workflow = create_loop_excel_workflow()
    await workflow.run()


if __name__ == "__main__":
    asyncio.run(main())
