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
# 1. Configuration & Engine Setup
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] Asterisk V4.2.1-FIX [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk")

try:
    with open("PROMPT.md", "r") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    BASE_SYSTEM_PROMPT = "You are Asterisk, a high-fidelity autonomous agent."

USER_TASK = os.getenv("AGENT_TASK", "Execute default objective.")
MODEL = os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t")

client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

UNIVERSAL_PERSONAS = [
    "LOGIC & STRUCTURE: Rigid hierarchy. Focus on sequence and foundational rules.",
    "CREATIVE & ALTERNATIVE: Unconventional paths and elegant shortcuts.",
    "CRITICAL & SKEPTICAL: Identify failure points and technical debt.",
    "PRAGMATIC & TECHNICAL: High-fidelity execution and specific syntax."
]

# ==========================================
# 2. Reasoning & Synthesis Functions
# ==========================================
async def get_specialist_reasoning(persona_desc: str, task: str) -> str:
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

class ReasoningHarness:
    @staticmethod
    async def generate_internal_strategy(task: str, council_context: str) -> str:
        logger.info("Lead Engine: Synthesizing Council Reports...")
        thought_prompt = [
            {"role": "assistant", "content": "I am synthesizing the Specialist Council reports into a master plan."},
            {"role": "user", "content": f"TASK: {task}\n\nCOUNCIL DATA:\n{council_context}\n\nINSTRUCTION: Create a final technical blueprint."}
        ]
        resp = await client.chat.completions.create(model=MODEL, messages=thought_prompt, temperature=0.2)
        return resp.choices[0].message.content

# ==========================================
# 3. Execution Loop (Multi-Server Bridge)
# ==========================================
async def run_agent():
    # --- PHASE 1 & 2: Quad-Council Fan-Out ---
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    internal_strategy = await ReasoningHarness.generate_internal_strategy(USER_TASK, "\n\n".join(reports))

    # --- PHASE 3: Path-Hardened MCP Setup ---
    # We use direct bin paths to avoid the 'npx' update check deadlock
    mcp_configs = {
        "p": StdioServerParameters(command="playwright-mcp", args=["--headless"]),
        "g": StdioServerParameters(
            command="mcp-server-github", 
            env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
        ),
        "f": StdioServerParameters(command="mcp-server-filesystem", args=[os.getcwd(), "/tmp"]),
        "s": StdioServerParameters(command="mcp-shell-server")
    }

    async with stdio_client(mcp_configs["p"]) as (p_r, p_w), \
               stdio_client(mcp_configs["g"]) as (g_r, g_w), \
               stdio_client(mcp_configs["f"]) as (f_r, f_w), \
               stdio_client(mcp_configs["s"]) as (s_r, s_w):
        
        sessions = {"p": ClientSession(p_r, p_w), "g": ClientSession(g_r, g_w), "f": ClientSession(f_r, f_w), "s": ClientSession(s_r, s_w)}

        # Parallel Init with 30s Safety Timeout
        try:
            await asyncio.wait_for(asyncio.gather(*(s.initialize() for s in sessions.values())), timeout=30)
        except asyncio.TimeoutError:
            logger.critical("Handshake Timeout: Stdio pipe deadlock.")
            return

        # Map Tools to Sessions
        available_tools = []
        tool_to_session = {}
        for key, sess in sessions.items():
            discovered = await sess.list_tools()
            for t in discovered.tools:
                available_tools.append({
                    "type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}
                })
                tool_to_session[t.name] = sess

        messages = [
            {"role": "system", "content": f"{BASE_SYSTEM_PROMPT}\nYou are the LEAD ENGINE."},
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

            logger.info(f"Executing {len(choice.tool_calls)} tool calls...")
            tool_results = []
            for tc in choice.tool_calls:
                t_name = tc.function.name
                t_args = json.loads(tc.function.arguments)
                target_sess = tool_to_session.get(t_name)
                try:
                    res = await target_sess.call_tool(t_name, t_args)
                    tool_results.append({"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": str(res.content)})
                except Exception as e:
                    tool_results.append({"role": "tool", "tool_call_id": tc.id, "name": t_name, "content": f"Error: {e}"})

            messages.extend(tool_results)

if __name__ == "__main__":
    asyncio.run(run_agent())
