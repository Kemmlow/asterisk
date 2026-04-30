import os
import json
import asyncio
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ==========================================
# 1. Production Logging & Config
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] Asterisk V4.2.3-ULTRAPROD [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Asterisk")

USER_TASK = os.getenv("AGENT_TASK", "Refactor the codebase for performance.")
MODEL = os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t")

client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

UNIVERSAL_PERSONAS = [
    "LOGIC: Senior Architect. Focus on Big O complexity, type safety, and memory management.",
    "CREATIVE: Polyglot Developer. Focus on design patterns (Functional, OOP) and clean abstractions.",
    "SKEPTICAL: Security/QA Lead. Focus on race conditions, edge cases, and technical debt.",
    "PRAGMATIC: DevOps/SRE. Focus on build stability, CI/CD compatibility, and local execution."
]

# ==========================================
# 2. Reasoning & Synthesis
# ==========================================
async def get_specialist_reasoning(persona: str, task: str) -> str:
    logger.info(f"Council Member starting: {persona.split(':')[0]}")
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": f"LENS: {persona}"},
                  {"role": "user", "content": f"Develop a heavy-duty strategy for: {task}"}],
        temperature=0.3
    )
    return f"### {persona.split(':')[0]} ANALYSIS\n{resp.choices[0].message.content}"

class ReasoningHarness:
    @staticmethod
    async def synthesize(task: str, context: str) -> str:
        logger.info("Lead Engine: Synthesizing Council Reports...")
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are the Lead Technical Architect. Synthesize reports into a production blueprint."},
                      {"role": "user", "content": f"TASK: {task}\n\nCOUNCIL REPORTS:\n{context}"}],
            temperature=0.2
        )
        return resp.choices[0].message.content

# ==========================================
# 3. Execution & MCP Bridge
# ==========================================
async def run_agent():
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    blueprint = await ReasoningHarness.synthesize(USER_TASK, "\n\n".join(reports))

    # Path fix: Ensure current working directory is explicitly passed
    cwd = os.getcwd()

    mcp_configs = {
        "browser": StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"], env=os.environ),
        "git": StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-github"], 
                                    env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}),
        "fs": StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", cwd], env=os.environ),
        "shell": StdioServerParameters(command="npx", args=["-y", "mcp-shell-server"], env=os.environ)
    }

    async with stdio_client(mcp_configs["browser"]) as (b_r, b_w), \
               stdio_client(mcp_configs["git"]) as (g_r, g_w), \
               stdio_client(mcp_configs["fs"]) as (f_r, f_w), \
               stdio_client(mcp_configs["shell"]) as (s_r, s_w):
        
        sessions = [ClientSession(b_r, b_w), ClientSession(g_r, g_w), ClientSession(f_r, f_w), ClientSession(s_r, s_w)]
        await asyncio.gather(*(s.initialize() for s in sessions))

        tool_map = {}
        available_tools = []
        for sess in sessions:
            mcp_tools = await sess.list_tools()
            for t in mcp_tools.tools:
                tool_map[t.name] = sess
                available_tools.append({"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}})

        messages = [
            {"role": "system", "content": "You are the Lead Production Engine. Execute the blueprint. Use local shell for testing."},
            {"role": "assistant", "content": f"BLUEPRINT: {blueprint}"},
            {"role": "user", "content": USER_TASK}
        ]

        while True:
            response = await client.chat.completions.create(model=MODEL, messages=messages, tools=available_tools, temperature=0.5)
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                print(f"\n[FINAL DEPLOYMENT OUTPUT]:\n{msg.content}")
                break

            for tc in msg.tool_calls:
                logger.info(f"Tool Call: {tc.function.name}")
                target = tool_map.get(tc.function.name)
                try:
                    res = await target.call_tool(tc.function.name, json.loads(tc.function.arguments))
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": str(res.content)})
                except Exception as e:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": f"Error: {e}"})

if __name__ == "__main__":
    async asyncio.run(run_agent())
