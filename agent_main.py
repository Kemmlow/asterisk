import os
import asyncio
import logging
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool

# Production Logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] OpenHands [%(levelname)s] %(message)s")
logger = logging.getLogger("ProdAgent")

async def run_mission():
    # 1. Resolve Model Name
    raw_model = os.getenv("LLM_MODEL", "novita/ling-2.6-1t")
    model_name = "novita/ling-2.6-1t" if not raw_model or raw_model.strip() == "novita/" else raw_model
    
    logger.info(f"Initialized with model: {model_name}")

    # 2. Setup LLM
    llm = LLM(
        model=model_name,
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )

    # 3. Load System Prompt from PROMPT.md
    system_instr = "You are a senior full-stack engineer. Build the project."
    if os.path.exists("PROMPT.md"):
        with open("PROMPT.md", "r") as f:
            system_instr = f.read()
            logger.info("System Prompt loaded from PROMPT.md")

    # 4. Initialize Agent with Standard SDK Tools
    # Note: TerminalTool and FileEditorTool are the "Power Couple" of OpenHands.
    agent = Agent(
        llm=llm,
        system_prompt=system_instr,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name)
        ],
    )

    # 5. Start Autonomous Mission
    task = os.getenv("AGENT_TASK")
    # workspace is the current directory
    conversation = Conversation(agent=agent, workspace=os.getcwd())
    
    logger.info(f"🚀 Mission Start: {task[:60]}...")
    
    try:
        await conversation.send_message_async(task)
        await conversation.run_async()
        logger.info("🏁 Mission Complete.")
    except Exception as e:
        logger.error(f"Execution Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_mission())
    
