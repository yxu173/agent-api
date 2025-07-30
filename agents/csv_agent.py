from typing import List, Optional
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from textwrap import dedent
from agno.storage.agent.postgres import PostgresAgentStorage
from db.session import db_url
import pandas as pd
from io import StringIO


class KeywordEvaluation(BaseModel):
    keyword: str = Field(..., description="The keyword being evaluated.")
    reason: str = Field(..., description="The reason for inclusion or exclusion.")


class SEOKeywordAnalysis(BaseModel):
    audience_analysis: str = Field(...,
                                   description="Detailed statement of target audience analysis and relevant characteristics.")
    valuable_keywords: List[KeywordEvaluation] = Field(..., description="List of valuable keywords and reasons.")


class CSVProcessingResult(BaseModel):
    valuable_keywords_found: int = Field(..., description="The total number of valuable keywords found.")
    output_path: str = Field(..., description="The path to the output CSV file.")


def get_csv_agent(
    model_id: str = "o4-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    return Agent(
        name="CSV Keyword Agent",
        agent_id="csv_agent",
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
            Also “Avoid over‐elaboration or speculative reasoning: focus only on the given criteria without philosophical digressions.”
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
        add_state_in_messages=True,
        storage=PostgresAgentStorage(table_name="csv_agent_sessions", db_url=db_url),
        add_history_to_messages=True,
        num_history_runs=3,
        read_chat_history=True,
        response_model=SEOKeywordAnalysis,
        use_json_mode=True,
        debug_mode=debug_mode,
        stream=False,
    )


async def process_csv_file(agent: Agent, file_path: str, output_path: str, keyword_column: str = 'keyword',
                           category_column: str = 'category') -> CSVProcessingResult:
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    if keyword_column not in df.columns:
        raise ValueError(f"Keyword column '{keyword_column}' not found in the CSV file.")
    if category_column not in df.columns:
        raise ValueError(f"Category column '{category_column}' not found in the CSV file.")

    total_rows = len(df)
    chunk_size = 100
    all_valuable_keywords = []

    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk_df = df.iloc[start:end]

        keywords_with_category = chunk_df[[keyword_column, category_column]].to_dict('records')

        message = "Please analyze the following keywords:\n"
        for item in keywords_with_category:
            message += f"- Keyword: {item[keyword_column]}, Category: {item[category_column]}\n"

        run_result = await agent.arun(message, stream=False)

        if isinstance(run_result.content, SEOKeywordAnalysis):
            analysis_result = run_result.content
            all_valuable_keywords.extend(analysis_result.valuable_keywords)
        else:
            print(f"Warning: Received unexpected response type from agent for chunk {start}-{end}. Skipping.")
            continue

    if all_valuable_keywords:
        output_df = pd.DataFrame([k.dict() for k in all_valuable_keywords])
        output_df.to_csv(output_path, index=False)
    else:
        pd.DataFrame(columns=['keyword', 'reason']).to_csv(output_path, index=False)

    return CSVProcessingResult(
        valuable_keywords_found=len(all_valuable_keywords),
        output_path=output_path
    )
