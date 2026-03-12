"""
CineMatch — SaaS Movie Advisor (Gradio Edition)
================================================
Production-ready web application built with Gradio and Azure AI Agents.

Features:
  ✦ Multi-turn conversational AI (persistent session per browser tab)
  ✦ Live movie data from TMDb (popularity, year, genre, similarity)
  ✦ UserProfile schema — preferences remembered across the session
  ✦ FunctionTool auto-execution: search, recommend, trending
  ✦ Beautiful dark UI with branded design
  ✦ Per-session agent isolation (safe for multi-user SaaS)
  ✦ Agent cleanup on session end

Environment (.env):
    PROJECT_ENDPOINT      — Azure AI Foundry project endpoint
    MODEL_DEPLOYMENT_NAME — Your deployed model (e.g. gpt-4o)
    TMDB_API_KEY          — Get free key at themoviedb.org/settings/api

Usage:
    python movie-advisor-gradio.py
    # Open http://127.0.0.1:7860 in your browser
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

import gradio as gr
import requests as http_requests
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ListSortOrder, MessageRole, ToolSet
from azure.core.exceptions import AzureError, HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME", "")
TMDB_API_KEY     = os.getenv("TMDB_API_KEY", "")
TMDB_BASE        = "https://api.themoviedb.org/3"
TMDB_IMG_BASE    = "https://image.tmdb.org/t/p/w342"

TMDB_GENRE_MAP: dict[str, int] = {
    "action": 28, "adventure": 12, "animation": 16, "animated": 16,
    "comedy": 35, "crime": 80, "documentary": 99, "drama": 18,
    "family": 10751, "fantasy": 14, "history": 36, "horror": 27,
    "mystery": 9648, "romance": 10749, "sci-fi": 878,
    "science fiction": 878, "thriller": 53, "war": 10752, "western": 37,
}

CONFIG_ERROR: str | None = None
if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
    CONFIG_ERROR = "⚠️  Set PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME in your .env file."
if not TMDB_API_KEY:
    logger.warning("TMDB_API_KEY not set — live search unavailable")


# ---------------------------------------------------------------------------
# UserProfile Schema
# ---------------------------------------------------------------------------
@dataclass
class UserProfile:
    fav_genres:      list[str] = field(default_factory=list)
    disliked_genres: list[str] = field(default_factory=list)
    preferred_years: list[int] = field(default_factory=list)
    min_rating:      float      = 6.0
    watched_movies:  list[str] = field(default_factory=list)
    liked_movies:    list[str] = field(default_factory=list)
    disliked_movies: list[str] = field(default_factory=list)
    mood:            str        = ""

    def summary(self) -> str:
        parts = []
        if self.fav_genres:
            parts.append(f"**Genres:** {', '.join(self.fav_genres)}")
        if self.preferred_years:
            parts.append(f"**Era:** {min(self.preferred_years)}–{max(self.preferred_years)}")
        if self.liked_movies:
            parts.append(f"**Loved:** {', '.join(self.liked_movies[:5])}")
        if self.watched_movies:
            parts.append(f"**Watched {len(self.watched_movies)} movies**")
        if self.mood:
            parts.append(f"**Mood:** {self.mood}")
        return "  \n".join(parts) if parts else "*No preferences captured yet.*"


# ---------------------------------------------------------------------------
# Session state — one per Gradio session
# ---------------------------------------------------------------------------
@dataclass
class Session:
    session_id:  str
    profile:     UserProfile
    client:      AgentsClient | None  = None
    agent_id:    str | None           = None
    thread_id:   str | None           = None

    def close(self) -> None:
        """Clean up Azure resources."""
        if self.client and self.agent_id:
            try:
                self.client.delete_agent(self.agent_id)
                logger.info("[%s] Agent deleted", self.session_id)
            except AzureError as e:
                logger.warning("[%s] Could not delete agent: %s", self.session_id, e)
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# TMDb helpers
# ---------------------------------------------------------------------------
def _tmdb_get(path: str, params: dict | None = None) -> dict:
    base = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        base.update(params)
    r = http_requests.get(f"{TMDB_BASE}{path}", params=base, timeout=10)
    r.raise_for_status()
    return r.json()


def _fmt(m: dict, include_poster: bool = False) -> dict:
    result = {
        "title":      m.get("title", "Unknown"),
        "year":       (m.get("release_date") or "")[:4] or "N/A",
        "rating":     round(m.get("vote_average", 0), 1),
        "votes":      m.get("vote_count", 0),
        "overview":   (m.get("overview") or "")[:220],
        "popularity": round(m.get("popularity", 0), 1),
    }
    if include_poster and m.get("poster_path"):
        result["poster"] = TMDB_IMG_BASE + m["poster_path"]
    return result


# ---------------------------------------------------------------------------
# Agent function tools (factories bound to each session's profile)
# ---------------------------------------------------------------------------
def make_agent_functions(profile: UserProfile) -> set:
    """Create closure-bound agent functions for a single session."""

    def search_movies(
        genres: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float = 6.0,
        sort_by: str = "popularity.desc",
        limit: int = 8,
    ) -> str:
        """
        Search TMDb for movies matching genre(s), year range, and minimum rating.

        Args:
            genres:     List of genre names (e.g. ["comedy", "sci-fi"]).
            year_from:  Earliest release year included.
            year_to:    Latest release year included.
            min_rating: Minimum TMDb rating (0–10).
            sort_by:    Sort field — "popularity.desc", "vote_average.desc",
                        "release_date.desc".
            limit:      Max number of results (up to 20).
        Returns:
            JSON with matching movies list.
        """
        ids = [str(TMDB_GENRE_MAP[g.lower().strip()]) for g in (genres or []) if g.lower().strip() in TMDB_GENRE_MAP]
        params: dict[str, Any] = {"sort_by": sort_by, "vote_count.gte": 150, "vote_average.gte": min_rating}
        if ids:
            params["with_genres"] = ",".join(ids)
        if year_from:
            params["primary_release_date.gte"] = f"{year_from}-01-01"
        if year_to:
            params["primary_release_date.lte"] = f"{year_to}-12-31"
        try:
            data = _tmdb_get("/discover/movie", params)
            watched_lower = [w.lower() for w in profile.watched_movies]
            movies = [_fmt(m, include_poster=True) for m in data.get("results", [])[:limit * 2]]
            movies = [m for m in movies if m["title"].lower() not in watched_lower][:limit]
            return json.dumps({"movies": movies, "total_found": data.get("total_results", 0)})
        except Exception as e:
            return json.dumps({"error": str(e), "movies": []})

    def get_similar_movies(movie_title: str, limit: int = 6) -> str:
        """
        Find movies similar to a title the user enjoyed.

        Args:
            movie_title: Title of a movie the user liked.
            limit:       Number of recommendations.
        Returns:
            JSON with similar movies.
        """
        try:
            res = _tmdb_get("/search/movie", {"query": movie_title, "include_adult": False})
            results = res.get("results", [])
            if not results:
                return json.dumps({"error": f"Movie '{movie_title}' not found", "movies": []})
            mid = results[0]["id"]
            data = _tmdb_get(f"/movie/{mid}/similar")
            watched_lower = [w.lower() for w in profile.watched_movies]
            movies = [_fmt(m, include_poster=True) for m in data.get("results", [])[:limit * 2] if m.get("vote_count", 0) > 50]
            movies = [m for m in movies if m["title"].lower() not in watched_lower][:limit]
            return json.dumps({"based_on": results[0]["title"], "movies": movies})
        except Exception as e:
            return json.dumps({"error": str(e), "movies": []})

    def get_trending_movies(time_window: str = "week", limit: int = 8) -> str:
        """
        Fetch currently trending movies.

        Args:
            time_window: "day" or "week".
            limit:       Number of results.
        Returns:
            JSON with trending movies.
        """
        try:
            data = _tmdb_get(f"/trending/movie/{time_window}")
            movies = [_fmt(m, include_poster=True) for m in data.get("results", [])[:limit]]
            return json.dumps({"time_window": time_window, "movies": movies})
        except Exception as e:
            return json.dumps({"error": str(e), "movies": []})

    def update_user_profile(
        fav_genres:      list[str] | None = None,
        disliked_genres: list[str] | None = None,
        year_from:       int | None       = None,
        year_to:         int | None       = None,
        liked_movies:    list[str] | None = None,
        watched_movies:  list[str] | None = None,
        disliked_movies: list[str] | None = None,
        mood:            str | None       = None,
        min_rating:      float | None     = None,
    ) -> str:
        """
        Update the user's preference profile with information learned during conversation.

        Args:
            fav_genres:      Genres the user likes.
            disliked_genres: Genres to avoid.
            year_from:       Start of preferred release year range.
            year_to:         End of preferred release year range.
            liked_movies:    Movies the user enjoyed.
            watched_movies:  Movies already seen.
            disliked_movies: Movies the user disliked.
            mood:            User's current mood.
            min_rating:      Minimum acceptable rating.
        Returns:
            JSON confirming update.
        """
        if fav_genres:
            profile.fav_genres      = list(set(profile.fav_genres + fav_genres))
        if disliked_genres:
            profile.disliked_genres = list(set(profile.disliked_genres + disliked_genres))
        if year_from or year_to:
            profile.preferred_years = list(range(year_from or 1980, (year_to or 2025) + 1))
        if liked_movies:
            profile.liked_movies    = list(set(profile.liked_movies + liked_movies))
        if watched_movies:
            profile.watched_movies  = list(set(profile.watched_movies + watched_movies))
        if disliked_movies:
            profile.disliked_movies = list(set(profile.disliked_movies + disliked_movies))
        if mood:
            profile.mood = mood
        if min_rating is not None:
            profile.min_rating = float(min_rating)
        return json.dumps({"status": "updated", "genres": profile.fav_genres, "mood": profile.mood})

    def get_user_profile() -> str:
        """Return the current user preference profile as JSON."""
        return json.dumps({
            "fav_genres":      profile.fav_genres,
            "disliked_genres": profile.disliked_genres,
            "preferred_years": f"{min(profile.preferred_years, default=1980)}–{max(profile.preferred_years, default=2025)}" if profile.preferred_years else "any",
            "min_rating":      profile.min_rating,
            "liked_movies":    profile.liked_movies,
            "watched_movies":  profile.watched_movies,
            "mood":            profile.mood,
        })

    return {search_movies, get_similar_movies, get_trending_movies, update_user_profile, get_user_profile}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are "CineMatch" — a premium AI movie advisor with real-time search tools.

YOUR WORKFLOW:
1. Greet warmly and ask 2-3 preference questions (genres, mood, a movie they loved recently).
2. Call update_user_profile() whenever you learn something.
3. Use search_movies() with discovered genres/year range.
4. Use get_similar_movies() when user mentions a movie they liked.  
5. Use get_trending_movies() to add current popular picks.
6. ALWAYS filter out movies in watched_movies.
7. Present 5+ personalized recommendations with year, rating, and a 1-sentence "why this fits you" explanation.

RULES:
- Ask one discovery question at a time, naturally.
- Update the profile after every answer with update_user_profile().
- Support multiple genres (e.g. "sci-fi and comedy").
- Be enthusiastic, concise, and personalized.
- When users say a movie title, note it as watched unless they say they loved/hated it.
"""


def create_session() -> Session:
    if CONFIG_ERROR:
        raise RuntimeError(CONFIG_ERROR)

    session_id = str(uuid.uuid4())[:8]
    profile    = UserProfile()
    functions  = make_agent_functions(profile)

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    client = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    fn_tool = FunctionTool(functions)
    toolset = ToolSet()
    toolset.add(fn_tool)
    client.enable_auto_function_calls(toolset)

    agent = client.create_agent(
        model=MODEL_DEPLOYMENT,
        name=f"cinematch-{session_id}",
        instructions=SYSTEM_PROMPT,
        toolset=toolset,
    )
    thread = client.threads.create()

    logger.info("[%s] Session started — agent: %s", session_id, agent.id)
    return Session(
        session_id=session_id,
        profile=profile,
        client=client,
        agent_id=agent.id,
        thread_id=thread.id,
    )


def chat(
    message: str,
    history: list[dict],
    session_state: dict,
) -> tuple[str, list[tuple[str, str]], dict, str]:
    """
    Gradio chat handler. Maintains one Azure AI Agent session per browser tab.
    Returns: (cleared_input, updated_history, updated_session_state, profile_md)
    """
    if CONFIG_ERROR:
        history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ {CONFIG_ERROR}"}]
        return "", history, session_state, "*Config error*"

    # Initialize session on first message
    session: Session | None = session_state.get("session")
    if session is None:
        try:
            session = create_session()
            session_state = {"session": session}
        except Exception as e:
            logger.error("Session init failed: %s", e)
            history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ Failed to start session: {e}"}]
            return "", history, session_state, "*Error*"

    # First message — kick off with agent greeting first, then handle user message
    if not history:
        try:
            session.client.messages.create(
                thread_id=session.thread_id,
                role=MessageRole.USER,
                content="Hello! I'm looking for a great movie to watch.",
            )
            intro_run = session.client.runs.create_and_process(
                thread_id=session.thread_id,
                agent_id=session.agent_id,
            )
            if intro_run.status != "failed":
                intro = session.client.messages.get_last_message_text_by_role(
                    thread_id=session.thread_id, role=MessageRole.AGENT
                )
                if intro:
                    history = [{"role": "assistant", "content": intro.text.value}]
        except Exception as e:
            logger.warning("Intro run failed: %s", e)

        if message.strip().lower() in ("hi", "hello", "hey", "start", ""):
            profile_md = session.profile.summary()
            return "", history, session_state, profile_md

    # Send user message
    try:
        session.client.messages.create(
            thread_id=session.thread_id,
            role=MessageRole.USER,
            content=message.strip(),
        )
        run = session.client.runs.create_and_process(
            thread_id=session.thread_id,
            agent_id=session.agent_id,
        )

        if run.status == "failed":
            reply = f"❌ Agent error: {run.last_error}"
        else:
            last = session.client.messages.get_last_message_text_by_role(
                thread_id=session.thread_id, role=MessageRole.AGENT
            )
            reply = last.text.value if last else "*(No response)*"

    except HttpResponseError as e:
        reply = f"❌ Azure API error [{e.status_code}]: {e.message}"
    except Exception as e:
        reply = f"❌ Error: {e}"

    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    profile_md = session.profile.summary()
    return "", history, session_state, profile_md


def reset_session(session_state: dict) -> tuple[list, dict, str]:
    """Clear chat and delete agent for this session."""
    session: Session | None = session_state.get("session")
    if session:
        session.close()
    return [], {}, "*Session reset. Start a new conversation!*"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

body, .gradio-container {
    background: #0d0d14 !important;
    color: #e8e8f0 !important;
}

.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.06);
}

.main-header h1 {
    font-size: 2.4em;
    font-weight: 700;
    background: linear-gradient(90deg, #e040fb, #7c4dff, #40c4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 6px 0;
}

.main-header p {
    color: #888;
    margin: 0;
    font-size: 1.05em;
}

/* Chat bubbles */
.message.user-message {
    background: linear-gradient(135deg, #7c4dff22, #7c4dff11) !important;
    border: 1px solid #7c4dff44 !important;
    border-radius: 14px !important;
}

.message.bot-message {
    background: #1a1a2e !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
}

/* Side panel */
.side-panel {
    background: #1a1a2e;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.06);
}

.side-panel h3 {
    color: #e040fb;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 0 0 12px 0;
}

/* Buttons */
.send-btn {
    background: linear-gradient(135deg, #7c4dff, #e040fb) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    color: white !important;
}

.reset-btn {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #aaa !important;
}

.quick-btn {
    background: rgba(124,77,255,0.15) !important;
    border: 1px solid rgba(124,77,255,0.3) !important;
    border-radius: 20px !important;
    font-size: 0.85em !important;
    color: #c4b5ff !important;
    margin: 2px !important;
    padding: 4px 12px !important;
}

.quick-btn:hover {
    background: rgba(124,77,255,0.3) !important;
}

/* Textbox */
.textbox-input textarea {
    background: #1a1a2e !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #e8e8f0 !important;
    font-size: 15px !important;
    resize: none !important;
}

/* Chatbot */
.chatbot {
    background: #0d0d14 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
}

/* Status badge */
.status-badge {
    display: inline-block;
    background: rgba(64,196,255,0.15);
    border: 1px solid rgba(64,196,255,0.3);
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 12px;
    color: #40c4ff;
    margin-top: 8px;
}

.footer-text {
    text-align: center;
    color: #444;
    font-size: 12px;
    margin-top: 20px;
    padding: 12px;
}

/* Markdown profile */
.profile-md p, .profile-md strong {
    color: #c4b5ff !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}
"""

MOOD_PRESETS = [
    ("😴 Cozy Night", "I feel sleepy and want something cozy and comforting"),
    ("😂 Need Laughs", "I want something funny that will make me laugh out loud"),
    ("💕 Date Night", "Looking for something romantic for a date night"),
    ("🚀 Mind-Blowing", "I want an epic, mind-blowing sci-fi or thriller"),
    ("😱 Get Spooked", "I love horror — give me something terrifying"),
    ("🎭 Feel Deeply", "I want something emotional and meaningful"),
    ("🍿 Just Trending", "Show me what's popular right now"),
    ("🌍 World Cinema", "Recommend something from international cinema"),
]


def build_app() -> gr.Blocks:
    with gr.Blocks(title="CineMatch — AI Movie Advisor") as app:

        # ── Header ─────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="main-header">
            <h1>🎬 CineMatch</h1>
            <p>Your personal AI movie advisor — powered by Azure AI Agents & live TMDb data</p>
            <span class="status-badge">● Live</span>
        </div>
        """)

        with gr.Row(equal_height=True):
            # ── Chat Panel ─────────────────────────────────────────────────
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    elem_classes=["chatbot"],
                    height=520,
                    show_label=False,
                    avatar_images=(None, "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=cinematch"),
                    render_markdown=True,
                )

                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Tell me your mood, a genre, or a movie you loved…",
                        show_label=False,
                        lines=1,
                        max_lines=3,
                        elem_classes=["textbox-input"],
                        scale=5,
                    )
                    send_btn = gr.Button("Send ➤", elem_classes=["send-btn"], scale=1, min_width=80)

                # Quick mood presets
                gr.Markdown("**✨ Quick picks:**", elem_id="quick-label")
                with gr.Row(elem_id="quick-row"):
                    for label, prompt in MOOD_PRESETS:
                        b = gr.Button(label, elem_classes=["quick-btn"], size="sm")
                        b.click(lambda p=prompt: p, outputs=msg_box)

            # ── Side Panel ─────────────────────────────────────────────────
            with gr.Column(scale=1, min_width=220):
                gr.HTML('<div class="side-panel"><h3>🧠 Your Profile</h3></div>')
                profile_md = gr.Markdown(
                    "*Start chatting to build your profile!*",
                    elem_classes=["profile-md"],
                )

                gr.HTML("<br>")

                gr.HTML('<div class="side-panel"><h3>⚡ Actions</h3></div>')
                reset_btn = gr.Button("🔄 New Session", elem_classes=["reset-btn"], size="sm")
                gr.HTML("""
                <div style="margin-top:16px;color:#555;font-size:12px;line-height:1.6">
                    <strong style="color:#666">Tips:</strong><br>
                    • Tell me movies you loved<br>
                    • Say genres you like/hate<br>
                    • Mention a decade or year<br>
                    • Ask for trending picks
                </div>
                """)

        # ── Footer ─────────────────────────────────────────────────────────
        gr.HTML("""
        <div class="footer-text">
            CineMatch · Powered by Azure AI Agents · TMDb API · Built with Gradio<br>
            Movie data provided by <a href="https://www.themoviedb.org" style="color:#555">TMDb</a>
        </div>
        """)

        # ── State ──────────────────────────────────────────────────────────
        session_state = gr.State({})

        # ── Event handlers ─────────────────────────────────────────────────
        def _submit(message, history, state):
            if not message.strip():
                return "", history, state, profile_md.value
            return chat(message, history, state)

        send_btn.click(
            fn=_submit,
            inputs=[msg_box, chatbot, session_state],
            outputs=[msg_box, chatbot, session_state, profile_md],
        )
        msg_box.submit(
            fn=_submit,
            inputs=[msg_box, chatbot, session_state],
            outputs=[msg_box, chatbot, session_state, profile_md],
        )
        reset_btn.click(
            fn=reset_session,
            inputs=[session_state],
            outputs=[chatbot, session_state, profile_md],
        )

        # Auto-greet on page load
        app.load(
            fn=lambda: ([], {}, "*Start chatting to build your profile!*"),
            outputs=[chatbot, session_state, profile_md],
        )

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")

    if CONFIG_ERROR:
        print(f"\n⚠️  {CONFIG_ERROR}\n")
    if not TMDB_API_KEY:
        print("⚠️  TMDB_API_KEY not set — live movie search will not return results")
        print("    Get a free key at: https://www.themoviedb.org/settings/api\n")

    print("🎬 Launching CineMatch SaaS App…")
    print("   http://127.0.0.1:7860\n")

    build_app().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(),
    )