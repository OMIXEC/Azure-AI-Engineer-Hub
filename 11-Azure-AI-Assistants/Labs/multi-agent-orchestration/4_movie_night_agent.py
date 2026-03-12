"""
Movie Night AI — Final v4 (robust parsing + markdown-aware line parser)

Features:
- Detects and parses JSON block if the orchestrator returns JSON.
- Fallback parser handles line-format, markdown bullets, numbered lists, and bold/italic.
- Extracts sample movies when present in markdown.
- Sensible SAMPLE_MOVIES fallback and teacher-friendly output.
- Ephemeral agents cleaned up after demo.

Usage:
  python agent_movie_night_final_v4.py
"""

import os
import re
import json
from dotenv import load_dotenv
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder
from azure.identity import DefaultAzureCredential

# ---------- small local fallback movie samples (for classroom demo) ----------
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

# ---------- helpers ----------
def pretty_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)

def find_json_block(text):
    """
    Extract the first top-level JSON object or array from `text` using a
    brace/bracket balancing approach. Returns the substring or None.
    """
    if not text:
        return None

    # Try find first '{' for object and first '[' for array
    start_obj = text.find('{')
    start_arr = text.find('[')

    # Build list of found starts (index, opener)
    starts = []
    if start_obj != -1:
        starts.append((start_obj, '{'))
    if start_arr != -1:
        starts.append((start_arr, '['))
    if not starts:
        return None

    # Choose earliest opener
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
    """
    Remove common leading bullet markers and markdown bold/italic.
    """
    s = s.strip()
    s = re.sub(r'^[\-\*\+\s]+', '', s)  # leading bullets/spaces
    # remove surrounding bold/italic markers if the whole string is wrapped
    s = re.sub(r'^\*\*(.+?)\*\*$', r'\1', s)
    s = re.sub(r'^\*(.+?)\*$', r'\1', s)
    s = s.strip()
    return s

def parse_line_format(text):
    """
    Robust parser that accepts:
      - "- **Genre**: Action-Comedy"
      - "GENRE: Action-Comedy"
      - "SNACKS:" followed by "- item" or "1. item" lines
      - numbered snack lists like "1. Spicy nachos + iced cola"
      - FUNFACT: ...
      - Sample movies inside brackets or inline quotes
    Returns dict with keys: genre, genre_reason, snacks, funfact, _samples_tmp (optional)
    """
    parsed = {"genre": None, "genre_reason": None, "snacks": [], "funfact": None}
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() != ""]
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        # remove leading bullet/marker for pattern matching
        no_bullet = re.sub(r'^[\-\*\+]\s*', '', raw)
        # detect key: value with optional bold markers
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
                # collect subsequent bullet/numbered lines as snacks
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
            # bullets or numbered snack lines without "SNACKS:" header
            if re.match(r'^[\-\*\+]\s+', raw) or re.match(r'^\d+\.\s+', raw):
                snack = re.sub(r'^[\-\*\+]\s+|^\d+\.\s+', '', raw).strip()
                snack = clean_markdown(snack)
                parsed["snacks"].append(snack)
            else:
                # check uppercase KEY: style without bullet
                line_upper = raw.upper()
                if line_upper.startswith("GENRE:"):
                    parsed["genre"] = clean_markdown(raw.split(":", 1)[1].strip())
                elif line_upper.startswith("REASON:"):
                    parsed["genre_reason"] = clean_markdown(raw.split(":", 1)[1].strip())
                elif line_upper.startswith("FUNFACT:"):
                    parsed["funfact"] = clean_markdown(raw.split(":", 1)[1].strip())
                elif line_upper.startswith("SNACKS:"):
                    j = i + 1
                    while j < len(lines) and (re.match(r'^[\-\*\+]\s+', lines[j]) or re.match(r'^\d+\.\s+', lines[j])):
                        snack = re.sub(r'^[\-\*\+]\s+|^\d+\.\s+', '', lines[j]).strip()
                        snack = clean_markdown(snack)
                        parsed["snacks"].append(snack)
                        j += 1
                    i = j - 1
                else:
                    # try to extract sample movies inside *italics* or quotes inside the line
                    italics = re.findall(r'\*([^*]+)\*', raw)
                    if italics:
                        tmp = parsed.setdefault("_samples_tmp", [])
                        tmp.extend([s.strip() for s in italics if s.strip()])
                    # also look for bracketed suggestions like [You can dive into classics like *Rush Hour* or *Deadpool*!]
                    bracket_movies = re.findall(r'\[\s*(?:[^\]]*?)\*([^*]+)\*', raw)
                    if bracket_movies:
                        tmp = parsed.setdefault("_samples_tmp", [])
                        tmp.extend([s.strip() for s in bracket_movies if s.strip()])
        i += 1

    # clean snacks
    parsed["snacks"] = [re.sub(r'[\[\]\*]+', '', s).strip() for s in parsed["snacks"] if s.strip()]
    return parsed

# ---------- startup ----------
os.system("cls" if os.name == "nt" else "clear")
load_dotenv()
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME")

if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
    raise RuntimeError("Set PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME in your .env file.")

# ---------- connect to Agents service ----------
agents_client = AgentsClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    ),
)

with agents_client:
    # ---------- create agents ----------
    genre_agent = agents_client.create_agent(
        model=MODEL_DEPLOYMENT,
        name="genre_agent",
        instructions="""
        You are "Genre Guru" — upbeat and decisive.
        Given the user's mood, return a single best-fit genre and one-sentence reason.
        Prefer genres like: Comedy, Adventure, Sci-Fi, Horror, Romance, Drama, Animated, Action-Comedy.
        Output either a small JSON object or a line-format. Examples you may return:

        JSON example:
        {"genre":"Action-Comedy","genre_reason":"... (one sentence)"}

        Line-format example:
        GENRE: Action-Comedy
        REASON: It mixes thrills and laughs to beat boredom.

        Either format is acceptable.
        """
    )

    snack_agent = agents_client.create_agent(
        model=MODEL_DEPLOYMENT,
        name="snack_agent",
        instructions="""
        You are "Snack Specialist".
        Given a genre, recommend 2 snack+drink combos. Return them either as JSON list or as:
        SNACKS:
        - combo 1
        - combo 2
        Keep combos short (<=6 words each).
        """
    )

    funfact_agent = agents_client.create_agent(
        model=MODEL_DEPLOYMENT,
        name="funfact_agent",
        instructions="""
        You are "Trivia Trove".
        Given a genre, return a single short fun fact (<=25 words).
        Return either: FUNFACT: <text> or JSON { "funfact": "..." }.
        """
    )

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
          - A JSON object with keys: genre, genre_reason, snacks (list), funfact, sample_movies (list)
        OR
          - A human-friendly two-part output: line-format fields and then a "Movie Night Plan" paragraph.

        If you return JSON, prefer the keys exactly as above.
        """
        ,
        tools=[genre_tool.definitions[0], snack_tool.definitions[0], funfact_tool.definitions[0]]
    )

    # ---------- run demo ----------
    print("\n🎬 --- Movie Night AI (Final v4 Teaching Demo) --- 🎬\n")
    mood = input("Enter a mood (e.g., bored, romantic, hungry, sleepy, adventurous): ").strip()

    thread = agents_client.threads.create()
    user_message = f"My mood is: {mood}. Plan a fun movie night for me (genre + snacks + fun fact)."
    agents_client.messages.create(thread_id=thread.id, role=MessageRole.USER, content=user_message)

    print("\n🍿 Planning... (orchestrator will call helper agents behind the scenes)\n")
    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=orchestrator.id)

    if run.status == "failed":
        print("Run failed:", run.last_error)

    # retrieve messages and show raw outputs
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    assistant_texts = []
    print("---- Raw assistant output (what the orchestrator returned) ----\n")
    for msg in messages:
        if msg.text_messages:
            text = msg.text_messages[-1].text.value
            assistant_texts.append(text)
            print(text)
            print("------------------------------------------------------------\n")

    combined_text = "\n".join(assistant_texts)

    # ---------- parsing (auto-detect JSON or fall back to line format) ----------
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
            print("Detected and parsed a JSON block from the assistant output.")
        except Exception as e:
            print("Found a JSON-like block but failed to load it:", e)
            line_parsed = parse_line_format(combined_text)
            parsed.update({k: v for k, v in line_parsed.items() if v})
    else:
        line_parsed = parse_line_format(combined_text)
        parsed.update({k: v for k, v in line_parsed.items() if v})
        print("No JSON detected; used line-format parsing.")

    # If parser captured italicized/sample movies in _samples_tmp, add them
    if "_samples_tmp" in parsed and parsed["_samples_tmp"]:
        # append to sample_movies while avoiding duplicates
        tmp = [s for s in parsed["_samples_tmp"] if s and s not in parsed["sample_movies"]]
        parsed["sample_movies"].extend(tmp)
        del parsed["_samples_tmp"]

    # ---------- ensure sensible fallback sample movies ----------
    if parsed["genre"] and parsed["genre"] in SAMPLE_MOVIES:
        parsed["sample_movies"] = SAMPLE_MOVIES[parsed["genre"]]
    elif not parsed["sample_movies"]:
        mixed = []
        for v in SAMPLE_MOVIES.values():
            mixed.extend(v)
        parsed["sample_movies"] = list(dict.fromkeys(mixed))[:3]

    # ---------- present outputs ----------
    print("\n==== Parsed structured result ====\n")
    print(pretty_json(parsed))

    print("\n==== Friendly Movie Night Plan ====\n")
    genre_line = f"Genre suggestion: {parsed['genre'] or 'A surprise mix'}"
    if parsed.get("genre_reason"):
        genre_line += f" — {parsed['genre_reason']}"
    print(genre_line)

    print("\nSnacks & drinks:")
    if parsed["snacks"]:
        for s in parsed["snacks"]:
            print("-", s)
    else:
        print("- Chef's choice snacks!")

    if parsed.get("funfact"):
        print("\nFun fact:")
        print(parsed["funfact"])

    if parsed["sample_movies"]:
        print("\nSample movies:")
        print(", ".join(parsed["sample_movies"]))

    # ---------- cleanup ----------
    print("\nCleaning up agents (ephemeral demo) ...")
    for agent_obj in [orchestrator, genre_agent, snack_agent, funfact_agent]:
        try:
            agents_client.delete_agent(agent_obj.id)
        except Exception as e:
            print("Warning: deleting agent failed:", e)

    print("\nDone.")