import os
import json
import asyncio
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==========================================
# 1. Configuration & Logging
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] Asterisk Core [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk.Kemmlow")

# Load System Instructions (PROMPT.md)
PROMPT_FILE = "PROMPT.md"
try:
    with open(PROMPT_FILE, "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.warning(f"{PROMPT_FILE} not found. Running with empty system prompt.")
    SYSTEM_PROMPT = "You are a helpful autonomous agent."

USER_TASK = os.getenv("AGENT_TASK", "Execute default objective.")

# API Configuration
client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

# MCP Server Configuration (Playwright)
mcp_params = StdioServerParameters(
    command="npx",
    args=["-y", "@playwright/mcp@latest", "--headless"],
)

# ==========================================
# 2. Parallel-Capable Tool Wrapper
# ==========================================

async def execute_tool(session: ClientSession, tool_call: Any) -> Dict[str, Any]:
    """
    Executes a single tool call asynchronously. 
    Catches errors locally to prevent a single bad scrape from crashing the agent.
    """
    tool_name = tool_call.function.name
    logger.info(f"Triggering tool: {tool_name}")
    
    try:
        arguments = json.loads(tool_call.function.arguments)
        result = await session.call_tool(tool_name, arguments)
        
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": str(result.content)
        }
        
    except Exception as e:
        logger.error(f"Execution failed for {tool_name}: {str(e)}")
        # Feed error back to the model for self-correction
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": f"Error: {str(e)}"
        }

# ==========================================
# 3. Main Autonomous Loop
# ==========================================

async def run_agent() -> None:
    logger.info("Initializing Playwright MCP...")
    
    async with stdio_client(mcp_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Map discovered tools to OpenAI/Novita format
            discovered = await session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in discovered.tools]
            
            logger.info(f"System ready with {len(available_tools)} tools.")

            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TASK}
            ]

            logger.info(f"Task Started: {USER_TASK}")

            iteration = 0
            while True:
                iteration += 1
                logger.info(f"Thinking... (Loop {iteration})")
                
                try:
                    response = await client.chat.completions.create(
                        model=os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t"),
                        messages=messages,
                        tools=available_tools
                    )
                except Exception as e:
                    logger.critical(f"API Failure: {str(e)}")
                    break

                choice = response.choices[0].message
                messages.append(choice)

                # If no tool calls are present, the agent has finished its work
                if not choice.tool_calls:
                    logger.info("Task concluded successfully.")
                    print(f"\n[FINAL RESPONSE]:\n{choice.content}")
                    break

                # PARALLEL EXECUTION: Launch all requested tool calls at once
                logger.info(f"Processing {len(choice.tool_calls)} concurrent actions...")
                tasks = [execute_tool(session, tool_call) for tool_call in choice.tool_calls]
                tool_results = await asyncio.gather(*tasks)
                
                # Append all results to context for the next iteration
                messages.extend(tool_results)

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.critical(f"Unrecoverable error: {str(e)}")
        
