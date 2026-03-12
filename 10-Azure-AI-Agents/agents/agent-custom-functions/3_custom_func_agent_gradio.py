import os
from dotenv import load_dotenv
from typing import Any
from pathlib import Path
import gradio as gr
import glob

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
from user_functions import user_functions

# Global variables to store agent and client
agent_client = None
agent = None
thread = None

def get_support_tickets():
    """Get list of all support ticket files"""
    try:
        script_dir = Path(__file__).parent
        ticket_files = list(script_dir.glob("ticket-*.txt"))
        ticket_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Sort by modification time
        return [f.name for f in ticket_files]
    except Exception as e:
        return [f"Error: {str(e)}"]

def read_ticket_content(filename):
    """Read the content of a support ticket file"""
    if not filename or filename.startswith("Error:"):
        return "No ticket selected or error occurred."
    
    try:
        script_dir = Path(__file__).parent
        file_path = script_dir / filename
        if file_path.exists():
            content = file_path.read_text()
            return content
        else:
            return f"File {filename} not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_latest_ticket():
    """Get the latest created support ticket"""
    tickets = get_support_tickets()
    if tickets and not tickets[0].startswith("Error:"):
        return tickets[0]
    return None

def update_download_button(filename):
    """Update download button with file path"""
    if filename and not filename.startswith("Error:"):
        script_dir = Path(__file__).parent
        file_path = script_dir / filename
        if file_path.exists():
            return gr.DownloadButton(value=str(file_path))
    return gr.DownloadButton(value=None)

def initialize_agent():
    """Initialize the Azure AI Agent"""
    global agent_client, agent, thread
    
    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    # Connect to the Agent client
    agent_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
    )

    # Define an agent that can use the custom functions
    functions = FunctionTool(user_functions)
    toolset = ToolSet()
    toolset.add(functions)
    agent_client.enable_auto_function_calls(toolset)
            
    agent = agent_client.create_agent(
        model=model_deployment,
        name="support-agent",
        instructions="""You are a technical support agent.
                        When a user has a technical issue, you get their email address and a description of the issue.
                        Then you use those values to submit a support ticket using the function available to you.
                        If a file is saved, tell the user the file name.
                    """,
        toolset=toolset
    )

    thread = agent_client.threads.create()
    return f"Agent initialized: {agent.name} ({agent.id})"

def chat_with_agent(message, history):
    """Process user message and return agent response"""
    global agent_client, agent, thread
    
    if not message.strip():
        return history, ""
    
    try:
        # Send a prompt to the agent
        agent_message = agent_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        run = agent_client.runs.create_and_process(
            thread_id=thread.id, 
            agent_id=agent.id
        )

        # Check the run status for failures
        if run.status == "failed":
            response = f"Run failed: {run.last_error}"
        else:
            # Show the latest response from the agent
            last_msg = agent_client.messages.get_last_message_text_by_role(
                thread_id=thread.id,
                role=MessageRole.AGENT,
            )
            response = last_msg.text.value if last_msg else "No response received."
        
        # Add to history using messages format
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        
        return history, ""
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, ""

def get_conversation_history():
    """Get the full conversation history"""
    global agent_client, thread
    
    try:
        # Get the conversation history
        conversation_log = "Conversation Log:\n\n"
        messages = agent_client.messages.list(
            thread_id=thread.id, 
            order=ListSortOrder.ASCENDING
        )
        
        for message in messages:
            if message.text_messages:
                last_msg = message.text_messages[-1]
                conversation_log += f"{message.role}: {last_msg.text.value}\n\n"
        
        return conversation_log
        
    except Exception as e:
        return f"Error retrieving history: {str(e)}"

def reset_conversation():
    """Reset the conversation by creating a new thread"""
    global agent_client, thread
    
    try:
        thread = agent_client.threads.create()
        return [], "", "Conversation reset successfully!"
    except Exception as e:
        return [], "", f"Error resetting conversation: {str(e)}"

def cleanup_agent():
    """Clean up the agent"""
    global agent_client, agent
    
    try:
        if agent and agent_client:
            agent_client.delete_agent(agent.id)
            return "Agent deleted successfully"
    except Exception as e:
        return f"Error deleting agent: {str(e)}"

def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')
    
    # Initialize the agent
    init_message = initialize_agent()
    print(init_message)
    
    # Create Gradio interface
    with gr.Blocks(title="Technical Support Agent") as demo:
        gr.Markdown("# Technical Support Agent")
        gr.Markdown("I'm here to help you with technical issues. Provide your email and describe your problem to submit a support ticket.")
        
        with gr.Row():
            with gr.Column(scale=2):
                # Chat interface
                chatbot = gr.Chatbot(
                    label="Support Chat",
                    height=400,
                    type="messages"
                )
                
                # Message input
                msg = gr.Textbox(
                    label="Enter your message",
                    placeholder="Describe your technical issue and provide your email address...",
                    lines=3
                )
                
                # Buttons
                with gr.Row():
                    submit_btn = gr.Button("Send Message", variant="primary")
                    clear_btn = gr.Button("Reset Chat")
            
            with gr.Column(scale=2):
                # Support Tickets Section
                gr.Markdown("### 📋 Support Tickets")
                
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh List", size="sm")
                
                # Ticket selection dropdown
                ticket_dropdown = gr.Dropdown(
                    label="Select Support Ticket",
                    choices=[],
                    value=None,
                    interactive=True
                )
                
                # Ticket content display
                ticket_content = gr.Textbox(
                    label="Ticket Content",
                    lines=8,
                    max_lines=12,
                    interactive=False,
                    value="No tickets available"
                )
                
                # Download button
                download_btn = gr.DownloadButton(
                    label="📥 Download Ticket",
                    value=None,
                    variant="secondary"
                )
        
        with gr.Row():
            with gr.Column(scale=1):
                # Instructions
                gr.Markdown("""
                ### How to use:
                1. Describe your technical issue
                2. Include your email address
                3. The agent will create a support ticket for you
                4. View and download your tickets from the right panel
                
                ### Example:
                "I'm having trouble with my email not syncing. My email is john@example.com"
                """)
            
            with gr.Column(scale=1):
                # Conversation history section
                with gr.Accordion("Conversation History", open=False):
                    history_btn = gr.Button("Show Full History")
                    history_output = gr.Textbox(
                        label="Complete Conversation Log",
                        lines=8,
                        max_lines=12
                    )
                
                # Status/feedback area
                status_output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=2
                )
        
        # Enhanced chat function that refreshes ticket list
        def enhanced_chat(message, history):
            # Process the chat
            new_history, empty_msg = chat_with_agent(message, history)
            
            # Refresh ticket list and get latest
            updated_tickets = get_support_tickets()
            latest_ticket = updated_tickets[0] if updated_tickets and not updated_tickets[0].startswith("Error:") else None
            latest_content = read_ticket_content(latest_ticket) if latest_ticket else "No tickets available"
            
            return (
                new_history, 
                empty_msg, 
                gr.Dropdown(choices=updated_tickets, value=latest_ticket),
                latest_content,
                update_download_button(latest_ticket)
            )
        
        # Initialize interface when loaded
        def initialize_interface():
            tickets = get_support_tickets()
            latest_ticket = tickets[0] if tickets and not tickets[0].startswith("Error:") else None
            content = read_ticket_content(latest_ticket) if latest_ticket else "No tickets available"
            download_btn_value = update_download_button(latest_ticket)
            
            return [
                init_message,  # status_output
                gr.Dropdown(choices=tickets, value=latest_ticket),  # ticket_dropdown
                content,  # ticket_content
                download_btn_value  # download_btn
            ]
        
        # Event handlers
        submit_btn.click(
            enhanced_chat,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg, ticket_dropdown, ticket_content, download_btn]
        )
        
        msg.submit(
            enhanced_chat,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg, ticket_dropdown, ticket_content, download_btn]
        )
        
        clear_btn.click(
            reset_conversation,
            outputs=[chatbot, msg, status_output]
        )
        
        history_btn.click(
            get_conversation_history,
            outputs=[history_output]
        )
        
        # Ticket dropdown change handler
        ticket_dropdown.change(
            lambda filename: [read_ticket_content(filename), update_download_button(filename)],
            inputs=[ticket_dropdown],
            outputs=[ticket_content, download_btn]
        )
        
        # Refresh button handler
        refresh_btn.click(
            lambda: [
                gr.Dropdown(choices=get_support_tickets(), value=get_latest_ticket()),
                read_ticket_content(get_latest_ticket()) if get_latest_ticket() else "No tickets available",
                update_download_button(get_latest_ticket())
            ],
            outputs=[ticket_dropdown, ticket_content, download_btn]
        )
        
        # Initialize status and tickets on load
        demo.load(
            initialize_interface,
            outputs=[status_output, ticket_dropdown, ticket_content, download_btn]
        )
    
    try:
        print(f"You're chatting with: {agent.name} ({agent.id})")
        print("Starting Gradio interface...")
        
        # Launch the interface
        demo.launch(
            server_name="127.0.0.1",  # Local access only
            server_port=7860,
            share=False,
            debug=True
        )
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up
        cleanup_result = cleanup_agent()
        print(cleanup_result)

if __name__ == '__main__': 
    main()