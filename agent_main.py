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
# 1. Configuration & Universal Personas
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] Asterisk V2.6 [%(levelname)s] %(message)s",
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

# These cover 100% of all possible problem-solving domains
UNIVERSAL_PERSONAS = [
    "LOGIC & STRUCTURE: Deconstruct the task into a rigid, logical hierarchy. Focus on sequence and foundational rules.",
    "CREATIVE & ALTERNATIVE: Explore unconventional paths, elegant shortcuts, and innovative perspectives.",
    "CRITICAL & SKEPTICAL: Identify all potential failure points, technical debt, security risks, and logical gaps.",
    "PRAGMATIC & TECHNICAL: Focus on high-fidelity execution, specific syntax/tools, and real-world efficiency."
]

# ==========================================
# 2. Smart Rate-Limit Engine
# ==========================================
async def smart_delay(min_sec=2.0, max_sec=4.0):
    """Jitter delay to bypass Novita RPM filters."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def get_specialist_reasoning(persona_desc: str, task: str) -> str:
    """Independent reasoning without inter-agent context interference."""
    await smart_delay(1.0, 5.0) # Heavy jitter for initial fan-out
    logger.info(f"Specialist starting reasoning: {persona_desc.split(':')[0]}")
    
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nREASONING LENS: {persona_desc}\nProvide a deep-reasoned strategic report for the task."},
                {"role": "user", "content": task}
            ]
        )
        return f"### {persona_desc.split(':')[0]} REPORT\n{resp.choices[0].message.content}"
    except Exception as e:
        logger.error(f"Specialist Reasoning Failed: {e}")
        return f"### {persona_desc.split(':')[0]} ERROR: Reasoning could not be completed."

# ==========================================
# 3. Main Multi-Agent Loop
# ==========================================
async def run_agent():
    # --- PHASE 1: Parallel Fan-Out (Deep Reasoning) ---
    logger.info("Spawning Universal Council (4-Agent Fan-Out)...")
    tasks = [get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS]
    reports = await asyncio.gather(*tasks)
    
    council_context = "\n\n".join(reports)
    logger.info("Council reports synthesized. Initializing MCP...")

    # --- PHASE 2: Main Autonomous Execution ---
    mcp_params = StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"])
    
    async with stdio_client(mcp_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Auto-discover tools
            discovered = await session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in discovered.tools]

            messages = [
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nYou are the LEAD ENGINE. Use the Council's wisdom to achieve the goal.\n\nCOUNCIL REASONING:\n{council_context}"},
                {"role": "user", "content": USER_TASK}
            ]

            while True:
                await smart_delay(1.5, 3.0) 
                logger.info("Main Engine Thinking...")
                
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=available_tools
                )

                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    logger.info("Execution complete.")
                    print(f"\n[FINAL OUTPUT]:\n{choice.content}")
                    break

                # PARALLEL TOOL EXECUTION (High Performance)
                logger.info(f"Executing {len(choice.tool_calls)} tools in parallel...")
                
                async def run_tool(tc):
                    try:
                        res = await session.call_tool(tc.function.name, json.loads(tc.function.arguments))
                        return {"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": str(res.content)}
                    except Exception as err:
                        return {"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": f"Error: {err}"}

                tool_results = await asyncio.gather(*[run_tool(tc) for tc in choice.tool_calls])
                messages.extend(tool_results)

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except Exception as e:
        logger.critical(f"FATAL: {e}")
    
