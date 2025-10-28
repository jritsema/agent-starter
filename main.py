import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
from strands import Agent
from strands_tools import current_time, rss
from log import JSONFormatter

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.getLogger("strands.models.bedrock").handlers = []
llm_handler = logging.StreamHandler()
llm_handler.setFormatter(JSONFormatter(
    "%(levelname)s | %(name)s | %(message)s"))
logging.getLogger("strands.models.bedrock").addHandler(llm_handler)

# Sets the logging format and streams logs to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

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


@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: Request):
    global strands_agent
    result = None

    req = await request.json()
    invoke_input = req["input"]
    prompt = invoke_input["prompt"]

    if strands_agent is None:

        logging.info("agent initializing")
        try:
            strands_agent = Agent(
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                system_prompt=system_prompt,
                tools=[current_time, rss],
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
