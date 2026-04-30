import os
import json
import asyncio
import logging
from contextlib import AsyncExitStack
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

USER_TASK = os.getenv("AGENT_TASK", "List the files in the current directory and check git status.")
MODEL = os.getenv("MODEL_NAME", "inclusionai/ling-2.6-1t")

client = AsyncOpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
)

UNIVERSAL_PERSONAS = [
    "LOGIC: Senior Architect. Focus on Big O complexity and memory management.",
    "CREATIVE: Polyglot Developer. Focus on design patterns and clean abstractions.",
    "SKEPTICAL: Security/QA Lead. Focus on race conditions and edge cases.",
    "PRAGMATIC: DevOps/SRE. Focus on build stability and CI/CD compatibility."
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
# 3. Execution & MCP Bridge (The Fix)
# ==========================================
async def run_agent():
    # Phase 1 & 2: Planning
    reports = await asyncio.gather(*[get_specialist_reasoning(p, USER_TASK) for p in UNIVERSAL_PERSONAS])
    blueprint = await ReasoningHarness.synthesize(USER_TASK, "\n\n".join(reports))

    logger.info("Starting up MCP Bridge...")
    
    # Environment Setup
    env = os.environ.copy()
    if "GITHUB_TOKEN" in env and "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = env["GITHUB_TOKEN"]

    # Absolute path prevents ENOENT crashes on the filesystem server
    current_dir = os.path.abspath(".")
    
    # The 4 Cherry-Picked Maker Tools
    mcp_configs = {
        "browser": StdioServerParameters(command="npx", args=["-y", "@playwright/mcp@latest", "--headless"], env=env),
        "git": StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-github"], env=env),
        "fs": StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", current_dir], env=env),
        "shell": StdioServerParameters(command="npx", args=["-y", "mcp-shell-server"], env=env)
    }

    # AsyncExitStack prevents deadlocks by initializing sequentially
    async with AsyncExitStack() as stack:
        tool_map = {}
        available_tools = []

        for name, config in mcp_configs.items():
            logger.info(f"Initializing {name} server...")
            try:
                stdio_transport = await stack.enter_async_context(stdio_client(config))
                read_stream, write_stream = stdio_transport
                
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()
                
                tools_response = await session.list_tools()
                for t in tools_response.tools:
                    tool_map[t.name] = session
                    available_tools.append({
                        "type": "function", 
                        "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}
                    })
                logger.info(f"✅ [{name}] online with {len(tools_response.tools)} tools.")
            except Exception as e:
                logger.error(f"❌ Failed to start [{name}]: {e}")

        if not available_tools:
            logger.critical("No tools loaded! Exiting to prevent infinite loop.")
            return

        messages = [
            {"role": "system", "content": "You are the Lead Production Engine. Execute the blueprint using the provided tools. Output brief status updates."},
            {"role": "assistant", "content": f"BLUEPRINT: {blueprint}"},
            {"role": "user", "content": USER_TASK}
        ]

        logger.info("Entering Main Execution Loop...")
        while True:
            response = await client.chat.completions.create(model=MODEL, messages=messages, tools=available_tools, temperature=0.5)
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                print(f"\n[FINAL DEPLOYMENT OUTPUT]:\n{msg.content}")
                break

            for tc in msg.tool_calls:
                logger.info(f"🔧 Tool Call: {tc.function.name}")
                target = tool_map.get(tc.function.name)
                
                if not target:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": "Error: Tool not found."})
                    continue

                try:
                    args = json.loads(tc.function.arguments)
                    res = await target.call_tool(tc.function.name, args)
                    
                    # Robust parsing of MCP text content blocks
                    result_text = "\n".join([c.text for c in res.content if hasattr(c, 'text')])
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": result_text or "Success"})
                except Exception as e:
                    logger.error(f"Execution Error in {tc.function.name}: {e}")
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": f"Error: {e}"})

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\nAgent stopped.")