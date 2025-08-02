from agno.playground import Playground

from agents.agno_assist import get_agno_assist
from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent
from workflows.excel_workflow import create_loop_excel_workflow

######################################################
## Routes for the Playground Interface
######################################################

# Get Agents to serve in the playground
web_agent = get_web_agent(debug_mode=True)
agno_assist = get_agno_assist(debug_mode=True)
finance_agent = get_finance_agent(debug_mode=True)

# Create the Excel workflow for the playground
excel_workflow = create_loop_excel_workflow(debug_mode=True)

# Create a playground instance
playground = Playground(agents=[web_agent, agno_assist, finance_agent], workflows=[excel_workflow])

# Get the router for the playground
playground_router = playground.get_async_router()
