"""
Movie Night AI Advisor — Enhanced Edition with Real-Time Search
==============================================================
Features:
  ✦ Live movie search via TMDb API (real-time, by popularity/year/genre)
  ✦ UserProfile schema to capture preferences interactively
  ✦ Multi-genre support
  ✦ "Movies you might like" similarity-based recommendations
  ✦ Tracks movies you've watched / liked / disliked
  ✦ Multi-turn conversation — agent asks preference questions
  ✦ FunctionTool with auto-execution

Requirements:
    pip install requests python-dotenv azure-ai-agents azure-identity

Environment (.env):
    PROJECT_ENDPOINT      — Azure AI Foundry project endpoint
    MODEL_DEPLOYMENT_NAME — Your model deployment name
    TMDB_API_KEY          — Get free key from https://www.themoviedb.org/settings/api

Usage:
    python movie-advisor.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import requests
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
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()
PROJECT_ENDPOINT    = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT    = os.getenv("MODEL_DEPLOYMENT_NAME", "")
TMDB_API_KEY        = os.getenv("TMDB_API_KEY", "")
TMDB_BASE           = "https://api.themoviedb.org/3"

# TMDb genre name → ID map (for quick lookup)
TMDB_GENRE_MAP: dict[str, int] = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}


# ---------------------------------------------------------------------------
# User Profile Schema
# ---------------------------------------------------------------------------
@dataclass
class UserProfile:
    """Captures user movie preferences across the session."""
    fav_genres:       list[str]  = field(default_factory=list)
    disliked_genres:  list[str]  = field(default_factory=list)
    preferred_years:  list[int]  = field(default_factory=list)   # e.g. [2015, 2024]
    min_rating:       float       = 6.0
    watched_movies:   list[str]  = field(default_factory=list)   # titles user already saw
    liked_movies:     list[str]  = field(default_factory=list)   # titles user enjoyed
    disliked_movies:  list[str]  = field(default_factory=list)
    mood:             str         = ""
    languages:        list[str]  = field(default_factory=lambda: ["en"])

    def to_context_string(self) -> str:
        parts = []
        if self.fav_genres:
            parts.append(f"Favourite genres: {', '.join(self.fav_genres)}")
        if self.disliked_genres:
            parts.append(f"Dislikes: {', '.join(self.disliked_genres)}")
        if self.preferred_years:
            yr = self.preferred_years
            parts.append(f"Preferred era: {min(yr)}–{max(yr)}")
        if self.liked_movies:
            parts.append(f"Movies they loved: {', '.join(self.liked_movies[:5])}")
        if self.watched_movies:
            parts.append(f"Already watched: {', '.join(self.watched_movies[:10])}")
        if self.mood:
            parts.append(f"Current mood: {self.mood}")
        return "\n".join(parts) if parts else "No profile yet."


# Global profile (shared across functions called by the agent)
user_profile = UserProfile()


# ---------------------------------------------------------------------------
# TMDb helpers
# ---------------------------------------------------------------------------
def _tmdb_get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to TMDb. Raises on error."""
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is missing. Add it to your .env file.")
    base_params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        base_params.update(params)
    resp = requests.get(f"{TMDB_BASE}{path}", params=base_params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _format_movie(m: dict) -> dict:
    """Extract the fields we care about from a TMDb movie dict."""
    return {
        "title":       m.get("title", "Unknown"),
        "year":        (m.get("release_date") or "")[:4] or "N/A",
        "rating":      round(m.get("vote_average", 0), 1),
        "votes":       m.get("vote_count", 0),
        "overview":    (m.get("overview") or "")[:200],
        "genres":      m.get("genre_ids", []),           # IDs — resolved by agent
        "popularity":  round(m.get("popularity", 0), 1),
    }


# ---------------------------------------------------------------------------
# Agent-callable Functions
# ---------------------------------------------------------------------------
def search_movies(
    genres: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    min_rating: float = 6.0,
    sort_by: str = "popularity.desc",
    limit: int = 8,
) -> str:
    """
    Search TMDb for movies matching genre(s), year range, and rating threshold.

    Args:
        genres:     List of genre names (e.g. ["comedy", "sci-fi"]).
        year_from:  Earliest release year (inclusive).
        year_to:    Latest release year (inclusive).
        min_rating: Minimum TMDb average rating (0–10).
        sort_by:    TMDb sort field. Options: "popularity.desc", "vote_average.desc",
                    "release_date.desc", "revenue.desc".
        limit:      Max results to return (max 20).

    Returns:
        JSON string with a list of matching movies.
    """
    genre_ids: list[str] = []
    if genres:
        for g in genres:
            gid = TMDB_GENRE_MAP.get(g.lower().strip())
            if gid:
                genre_ids.append(str(gid))

    params: dict[str, Any] = {
        "sort_by": sort_by,
        "vote_count.gte": 200,
        "vote_average.gte": min_rating,
    }
    if genre_ids:
        params["with_genres"] = ",".join(genre_ids)
    if year_from:
        params["primary_release_date.gte"] = f"{year_from}-01-01"
    if year_to:
        params["primary_release_date.lte"] = f"{year_to}-12-31"

    try:
        data   = _tmdb_get("/discover/movie", params)
        movies = [_format_movie(m) for m in data.get("results", [])[:limit]]
        # Filter out anything the user already watched
        watched_lower = [w.lower() for w in user_profile.watched_movies]
        movies = [m for m in movies if m["title"].lower() not in watched_lower]
        return json.dumps({"movies": movies, "total_found": data.get("total_results", 0)})
    except Exception as e:
        logger.error("search_movies error: %s", e)
        return json.dumps({"error": str(e), "movies": []})


def get_similar_movies(movie_title: str, limit: int = 6) -> str:
    """
    Find movies similar to a title the user enjoyed.

    Args:
        movie_title: Title of a movie the user liked.
        limit:       Number of recommendations to return.

    Returns:
        JSON string with similar movie recommendations.
    """
    try:
        # First search for the movie to get its ID
        search = _tmdb_get("/search/movie", {"query": movie_title, "include_adult": False})
        results = search.get("results", [])
        if not results:
            return json.dumps({"error": f"Could not find '{movie_title}'", "movies": []})

        movie_id = results[0]["id"]
        data     = _tmdb_get(f"/movie/{movie_id}/similar")
        watched_lower = [w.lower() for w in user_profile.watched_movies]
        movies = [
            _format_movie(m)
            for m in data.get("results", [])[:limit * 2]
            if m.get("vote_count", 0) > 50
        ]
        # Filter already watched
        movies = [m for m in movies if m["title"].lower() not in watched_lower][:limit]
        return json.dumps({"based_on": results[0]["title"], "movies": movies})
    except Exception as e:
        logger.error("get_similar_movies error: %s", e)
        return json.dumps({"error": str(e), "movies": []})


def get_trending_movies(time_window: str = "week", limit: int = 8) -> str:
    """
    Fetch currently trending movies from TMDb.

    Args:
        time_window: "day" or "week".
        limit:       Number of results.

    Returns:
        JSON string with trending movies.
    """
    try:
        data   = _tmdb_get(f"/trending/movie/{time_window}")
        movies = [_format_movie(m) for m in data.get("results", [])[:limit]]
        return json.dumps({"time_window": time_window, "movies": movies})
    except Exception as e:
        logger.error("get_trending_movies error: %s", e)
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
    Update the user's preference profile with new information gathered from the conversation.

    Args:
        fav_genres:      List of genre names the user enjoys.
        disliked_genres: Genres the user dislikes.
        year_from:       Start of preferred release year range.
        year_to:         End of preferred release year range.
        liked_movies:    Movie titles the user has enjoyed.
        watched_movies:  Movie titles the user has already seen.
        disliked_movies: Movie titles the user disliked.
        mood:            User's current mood.
        min_rating:      Minimum acceptable TMDb rating.

    Returns:
        JSON string confirming the update.
    """
    global user_profile
    if fav_genres:
        user_profile.fav_genres = list(set(user_profile.fav_genres + fav_genres))
    if disliked_genres:
        user_profile.disliked_genres = list(set(user_profile.disliked_genres + disliked_genres))
    if year_from or year_to:
        yr_range = list(range(year_from or 1980, (year_to or 2025) + 1))
        user_profile.preferred_years = yr_range
    if liked_movies:
        user_profile.liked_movies = list(set(user_profile.liked_movies + liked_movies))
    if watched_movies:
        user_profile.watched_movies = list(set(user_profile.watched_movies + watched_movies))
    if disliked_movies:
        user_profile.disliked_movies = list(set(user_profile.disliked_movies + disliked_movies))
    if mood:
        user_profile.mood = mood
    if min_rating is not None:
        user_profile.min_rating = float(min_rating)

    return json.dumps({"status": "profile_updated", "profile": {
        "fav_genres":      user_profile.fav_genres,
        "disliked_genres": user_profile.disliked_genres,
        "liked_movies":    user_profile.liked_movies,
        "watched_count":   len(user_profile.watched_movies),
        "mood":            user_profile.mood,
    }})


def get_user_profile() -> str:
    """Return the current user preference profile as JSON."""
    return json.dumps({
        "fav_genres":      user_profile.fav_genres,
        "disliked_genres": user_profile.disliked_genres,
        "preferred_years": f"{min(user_profile.preferred_years, default=1980)}–{max(user_profile.preferred_years, default=2025)}" if user_profile.preferred_years else "any",
        "min_rating":      user_profile.min_rating,
        "liked_movies":    user_profile.liked_movies,
        "disliked_movies": user_profile.disliked_movies,
        "watched_movies":  user_profile.watched_movies,
        "mood":            user_profile.mood,
    })


# Register all callable functions for the agent
AGENT_FUNCTIONS: set = {
    search_movies,
    get_similar_movies,
    get_trending_movies,
    update_user_profile,
    get_user_profile,
}


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
def load_config() -> dict:
    missing = []
    if not PROJECT_ENDPOINT:
        missing.append("PROJECT_ENDPOINT")
    if not MODEL_DEPLOYMENT:
        missing.append("MODEL_DEPLOYMENT_NAME")
    if not TMDB_API_KEY:
        logger.warning(
            "TMDB_API_KEY not set. Live movie search will be unavailable. "
            "Get a free key at https://www.themoviedb.org/settings/api"
        )
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)
    return {"endpoint": PROJECT_ENDPOINT, "model": MODEL_DEPLOYMENT}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are "CineMatch" — an expert, friendly movie recommendation AI with access to real-time movie data via function tools.

YOUR WORKFLOW:
1. Start with a warm greeting and ask 3-4 discovery questions to learn the user's preferences:
   - What genres do they enjoy? (be open to multiple)
   - What era/decade do they prefer?
   - A few movies they've loved and a few they've seen recently
   - Their current mood/vibe
   
2. Call update_user_profile() to record what you learn.

3. Use search_movies() with their genre preferences, year range, and rating threshold.

4. Use get_similar_movies() for movies they mentioned liking.

5. Use get_trending_movies() to add current popular options.

6. Filter out movies they've already watched.

7. Present a curated, personalized list with titles, years, ratings, and WHY each fits them.

IMPORTANT RULES:
- Ask follow-up questions naturally during conversation — don't bombard with a form.
- Always call update_user_profile when you learn something new about preferences.
- If user mentions a movie they've seen, add it to watched_movies.
- If user says they loved something, add it to liked_movies and call get_similar_movies.
- Support multiple genres per search.
- Be warm, enthusiastic, and explain your reasoning for each recommendation.
- Always filter out movies the user has already watched.
- Present at least 5 recommendations per response, sorted by likely fit.
"""


def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    config = load_config()

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    client = AgentsClient(endpoint=config["endpoint"], credential=credential)

    try:
        with client:
            agent_id: str | None = None
            try:
                # Register function tools
                functions = FunctionTool(AGENT_FUNCTIONS)
                toolset   = ToolSet()
                toolset.add(functions)
                client.enable_auto_function_calls(toolset)

                # Create agent
                agent = client.create_agent(
                    model=config["model"],
                    name="cinematch-advisor",
                    instructions=SYSTEM_PROMPT,
                    toolset=toolset,
                )
                agent_id = agent.id
                logger.info("CineMatch agent created: %s", agent.id)

                thread = client.threads.create()
                logger.info("Thread created: %s", thread.id)

                print("\n" + "═" * 55)
                print("  🎬  CineMatch — Personalized Movie Advisor  🎬")
                print("  Powered by Azure AI Agents + TMDb Live Data")
                print("═" * 55)
                print("  Type 'quit' to exit | 'profile' to see your profile")
                print("═" * 55 + "\n")

                # Kick off with the agent's greeting
                client.messages.create(
                    thread_id=thread.id,
                    role=MessageRole.USER,
                    content="Hello! I'd love some movie recommendations.",
                )
                run = client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent.id,
                )
                if run.status != "failed":
                    last = client.messages.get_last_message_text_by_role(
                        thread_id=thread.id, role=MessageRole.AGENT
                    )
                    if last:
                        print(f"CineMatch: {last.text.value}\n")

                # Conversation loop
                while True:
                    try:
                        user_input = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nGoodbye!")
                        break

                    if user_input.lower() in ("quit", "exit", "q"):
                        print(
                            "\n🎬 Thanks for using CineMatch! Enjoy your movie night!\n"
                        )
                        break

                    if user_input.lower() == "profile":
                        print("\n── Your Profile ──────────────────────────────")
                        print(user_profile.to_context_string())
                        print("──────────────────────────────────────────────\n")
                        continue

                    if not user_input:
                        continue

                    client.messages.create(
                        thread_id=thread.id,
                        role=MessageRole.USER,
                        content=user_input,
                    )

                    print("\n🔍 Searching...\n")
                    run = client.runs.create_and_process(
                        thread_id=thread.id,
                        agent_id=agent.id,
                    )

                    if run.status == "failed":
                        logger.error("Run failed: %s", run.last_error)
                        print(f"\n❌ Error: {run.last_error}\n")
                        continue

                    last = client.messages.get_last_message_text_by_role(
                        thread_id=thread.id, role=MessageRole.AGENT
                    )
                    if last:
                        print(f"CineMatch: {last.text.value}\n")

                # Final profile summary
                if user_profile.fav_genres or user_profile.liked_movies:
                    print("\n── Session Summary ───────────────────────────")
                    print(user_profile.to_context_string())
                    print("──────────────────────────────────────────────\n")

            finally:
                if agent_id:
                    try:
                        client.delete_agent(agent_id)
                        logger.info("Agent deleted.")
                    except AzureError as e:
                        logger.warning("Could not delete agent: %s", e)

    except HttpResponseError as e:
        logger.error("Azure API error [%s]: %s", e.status_code, e.message)
        if e.status_code == 404:
            logger.error("Check that PROJECT_ENDPOINT is your Azure AI Foundry project endpoint.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")


if __name__ == "__main__":
    main()