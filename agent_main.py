import os
import json
import asyncio
import logging
import random
from typing import List, Dict, Any
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==========================================
# 1. Setup & Specialist Personas
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] Asterisk Core [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk")

with open("PROMPT.md", "r") as f:
    BASE_SYSTEM_PROMPT = f.read()

USER_TASK = os.getenv("AGENT_TASK", "Execute default objective.")
MODEL = os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t")

client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

# Independent specialist logic
PERSONAS = [
    "Focus on high-speed efficiency and code optimization.",
    "Focus on extreme security, error handling, and stability.",
    "Focus on innovative UX and aesthetic brilliance.",
    "Think like a skeptic: find flaws and edge-cases in the logic."
]

# ==========================================
# 2. Smart Rate-Limit Helpers
# ==========================================
async def smart_delay():
    """Adds jitter to bypass RPM rate-limiters."""
    delay = random.uniform(2.0, 4.0)
    await asyncio.sleep(delay)

async def get_specialist_view(persona_mod: str, task: str) -> str:
    """Individual agent reasoning without seeing other agents' thoughts."""
    await smart_delay() # Staggered start
    logger.info(f"Specialist starting reasoning: {persona_mod[:30]}...")
    
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nConstraint: {persona_mod}"},
            {"role": "user", "content": f"Think deeply and provide a technical strategy for: {task}"}
        ]
    )
    return resp.choices[0].message.content

# ==========================================
# 3. Main Multi-Agent Loop (V1 Base)
# ==========================================
async def run_agent():
    # --- PHASE 1: Parallel Specialist Reasoning ---
    logger.info("Spawning Parallel Council (4 Agents)...")
    tasks = [get_specialist_view(p, USER_TASK) for p in PERSONAS]
    specialist_reports = await asyncio.gather(*tasks)
    
    council_context = "\n\n".join([f"--- Report {i+1} ---\n{r}" for i, r in enumerate(specialist_reports)])
    logger.info("Council reports gathered. Initializing Playwright...")

    # --- PHASE 2: Main Autonomous Execution (V1 Loop) ---
    mcp_params = StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"])
    
    async with stdio_client(mcp_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            discovered = await session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in discovered.tools]

            # The Lead Agent receives all the council's wisdom at once
            messages = [
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nYou are the LEAD AGENT. Review these 4 specialist strategies and execute the best plan using your tools.\n\nCOUNCIL STRATEGIES:\n{council_context}"},
                {"role": "user", "content": USER_TASK}
            ]

            iteration = 0
            while True:
                iteration += 1
                await smart_delay() # Prevent loop-based rate limiting
                
                logger.info(f"Thinking... (Loop {iteration})")
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=available_tools
                )

                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    logger.info("Task concluded.")
                    print(f"\n[FINAL RESPONSE]:\n{choice.content}")
                    break

                # Support for Parallel Tool Exec (from the previous working patch)
                logger.info(f"Executing {len(choice.tool_calls)} concurrent tool actions...")
                tool_tasks = []
                for tool_call in choice.tool_calls:
                    async def call_t(tc):
                        res = await session.call_tool(tc.function.name, json.loads(tc.function.arguments))
                        return {"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": str(res.content)}
                    tool_tasks.append(call_t(tool_call))
                
                results = await asyncio.gather(*tool_tasks)
                messages.extend(results)

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except Exception as e:
        logger.critical(f"Fatal Engine Failure: {e}")
        
