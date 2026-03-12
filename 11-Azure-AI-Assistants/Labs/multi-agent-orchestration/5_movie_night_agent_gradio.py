"""
Movie Night AI — Gradio Web Interface v1.0

Features:
- Beautiful, user-friendly Gradio interface
- Multi-agent AI system integration
- Enhanced UI with themes, emojis, and visual elements
- Real-time processing with progress updates
- Mood suggestions and presets
- Responsive design with custom CSS
- Error handling and user feedback

Usage:
  python movie_night_gradio.py
"""

import os
import re
import json
import gradio as gr
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder
from azure.identity import DefaultAzureCredential

# ---------- Configuration and Setup ----------
load_dotenv()
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME")

# Sample movies for fallback
SAMPLE_MOVIES = {
    "Comedy": ["The Grand Budapest Hotel", "Superbad", "Hunt for the Wilderpeople"],
    "Adventure": ["Raiders of the Lost Ark", "Jumanji: Welcome to the Jungle", "The Secret Life of Walter Mitty"],
    "Sci-Fi": ["Interstellar", "The Matrix", "Blade Runner 2049"],
    "Horror": ["Get Out", "A Quiet Place", "The Conjuring"],
    "Romance": ["La La Land", "The Big Sick", "About Time"],
    "Drama": ["The Shawshank Redemption", "Moonlight", "Parasite"],
    "Animated": ["Coco", "Spider-Man: Into the Spider-Verse", "Kubo and the Two Strings"],
    "Action-Comedy": ["Rush Hour", "21 Jump Street", "Deadpool", "The Other Guys"]
}

# Mood presets for user convenience
MOOD_PRESETS = [
    "😴 Sleepy & cozy", "😂 Want to laugh", "💕 Feeling romantic", "🎭 In the mood for drama",
    "😱 Want some thrills", "🚀 Adventurous spirit", "🤖 Love sci-fi", "👨‍👩‍👧‍👦 Family time",
    "🍿 Just bored", "😢 Need comfort", "🧠 Want something deep", "🎪 Quirky & weird"
]

# Custom CSS for enhanced styling
CUSTOM_CSS = """
.mood-button {
    margin: 2px !important;
    border-radius: 15px !important;
    font-size: 14px !important;
}

.header-text {
    text-align: center;
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #feca57);
    background-size: 300% 300%;
    animation: gradient 3s ease infinite;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5em;
    font-weight: bold;
    margin: 20px 0;
}

@keyframes gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.result-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    padding: 20px;
    color: white;
    margin: 10px 0;
}

.snack-list {
    
    border-left: 4px solid #28a745;
    padding: 15px;
    margin: 10px 0;
    border-radius: 5px;
}

.movie-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 10px;
    margin: 15px 0;
}

.movie-card {
    
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    
}

.loading-spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 2s linear infinite;
    margin: 20px auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
"""

# ---------- Core Agent Functions ----------
def pretty_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)

def find_json_block(text):
    """Extract JSON block from text using brace/bracket balancing."""
    if not text:
        return None

    start_obj = text.find('{')
    start_arr = text.find('[')
    
    starts = []
    if start_obj != -1:
        starts.append((start_obj, '{'))
    if start_arr != -1:
        starts.append((start_arr, '['))
    if not starts:
        return None

    starts.sort(key=lambda x: x[0])
    start_index, opener = starts[0]
    closer = '}' if opener == '{' else ']'

    depth = 0
    in_string = False
    escape = False
    for i in range(start_index, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        else:
            if ch == '"':
                in_string = True
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start_index:i+1]
    return None

def clean_markdown(s):
    """Remove markdown formatting."""
    s = s.strip()
    s = re.sub(r'^[\-\*\+\s]+', '', s)
    s = re.sub(r'^\*\*(.+?)\*\*$', r'\1', s)
    s = re.sub(r'^\*(.+?)\*$', r'\1', s)
    s = s.strip()
    return s

def parse_line_format(text):
    """Parse line-format output from agents."""
    parsed = {"genre": None, "genre_reason": None, "snacks": [], "funfact": None}
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() != ""]
    i = 0
    
    while i < len(lines):
        raw = lines[i].strip()
        no_bullet = re.sub(r'^[\-\*\+]\s*', '', raw)
        kv_match = re.match(r'^(?:\*{0,2})\s*([A-Za-z ]{3,30}?)\s*(?:\*{0,2})\s*[:\-]\s*(.+)$', no_bullet)
        
        if kv_match:
            key = kv_match.group(1).strip().lower()
            val = kv_match.group(2).strip()
            val = re.sub(r'^[\*\s]+|[\*\s]+$', '', val).strip()
            
            if key.startswith("genre"):
                parsed["genre"] = clean_markdown(val)
            elif key.startswith("reason") or key.startswith("genre reason"):
                parsed["genre_reason"] = clean_markdown(val)
            elif key.startswith("funfact") or key.startswith("fun fact"):
                parsed["funfact"] = clean_markdown(val)
            elif key.startswith("snacks"):
                j = i + 1
                while j < len(lines):
                    l = lines[j].strip()
                    if re.match(r'^[\-\*\+]\s+', l) or re.match(r'^\d+\.\s+', l):
                        snack = re.sub(r'^[\-\*\+]\s+|^\d+\.\s+', '', l).strip()
                        snack = clean_markdown(snack)
                        parsed["snacks"].append(snack)
                        j += 1
                    else:
                        break
                i = j - 1
        else:
            if re.match(r'^[\-\*\+]\s+', raw) or re.match(r'^\d+\.\s+', raw):
                snack = re.sub(r'^[\-\*\+]\s+|^\d+\.\s+', '', raw).strip()
                snack = clean_markdown(snack)
                parsed["snacks"].append(snack)
        i += 1
    
    parsed["snacks"] = [re.sub(r'[\[\]\*]+', '', s).strip() for s in parsed["snacks"] if s.strip()]
    return parsed

# Global agents client
agents_client = None

def initialize_agents():
    """Initialize the agents client and create agents."""
    global agents_client
    
    if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
        raise ValueError("Please set PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME in your .env file.")
    
    agents_client = AgentsClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
    )
    
    return agents_client

def create_movie_night_plan(mood: str, progress=gr.Progress()) -> Tuple[str, str, str, str]:
    """Main function to create movie night plan using AI agents."""
    try:
        progress(0.1, desc="🤖 Initializing AI agents...")
        
        if not agents_client:
            initialize_agents()
        
        with agents_client:
            progress(0.2, desc="🎭 Creating genre specialist...")
            
            # Create agents
            genre_agent = agents_client.create_agent(
                model=MODEL_DEPLOYMENT,
                name="genre_agent",
                instructions="""
                You are "Genre Guru" — upbeat and decisive.
                Given the user's mood, return a single best-fit genre and a meaningful one-sentence reason that explains WHY this genre matches their mood.
                
                Prefer genres like: Comedy, Adventure, Sci-Fi, Horror, Romance, Drama, Animated, Action-Comedy.
                
                IMPORTANT: Always provide a specific, helpful reason - NEVER return "none", "null", or empty reasons.
                
                Output examples:
                JSON format:
                {"genre":"Action-Comedy","genre_reason":"The perfect blend of excitement and humor will lift your spirits and keep you engaged"}
                
                Line format:
                GENRE: Drama
                REASON: Deep storytelling and emotional depth will resonate with your reflective mood
                
                Make sure your reason is specific, encouraging, and explains the connection between the mood and genre choice.
                """
            )
            
            progress(0.3, desc="🍿 Creating snack specialist...")
            
            snack_agent = agents_client.create_agent(
                model=MODEL_DEPLOYMENT,
                name="snack_agent",
                instructions="""
                You are "Snack Specialist".
                Given a genre, recommend 2 snack+drink combos. Return them either as JSON list or as:
                SNACKS:
                - combo 1
                - combo 2
                Keep combos short (<=6 words each) and make them appealing and specific.
                """
            )
            
            progress(0.4, desc="🧠 Creating trivia expert...")
            
            funfact_agent = agents_client.create_agent(
                model=MODEL_DEPLOYMENT,
                name="funfact_agent",
                instructions="""
                You are "Trivia Trove".
                Given a genre, return a single short fun fact (<=25 words) about that genre.
                Make it interesting and engaging!
                Return either: FUNFACT: <text> or JSON { "funfact": "..." }.
                """
            )
            
            progress(0.5, desc="🎬 Setting up movie night orchestrator...")
            
            # Tools
            genre_tool = ConnectedAgentTool(id=genre_agent.id, name="genre_agent", description="Picks genre")
            snack_tool = ConnectedAgentTool(id=snack_agent.id, name="snack_agent", description="Suggests snacks")
            funfact_tool = ConnectedAgentTool(id=funfact_agent.id, name="funfact_agent", description="Gives a fun fact")
            
            orchestrator = agents_client.create_agent(
                model=MODEL_DEPLOYMENT,
                name="movie_night_orchestrator",
                instructions="""
                You are "Movie Night Planner".
                Use the connected tools to:
                  1) Determine one movie genre (call genre_agent)
                  2) Based on genre, get 2 snack combos (call snack_agent)  
                  3) Get one fun fact (call funfact_agent)

                Produce EITHER:
                  - A JSON object with keys: genre, genre_reason, snacks (list), funfact
                OR
                  - A human-friendly output with line-format fields.

                Be enthusiastic and make the recommendations engaging!
                """,
                tools=[genre_tool.definitions[0], snack_tool.definitions[0], funfact_tool.definitions[0]]
            )
            
            progress(0.6, desc="💭 Processing your mood...")
            
            # Create thread and process request
            thread = agents_client.threads.create()
            user_message = f"My mood is: {mood}. Plan a fun movie night for me (genre + snacks + fun fact)."
            agents_client.messages.create(thread_id=thread.id, role=MessageRole.USER, content=user_message)
            
            progress(0.7, desc="🎯 AI agents are collaborating...")
            
            run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=orchestrator.id)
            
            if run.status == "failed":
                return "❌ Error", f"Run failed: {run.last_error}", "", ""
            
            progress(0.8, desc="📊 Parsing recommendations...")
            
            # Retrieve and parse messages
            messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
            assistant_texts = []
            raw_output = ""
            
            for msg in messages:
                if msg.text_messages:
                    text = msg.text_messages[-1].text.value
                    assistant_texts.append(text)
                    raw_output += text + "\n"
            
            combined_text = "\n".join(assistant_texts)
            
            # Parse output
            parsed = {"genre": None, "genre_reason": None, "snacks": [], "funfact": None, "sample_movies": []}
            
            json_block = find_json_block(combined_text)
            if json_block:
                try:
                    data = json.loads(json_block)
                    parsed["genre"] = data.get("genre") or parsed["genre"]
                    parsed["genre_reason"] = data.get("genre_reason") or data.get("reason") or parsed["genre_reason"]
                    snacks = data.get("snacks") or data.get("snack") or []
                    if isinstance(snacks, str):
                        parsed["snacks"] = [s.strip() for s in re.split(r"[;,]\s*|\n", snacks) if s.strip()]
                    elif isinstance(snacks, list):
                        parsed["snacks"] = snacks
                    parsed["funfact"] = data.get("funfact") or data.get("fun_fact") or parsed["funfact"]
                    parsed["sample_movies"] = data.get("sample_movies") or data.get("movies") or []
                except Exception:
                    line_parsed = parse_line_format(combined_text)
                    parsed.update({k: v for k, v in line_parsed.items() if v})
            else:
                line_parsed = parse_line_format(combined_text)
                parsed.update({k: v for k, v in line_parsed.items() if v})
            
            progress(0.9, desc="🎪 Adding sample movies...")
            
            # Add sample movies
            if parsed["genre"] and parsed["genre"] in SAMPLE_MOVIES:
                parsed["sample_movies"] = SAMPLE_MOVIES[parsed["genre"]]
            elif not parsed["sample_movies"]:
                mixed = []
                for v in SAMPLE_MOVIES.values():
                    mixed.extend(v)
                parsed["sample_movies"] = list(dict.fromkeys(mixed))[:3]
            
            progress(1.0, desc="✨ Your movie night is ready!")
            
            # Cleanup agents
            try:
                for agent_obj in [orchestrator, genre_agent, snack_agent, funfact_agent]:
                    agents_client.delete_agent(agent_obj.id)
            except Exception:
                pass  # Ignore cleanup errors
            
            # Format output
            genre_display = format_genre_output(parsed)
            snacks_display = format_snacks_output(parsed)
            funfact_display = format_funfact_output(parsed)
            movies_display = format_movies_output(parsed)
            
            return genre_display, snacks_display, funfact_display, movies_display
    
    except Exception as e:
        return "❌ Error", f"An error occurred: {str(e)}", "", ""

def format_genre_output(parsed: Dict) -> str:
    """Format genre output with emojis and styling."""
    genre_emojis = {
        "Comedy": "😂", "Adventure": "🗺️", "Sci-Fi": "🚀", "Horror": "😱",
        "Romance": "💕", "Drama": "🎭", "Animated": "🎨", "Action-Comedy": "🎬"
    }
    
    genre = parsed.get("genre", "Mystery Genre")
    emoji = genre_emojis.get(genre, "🎬")
    reason = parsed.get("genre_reason", "Perfect for your current mood!")
    
    return f"""
    <div class="result-card">
        <h2>{emoji} {genre}</h2>
        <p><em>"{reason}"</em></p>
    </div>
    """

def format_snacks_output(parsed: Dict) -> str:
    """Format snacks output with styling."""
    snacks = parsed.get("snacks", ["Popcorn & soda", "Candy & juice"])
    
    snack_html = "<div class='snack-list'><h3>🍿 Perfect Snack Combos:</h3><ul>"
    for snack in snacks:
        snack_html += f"<li><strong>{snack}</strong></li>"
    snack_html += "</ul></div>"
    
    return snack_html

def format_funfact_output(parsed: Dict) -> str:
    """Format fun fact output."""
    funfact = parsed.get("funfact", "Movies are a great way to unwind and explore new worlds!")
    return f"""
    <div style="background: linear-gradient(45deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%); 
                border-radius: 10px; padding: 15px; margin: 10px 0;">
        <h3>🧠 Fun Fact</h3>
        <p style="font-size: 16px; color: #333;"><em>{funfact}</em></p>
    </div>
    """

def format_movies_output(parsed: Dict) -> str:
    """Format movies output with grid layout."""
    movies = parsed.get("sample_movies", [])
    if not movies:
        return "<p>No movie suggestions available.</p>"
    
    movie_html = "<div class='movie-grid'>"
    for movie in movies[:6]:  # Show max 6 movies
        movie_html += f"""
        <div class="movie-card">
            <strong>{movie}</strong>
        </div>
        """
    movie_html += "</div>"
    
    return f"""
    <div>
        <h3>🎬 Sample Movies to Consider:</h3>
        {movie_html}
    </div>
    """

def set_mood_preset(mood_preset):
    """Set mood from preset buttons."""
    return mood_preset

def create_interface():
    """Create the Gradio interface."""
    
    # Initialize agents client
    try:
        initialize_agents()
    except Exception as e:
        print(f"Warning: Could not initialize agents client: {e}")
    
    with gr.Blocks(css=CUSTOM_CSS, title="🎬 Movie Night AI", theme=gr.themes.Soft()) as interface:
        
        # Header
        gr.HTML("""
            <div class="header-text">
                🎬 Movie Night AI Assistant 🍿
            </div>
            <p style="text-align: center; font-size: 1.2em; color: #666; margin-bottom: 30px;">
                Let AI curate your perfect movie night experience!
            </p>
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML("<h3>🎯 Tell us your mood:</h3>")
                
                # Mood input
                mood_input = gr.Textbox(
                    label="How are you feeling?",
                    placeholder="e.g., bored, romantic, adventurous, sleepy...",
                    lines=2,
                    value="",
                    elem_id="mood-input"
                )
                
                # Quick mood presets
                gr.HTML("<h4>✨ Or pick a mood:</h4>")
                
                with gr.Row():
                    mood_buttons = []
                    for i in range(0, len(MOOD_PRESETS), 3):
                        with gr.Row():
                            for j in range(3):
                                if i + j < len(MOOD_PRESETS):
                                    btn = gr.Button(
                                        MOOD_PRESETS[i + j],
                                        elem_classes="mood-button",
                                        size="sm"
                                    )
                                    mood_buttons.append(btn)
                
                # Generate button
                generate_btn = gr.Button(
                    "🎬 Create My Movie Night Plan!",
                    variant="primary",
                    size="lg",
                    elem_id="generate-btn"
                )
                
            with gr.Column(scale=2):
                gr.HTML("<h3>🎪 Your Personalized Movie Night Plan:</h3>")
                
                # Output sections
                genre_output = gr.HTML(label="🎭 Genre Recommendation")
                snacks_output = gr.HTML(label="🍿 Snack Suggestions")
                funfact_output = gr.HTML(label="🧠 Fun Fact")
                movies_output = gr.HTML(label="🎬 Movie Suggestions")
        
        # Examples section
        gr.HTML("""
            <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h3>💡 Need inspiration? Try these moods:</h3>
                <p><strong>😴 "Sleepy and want something cozy"</strong> → Get comfort movies with warm snacks</p>
                <p><strong>🎉 "Excited and energetic"</strong> → Get action-packed adventures with energizing treats</p>
                <p><strong>💕 "Romantic and dreamy"</strong> → Get heartwarming romance with sweet snacks</p>
                <p><strong>🤔 "Thoughtful and introspective"</strong> → Get deep dramas with sophisticated pairings</p>
            </div>
        """)
        
        # Event handlers
        for btn in mood_buttons:
            btn.click(
                fn=set_mood_preset,
                inputs=[btn],
                outputs=[mood_input]
            )
        
        generate_btn.click(
            fn=create_movie_night_plan,
            inputs=[mood_input],
            outputs=[genre_output, snacks_output, funfact_output, movies_output],
            show_progress=True
        )
        
        # Footer
        gr.HTML("""
            <div style="text-align: center; margin-top: 30px; padding: 20px; color: #666;">
                <p>🤖 Powered by Azure AI Agents | Built with ❤️ using Gradio</p>
                <p><em>Perfect movie nights, powered by AI</em></p>
            </div>
        """)
    
    return interface

# ---------- Main Application ----------
if __name__ == "__main__":
    # Clear console
    os.system("cls" if os.name == "nt" else "clear")
    
    print("🎬 Starting Movie Night AI Gradio Interface...")
    print("🌐 Initializing web server...")
    
    # Create and launch interface
    app = create_interface()
    
    # Launch with custom settings
    app.launch(
        server_name="127.0.0.1", # Local access
        server_port=7860,        # Default Gradio port
        share=False,             # Set to True for public sharing
        debug=True,              # Enable debug mode
        show_error=True,         # Show errors in interface
        quiet=False,             # Show startup logs
        inbrowser=True,          # Auto-open browser
        favicon_path=None,       # Add custom favicon if desired
    )