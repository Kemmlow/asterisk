import os
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool

# 1. Load System Prompt from PROMPT.md
def get_custom_instructions():
    if os.path.exists("PROMPT.md"):
        with open("PROMPT.md", "r") as f:
            return f.read()
    return "Execute the task autonomously."

# 2. Configure the LLM (Novita/Ling/DeepSeek)
llm = LLM(
    model=os.getenv("LLM_MODEL"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)

# 3. Initialize Agent with Prod Tools
# Note: OpenHands SDK handles the MCP-like logic for these tools internally
agent = Agent(
    llm=llm,
    system_prompt=get_custom_instructions(),
    tools=[
        Tool(name=TerminalTool.name),    # For shell commands
        Tool(name=FileEditorTool.name),  # For fixing code
        Tool(name=TaskTrackerTool.name), # For keeping the state
    ],
)

# 4. Run the Conversation
def main():
    task = os.getenv("AGENT_TASK", "Audit the repository.")
    workspace_path = os.getcwd()
    
    print(f"🚀 Mission Start: {task}")
    
    conversation = Conversation(agent=agent, workspace=workspace_path)
    conversation.send_message(task)
    
    # This runs the autonomous loop (Action-Observation-Reflection)
    # It replaces your manual while-loop and handles "stuck" states
    conversation.run()
    
    print("🏁 Mission Complete.")

if __name__ == "__main__":
    main()