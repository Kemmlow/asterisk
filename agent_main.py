import os
import asyncio
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.mcp import McpTool

async def run_mission():
    # 1. Setup LLM
    llm = LLM(
        model=os.getenv("LLM_MODEL"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )

    # 2. Configure MCP Tools (Maker's Choice)
    # We use stdio to communicate with the globally installed npm packages
    mcp_tools = [
        McpTool(name="browser", command="npx", args=["-y", "@playwright/mcp@latest", "--headless"]),
        McpTool(name="github", command="npx", args=["-y", "@modelcontextprotocol/server-github"], 
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}),
        McpTool(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()])
    ]

    # 3. Initialize Agent with Built-in + MCP Tools
    agent = Agent(
        llm=llm,
        system_prompt=open("PROMPT.md").read() if os.path.exists("PROMPT.md") else "Handle task.",
        tools=[
            Tool(name=TerminalTool.name),    # The raw shell
            Tool(name=FileEditorTool.name),  # Specialized for high-precision edits
            *mcp_tools                      # Your 4 cherry-picked MCPs
        ],
    )

    # 4. Start the Managed Conversation
    task = os.getenv("AGENT_TASK", "Execute audit.")
    conversation = Conversation(agent=agent, workspace=os.getcwd())
    
    print(f"🚀 Launching OpenHands with MCP integration...")
    await conversation.send_message_async(task)
    await conversation.run_async()
    print("🏁 Mission Complete.")

if __name__ == "__main__":
    asyncio.run(run_mission())