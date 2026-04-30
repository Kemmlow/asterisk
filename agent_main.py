import os
import json
import asyncio
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load PROMPT.md (Your system instructions)
with open("PROMPT.md", "r") as f:
    SYSTEM_PROMPT = f.read()

USER_TASK = os.getenv("AGENT_TASK", "Execute default objective.")

client = OpenAI(
    api_key=os.getenv("NOVITA_API_KEY"),
    base_url=os.getenv("NOVITA_BASE_URL")
)

# Updated for the 2026 @playwright/mcp package
mcp_params = StdioServerParameters(
    command="npx",
    args=["-y", "@playwright/mcp@latest", "--headless"],
)

async def run_agent():
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

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TASK}
            ]

            print(f"--- Starting Task: {USER_TASK} ---")

            while True:
                response = client.chat.completions.create(
                    model=os.getenv("MODEL_NAME"),
                    messages=messages,
                    tools=available_tools
                )

                choice = response.choices[0].message
                messages.append(choice)

                if not choice.tool_calls:
                    print(f"\n[DONE]: {choice.content}")
                    break

                for tool_call in choice.tool_calls:
                    print(f"[TOOL]: {tool_call.function.name}")
                    
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
