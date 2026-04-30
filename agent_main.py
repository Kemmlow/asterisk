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
    format="[%(asctime)s] Asterisk V4.1-QUAD [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk")

with open("PROMPT.md", "r") as f:
    BASE_SYSTEM_PROMPT = f.read()

USER_TASK = os.getenv("AGENT_TASK", "Refactor agent_main.py and create a PR.")
MODEL = os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t")

client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

UNIVERSAL_PERSONAS = [
    "LOGIC & STRUCTURE: Rigid hierarchy. Focus on sequence and foundational rules.",
    "CREATIVE & ALTERNATIVE: Unconventional paths and elegant shortcuts.",
    "CRITICAL & SKEPTICAL: Identify failure points, technical debt, and security risks.",
    "PRAGMATIC & TECHNICAL: High-fidelity execution, specific syntax, and efficiency."
]

# ==========================================
# 2. Quad-Reasoning & Synthesis
# ==========================================
async def get_specialist_reasoning(persona_desc: str, task: str) -> str:
    """Original Fan-Out: Each specialist provides their deep-reasoned report."""
    logger.info(f"Specialist starting reasoning: {persona_desc.split(':')[0]}")
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\n\nLENS: {persona_desc}"},
                {"role": "user", "content": f"Strategize for this task: {task}"}
            ],
            temperature=0.4
        )
        return f"### {persona_desc.split(':')[0]} REPORT\n{resp.choices[0].message.content}"
    except Exception as e:
        return f"### {persona_desc.split(':')[0]} ERROR: {e}"

class ReasoningHarness:
    @staticmethod
    async def generate_internal_strategy(task: str, council_context: str) -> str:
        """Squeezed Synthesis: Combines reports into a hardened execution plan."""
        logger.info("Lead Engine: Synthesizing Council Reports...")
        thought_prompt = [
            {"role": "assistant", "content": "I am synthesizing the Specialist Council reports into a master execution plan."},
            {"role": "user", "content": f"TASK: {task}\n\nCOUNCIL DATA:\n{council_context}\n\nINSTRUCTION: Create a final technical blueprint. Address the Skeptical agent's risks."}
        ]
        resp = await client.chat.completions.create(model=MODEL, messages=thought_prompt, temperature=0.2)
        return resp.choices[0].message.content

# ==========================================
# 3. Main Multi-Agent Loop (Dual MCP Support)
# ==========================================
async def run_agent():
    # --- PHASE 1: Quad Fan-Out ---
    logger.info("Spawning Universal Council (4-Agent Fan-Out)...")
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    council_context = "\n\n".join(reports)

    # --- PHASE 2: Synthesis ---
    internal_strategy = await ReasoningHarness.generate_internal_strategy(USER_TASK, council_context)

    # --- PHASE 3: Dual MCP Execution (Playwright + GitHub) ---
    playwright_mcp = StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"])
    github_mcp = StdioServerParameters(
        command="npx", 
        args=["-y", "@modelcontextprotocol/server-github"],
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
    )

    async with stdio_client(playwright_mcp) as (p_r, p_w), stdio_client(github_mcp) as (g_r, g_w):
        async with ClientSession(p_r, p_w) as p_session, ClientSession(g_r, g_w) as g_session:
            await p_session.initialize()
            await g_session.initialize()

            # Merge toolsets
            p_tools = await p_session.list_tools()
            g_tools = await g_session.list_tools()
            available_tools = [{
                "type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}
            } for t in p_tools.tools + g_tools.tools]

            messages = [
                {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\nYou are the LEAD ENGINE. Use the Council's wisdom."},
                {"role": "assistant", "content": f"INTERNAL STRATEGY: {internal_strategy}"},
                {"role": "user", "content": USER_TASK}
            ]

            while True:
                response = await client.chat.completions.create(model=MODEL, messages=messages, tools=available_tools, temperature=0.7)
                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    print(f"\n[FINAL OUTPUT]:\n{choice.content}")
                    break

                # Dispatcher logic for PR and Browser tools
                tool_results = []
                for tc in choice.tool_calls:
                    t_name = tc.function.name
                    t_args = json.loads(tc.function.arguments)
                    
                    # Routing: GitHub tools go to g_session, others to p_session
                    target = g_session if any(k in t_name for k in ["github", "pull", "repo", "create"]) else p_session
                    
                    try:
                        res = await target.call_tool(t_name, t_args)
                        tool_results.append({"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": str(res.content)})
                    except Exception as e:
                        tool_results.append({"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": f"Error: {e}"})

                messages.extend(tool_results)

if __name__ == "__main__":
    asyncio.run(run_agent())
