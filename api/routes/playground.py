from agno.playground import Playground

from agents.agno_assist import get_agno_assist
from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent
from agents.seo_keyword_agent import get_seo_keyword_agent
from agents.enhanced_csv_agent import get_enhanced_csv_agent
from workflows.csv_workflow import create_playground_csv_workflow_with_session

######################################################
## Routes for the Playground Interface
######################################################

# Get Agents to serve in the playground
web_agent = get_web_agent(debug_mode=True)
agno_assist = get_agno_assist(debug_mode=True)
finance_agent = get_finance_agent(debug_mode=True)
seo_keyword_agent = get_seo_keyword_agent(debug_mode=True)
enhanced_csv_agent = get_enhanced_csv_agent(debug_mode=True)

# Create the CSV workflow for the playground with session-based accumulation
csv_workflow = create_playground_csv_workflow_with_session(debug_mode=True)

# Create a playground instance
playground = Playground(agents=[web_agent, agno_assist, finance_agent, seo_keyword_agent, enhanced_csv_agent], workflows=[csv_workflow])

# Get the router for the playground
playground_router = playground.get_async_router()
