import os
import json
import asyncio
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. Load your PROMPT.md (Untouched)
with open("PROMPT.md", "r") as f:
    SYSTEM_INSTRUCTIONS = f.read()

# 2. Get the task from the Workflow input
USER_TASK = os.getenv("AGENT_TASK", "No task provided.")

client = OpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL")
)

mcp_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-playwright"],
)

async def run_agent():
    async with stdio_client(mcp_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Auto-map Playwright tools to OpenAI function format
            discovered = await session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in discovered.tools]

            # The system prompt is your PROMPT.md
            messages = [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": USER_TASK}
            ]

            while True:
                response = client.chat.completions.create(
                    model=os.getenv("MODEL_NAME"),
                    messages=messages,
                    tools=available_tools
                )

                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    print(f"\n[FINAL RESPONSE]:\n{choice.content}")
                    break

                for tool_call in choice.tool_calls:
                    print(f"[EXECUTING]: {tool_call.function.name}")
                    
                    result = await session.call_tool(
                        tool_call.function.name, 
                        json.loads(tool_call.function.arguments)
                    )
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": str(result.content)
                    })

if __name__ == "__main__":
    asyncio.run(run_agent())
    
