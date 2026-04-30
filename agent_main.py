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
    format="[%(asctime)s] Asterisk V4.2-PROD [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk")

# Ensure PROMPT.md exists or handle missing file
try:
    with open("PROMPT.md", "r") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    BASE_SYSTEM_PROMPT = "You are a professional AI agent. Use your specialist council for deep reasoning."

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
    """Phase 1: Fan-Out."""
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
        """Phase 2: Synthesis."""
        logger.info("Lead Engine: Synthesizing Council Reports into Unified Strategy...")
        thought_prompt = [
            {"role": "assistant", "content": "I am synthesizing the Specialist Council reports into a master execution plan."},
            {"role": "user", "content": f"TASK: {task}\n\nCOUNCIL DATA:\n{council_context}\n\nINSTRUCTION: Create a final technical blueprint. Address the Skeptical agent's risks."}
        ]
        resp = await client.chat.completions.create(model=MODEL, messages=thought_prompt, temperature=0.2)
        return resp.choices[0].message.content

# ==========================================
# 3. Full-System Multi-Agent Loop
# ==========================================
async def run_agent():
    # --- PHASE 1: Quad Fan-Out ---
    logger.info("Spawning Universal Council (4-Agent Fan-Out)...")
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    council_context = "\n\n".join(reports)

    # --- PHASE 2: Synthesis ---
    internal_strategy = await ReasoningHarness.generate_internal_strategy(USER_TASK, council_context)

    # --- PHASE 3: Quad MCP Setup (Browser, GitHub, FS, Shell) ---
    mcp_configs = {
        "p": StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"]),
        "g": StdioServerParameters(
            command="npx", 
            args=["-y", "@modelcontextprotocol/server-github"],
            env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
        ),
        "f": StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd(), "/tmp"]),
        "s": StdioServerParameters(command="npx", args=["-y", "mcp-shell-server"])
    }

    async with stdio_client(mcp_configs["p"]) as (p_r, p_w), \
               stdio_client(mcp_configs["g"]) as (g_r, g_w), \
               stdio_client(mcp_configs["f"]) as (f_r, f_w), \
               stdio_client(mcp_configs["s"]) as (s_r, s_w):
        
        sessions = {
            "p": ClientSession(p_r, p_w),
            "g": ClientSession(g_r, g_w),
            "f": ClientSession(f_r, f_w),
            "s": ClientSession(s_r, s_w)
        }

        # Initialize sessions in parallel
        await asyncio.gather(*(s.initialize() for s in sessions.values()))

        # Build Global Tool Map for Dynamic Routing
        available_tools = []
        tool_to_session = {}

        for key, session in sessions.items():
            discovered = await session.list_tools()
            for t in discovered.tools:
                available_tools.append({
                    "type": "function", 
                    "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}
                })
                tool_to_session[t.name] = session

        messages = [
            {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\nYou are the LEAD ENGINE. You have full RWX access and GitHub PR capabilities."},
            {"role": "assistant", "content": f"INTERNAL STRATEGY: {internal_strategy}"},
            {"role": "user", "content": USER_TASK}
        ]

        while True:
            await asyncio.sleep(1) # Thermal/Rate-limit breathing
            response = await client.chat.completions.create(model=MODEL, messages=messages, tools=available_tools, temperature=0.7)
            choice = response.choices[0].message
            messages.append(choice)

            if not choice.tool_calls:
                print(f"\n[FINAL OUTPUT]:\n{choice.content}")
                break

            logger.info(f"Executing {len(choice.tool_calls)} parallel tool calls...")
            
            async def dispatch_tool(tc):
                t_name = tc.function.name
                t_args = json.loads(tc.function.arguments)
                target = tool_to_session.get(t_name)
                try:
                    res = await target.call_tool(t_name, t_args)
                    return {"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": str(res.content)}
                except Exception as e:
                    return {"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": f"Error: {e}"}

            results = await asyncio.gather(*(dispatch_tool(tc) for tc in choice.tool_calls))
            messages.extend(results)

if __name__ == "__main__":
    asyncio.run(run_agent())
