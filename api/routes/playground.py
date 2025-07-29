from agno.playground import Playground

from agents.agno_assist import get_agno_assist
from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent
from agents.seo_keyword_agent import get_seo_keyword_agent

######################################################
## Routes for the Playground Interface
######################################################

# Get Agents to serve in the playground
web_agent = get_web_agent(debug_mode=True)
agno_assist = get_agno_assist(debug_mode=True)
finance_agent = get_finance_agent(debug_mode=True)
seo_keyword_agent = get_seo_keyword_agent(debug_mode=True)

# Create a playground instance
playground = Playground(agents=[web_agent, agno_assist, finance_agent, seo_keyword_agent])

# Get the router for the playground
playground_router = playground.get_async_router()
