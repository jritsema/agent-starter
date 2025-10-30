import logging
from os import getenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
from strands import Agent
from strands_tools import current_time, rss
from llm_logging import LoggingHookProvider
from botocore.config import Config
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.browser import AgentCoreBrowser

# Enables Strands logging level
logging.getLogger("strands").setLevel(logging.INFO)

# Sets the logging format and streams logs to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

region = getenv("AWS_REGION")
memory_id = getenv("MEMORY_ID")
logging.warning(f"MEMORY_ID = {memory_id}")
code_interpreter_id = getenv("CODE_INTERPRETER_ID")
logging.warning(f"CODE_INTERPRETER_ID = {code_interpreter_id}")
browser_id = getenv("BROWSER_ID")
logging.warning(f"BROWSER_ID = {browser_id}")

retry_config = Config(
    region_name=region,
    retries={
        "max_attempts": 10,  # Increase from default 4 to 10
        "mode": "adaptive"
    }
)

memory_client = MemoryClient(region_name=region)


app = FastAPI(title="My AI Agent", version="0.1.0")

system_prompt = """
Hacker News - https://hnrss.org/frontpage
• Constantly updating tech discussions
• Great for summarization and trend analysis
• Rich comment data and voting scores

NASA Breaking News - https://www.nasa.gov/rss/dyn/breaking_news.rss
• Exciting space discoveries and missions
• Visual content opportunities
• Perfect for "What's new in space?" queries

TechCrunch - https://techcrunch.com/feed/
• Startup funding announcements
• Product launches and acquisitions
• Great for business intelligence demos

Atlas Obscura - https://www.atlasobscura.com/feeds/latest
• Unique places and stories
• Perfect for travel recommendations
• Engaging, unusual content
"""

# we have a single stateful agent per container session id
strands_agent = None


class InvocationResponse(BaseModel):
    message: Dict[str, Any]


SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"


@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: Request):
    global strands_agent
    result = None

    req = await request.json()
    invoke_input = req["input"]
    prompt = invoke_input["prompt"]
    user_id = invoke_input["user_id"]
    session_id = request.headers.get(SESSION_HEADER)
    logging.warning(
        f"initializing with session: {session_id} and user: {user_id}")

    if strands_agent is None:

        # initialize a new agent once for each runtime container session.
        # conversation state will be persisted in both local memory
        # and remote agentcore memory. for resumed sessions,
        # AgentCoreMemorySessionManager will rehydrate state from agentcore memory

        logging.info("initializing session manager")
        config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=session_id,
            actor_id=user_id,
            retrieval_config={
                "/preferences/{actorId}": RetrievalConfig(
                    top_k=5,
                    relevance_score=0.7
                ),
                "/facts/{actorId}": RetrievalConfig(
                    top_k=10,
                    relevance_score=0.3
                ),
            },
        )

        session_manager = AgentCoreMemorySessionManager(
            boto_client_config=retry_config,
            agentcore_memory_config=config
        )

        code_interpreter_tool = AgentCoreCodeInterpreter(
            region=region,
            identifier=code_interpreter_id,
        )

        browser_tool = AgentCoreBrowser(
            region=region,
            identifier=browser_id,
        )

        logging.info("agent initializing")
        try:
            strands_agent = Agent(
                model="us.anthropic.claude-sonnet-4-20250514-v1:0",
                system_prompt=system_prompt,
                tools=[current_time,
                       rss,
                       code_interpreter_tool.code_interpreter,
                       browser_tool.browser,
                       ],
                hooks=[LoggingHookProvider()],
                session_manager=session_manager,
            )
        except Exception as e:
            logging.error(f"Agent initialization failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Agent initialization failed: {str(e)}")

    try:
        # invoke the agent
        logging.info("invoking agent")

        async def generate():
            async for event in strands_agent.stream_async(prompt):
                # Only stream text chunks to the client
                if "data" in event:
                    yield f"data: {event['data']}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    except Exception as e:
        logging.error(f"Agent processing failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Agent processing failed: {str(e)}")


class NoHealthCheckFilter(logging.Filter):
    """disable health check logging"""

    def filter(self, record):
        return "GET /ping" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(NoHealthCheckFilter())


@app.get("/ping")
async def ping():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
