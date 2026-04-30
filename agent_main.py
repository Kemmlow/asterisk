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
    format="[%(asctime)s] Asterisk V4.0-PROD [%(levelname)s] %(message)s",
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

UNIVERSAL_PERSONAS = [
    "LOGIC & STRUCTURE: Rigid hierarchy. Focus on sequence and foundational rules.",
    "CREATIVE & ALTERNATIVE: Unconventional paths, elegant shortcuts, and innovation.",
    "CRITICAL & SKEPTICAL: Identify failure points, technical debt, and security risks.",
    "PRAGMATIC & TECHNICAL: High-fidelity execution, specific syntax, and efficiency."
]

# ==========================================
# 2. Reasoning & Utility Functions
# ==========================================
async def smart_delay(min_sec=1.5, max_sec=3.0):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def get_specialist_reasoning(persona_desc: str, task: str) -> str:
    """Phase 1: Independent Deep-Reasoning Specialists."""
    logger.info(f"Specialist starting reasoning: {persona_desc.split(':')[0]}")
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nLENS: {persona_desc}"},
                {"role": "user", "content": f"Analyze and strategize for this task: {task}"}
            ],
            temperature=0.4
        )
        return f"### {persona_desc.split(':')[0]} REPORT\n{resp.choices[0].message.content}"
    except Exception as e:
        return f"### {persona_desc.split(':')[0]} ERROR: {e}"

# ==========================================
# 3. V4 Reasoning Harness (The "Brain" Patch)
# ==========================================
class ReasoningHarness:
    @staticmethod
    async def generate_internal_strategy(task: str, council_context: str) -> str:
        """Internal multi-pass reasoning loop to stabilize lead engine logic."""
        logger.info("Lead Engine: Synthesizing Council Reports into Hidden Strategy...")
        
        # We use a low temperature for the 'Thought' pass to ensure technical accuracy
        thought_prompt = [
            {"role": "assistant", "content": "I have received the council reports. I must now build a unified, fault-tolerant execution plan."},
            {"role": "user", "content": f"TASK: {task}\n\nCOUNCIL DATA:\n{council_context}\n\nINSTRUCTION: Create a step-by-step technical execution strategy. Address all risks identified by the Skeptical agent."}
        ]
        
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=thought_prompt,
            temperature=0.2 # Force high-fidelity reasoning
        )
        return resp.choices[0].message.content

# ==========================================
# 4. Main Multi-Agent Loop
# ==========================================
async def run_agent():
    # --- PHASE 1: Parallel Fan-Out ---
    logger.info("Spawning Universal Council (4-Agent Fan-Out)...")
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    council_context = "\n\n".join(reports)

    # --- PHASE 2: Internal Reasoning Harness (V4 Patch) ---
    internal_strategy = await ReasoningHarness.generate_internal_strategy(USER_TASK, council_context)
    logger.info("Strategic Reasoning Complete. Initializing MCP...")

    # --- PHASE 3: Autonomous Execution ---
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

            # Inject strategy as a 'realized' assistant thought to guide the lead engine
            messages = [
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nYou are the LEAD ENGINE."},
                {"role": "assistant", "content": f"INTERNAL STRATEGY: {internal_strategy}"},
                {"role": "user", "content": USER_TASK}
            ]

            while True:
                await smart_delay()
                logger.info("Main Engine Thinking...")
                
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=available_tools,
                    temperature=0.7 # Higher temp for final output synthesis
                )

                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    logger.info("Execution complete.")
                    print(f"\n[FINAL OUTPUT]:\n{choice.content}")
                    break

                # Parallel Tool Execution
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
