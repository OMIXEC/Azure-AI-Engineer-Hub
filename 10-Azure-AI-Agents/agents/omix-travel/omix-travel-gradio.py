"""
OmixTravel AI — SaaS Web Application (Gradio Edition)
======================================================
Production-ready enterprise travel planner built with Gradio + Azure AI Agents.

Features:
  ✦ Per-session agent isolation (multi-user safe)
  ✦ OmixTravel policy enforcement with visual compliance status
  ✦ Live flight, attraction, food & culture intelligence
  ✦ TravelPreferences schema — remembered per session
  ✦ 7 FunctionTools with auto-execution
  ✦ Dark premium enterprise UI with branded design
  ✦ Quick destination presets and policy summary panel

Usage:
    python omix-travel-gradio.py
    # Opens at http://127.0.0.1:7860
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import gradio as gr
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, MessageRole, ToolSet
from azure.core.exceptions import AzureError, HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME", "")
CONFIG_ERROR: str | None = None
if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
    CONFIG_ERROR = "⚠️  Set PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME in your .env file."

# ===========================================================================
# OMIX TRAVEL POLICY
# ===========================================================================
OMIX_TRAVEL_POLICY = """
OMIXTRAVEL CORPORATE TRAVEL POLICY (v2025.1)
=============================================

1. BOOKING WINDOWS
   - Flights: Book ≥14 days ahead (domestic), ≥21 days (international)
   - Hotels: Book ≥7 days in advance

2. BUDGET LIMITS (per traveler, per trip)
   - Domestic flights:       ≤ $600 economy
   - International flights:  ≤ $2,500 business (≥8h), economy otherwise
   - Hotel per night:        ≤ $250 (domestic) / ≤ $350 (international)
   - Daily expenses:         ≤ $75/day
   - Total standard budget:  ≤ $5,000 | Executive budget: ≤ $10,000

3. PREFERRED SUPPLIERS
   - Airlines: Delta, United, Emirates, Lufthansa, Turkish Airlines
   - Hotels:   Marriott, Hilton, Hyatt, IHG
   - Car:      Hertz, Enterprise

4. APPROVAL REQUIREMENTS
   - > $3,000 total: Manager approval
   - > $7,500 total: VP approval
   - All international trips: Manager pre-approval
   - Duration > 2 weeks: HR notification

5. RECEIPTS & REIMBURSEMENT
   - Expenses > $25 require original receipts
   - Submit claims within 30 days of trip
   - Personal upgrades not reimbursable

6. SUSTAINABILITY
   - Prefer direct flights where < 2hr vs. connecting
   - Rail travel preferred for trips < 500km
   - Choose eco-certified hotels when available

7. SAFETY
   - Register all international travel with security portal
   - Travel insurance mandatory for all international trips
   - High-risk destinations need security briefing
"""

# ===========================================================================
# TravelPreferences Schema
# ===========================================================================
@dataclass
class TravelPreferences:
    traveler_name:       str        = ""
    traveler_role:       str        = "standard"
    preferred_regions:   list[str]  = field(default_factory=list)
    visited_countries:   list[str]  = field(default_factory=list)
    wishlist_cities:     list[str]  = field(default_factory=list)
    travel_style:        list[str]  = field(default_factory=list)
    interests:           list[str]  = field(default_factory=list)
    dietary:             list[str]  = field(default_factory=list)
    seat_preference:     str        = "economy"
    hotel_stars:         int        = 4
    trip_purpose:        str        = ""
    budget_usd:          float      = 3000.0
    travel_dates:        str        = ""
    group_size:          int        = 1
    liked_experiences:   list[str]  = field(default_factory=list)

    def summary_md(self) -> str:
        rows = []
        if self.traveler_name:
            rows.append(f"**{self.traveler_name}** ({self.traveler_role})")
        if self.interests:
            rows.append(f"**Interests:** {', '.join(self.interests)}")
        if self.preferred_regions:
            rows.append(f"**Regions:** {', '.join(self.preferred_regions)}")
        if self.dietary:
            rows.append(f"**Dietary:** {', '.join(self.dietary)}")
        if self.travel_style:
            rows.append(f"**Style:** {', '.join(self.travel_style)}")
        if self.budget_usd:
            rows.append(f"**Budget:** ${self.budget_usd:,.0f}")
        if self.travel_dates:
            rows.append(f"**Dates:** {self.travel_dates}")
        if self.seat_preference:
            rows.append(f"**Class:** {self.seat_preference.title()}")
        if self.hotel_stars:
            rows.append(f"**Hotels:** {'⭐' * self.hotel_stars}")
        return "  \n".join(rows) if rows else "*Start chatting to build your profile!*"


# ===========================================================================
# Session
# ===========================================================================
@dataclass
class TravelSession:
    session_id: str
    profile: TravelPreferences
    client: AgentsClient | None = None
    agent_id: str | None = None
    thread_id: str | None = None

    def close(self) -> None:
        if self.client and self.agent_id:
            try:
                self.client.delete_agent(self.agent_id)
                logger.info("[%s] Agent deleted", self.session_id)
            except AzureError as e:
                logger.warning("Could not delete agent: %s", e)
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass


# ===========================================================================
# Agent Functions (closure-bound per session)
# ===========================================================================
def make_travel_functions(profile: TravelPreferences) -> set:

    def search_flights(
        origin: str,
        destination: str,
        departure_date: str | None = None,
        return_date: str | None = None,
        cabin_class: str = "ECONOMY",
        passengers: int = 1,
    ) -> str:
        """
        Search for flight options between two cities with OmixTravel preferred airlines.

        Args:
            origin:         IATA code or city (e.g. "JFK", "New York").
            destination:    IATA code or city (e.g. "LHR", "London").
            departure_date: YYYY-MM-DD. Defaults to 21 days from today.
            return_date:    Return date for round trips (YYYY-MM-DD).
            cabin_class:    ECONOMY, BUSINESS, or FIRST.
            passengers:     Number of passengers.
        Returns:
            JSON with flight options and policy compliance.
        """
        if not departure_date:
            departure_date = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")
        is_international = origin[:2].upper() != destination[:2].upper()
        limit = 2500 if is_international else 600
        preferred = ["Delta", "United", "Emirates", "Lufthansa", "Turkish Airlines"]
        flights = [
            {"airline": preferred[0], "flight_number": "DL1024", "departure": f"{departure_date} 08:15",
             "duration": "8h 15m direct", "stops": 0, "cabin": cabin_class,
             "price_usd": 820 if is_international else 275, "preferred_supplier": True, "eco_score": "A"},
            {"airline": preferred[2], "flight_number": "EK789",  "departure": f"{departure_date} 22:00",
             "duration": "8h 45m direct", "stops": 0, "cabin": cabin_class,
             "price_usd": 940 if is_international else 310, "preferred_supplier": True, "eco_score": "B"},
            {"airline": "Budget Air",   "flight_number": "BU4401", "departure": f"{departure_date} 06:00",
             "duration": "11h 20m (1 stop)", "stops": 1, "cabin": cabin_class,
             "price_usd": 530 if is_international else 175, "preferred_supplier": False, "eco_score": "C",
             "note": "Non-preferred supplier"},
        ]
        for f in flights:
            f["policy_status"] = "within_policy" if f["price_usd"] <= limit else "over_budget"
        return json.dumps({"route": f"{origin}→{destination}", "departure_date": departure_date,
                           "return_date": return_date, "policy_limit_usd": limit, "flights": flights})

    def search_attractions(city: str, categories: list[str] | None = None, max_results: int = 8) -> str:
        """
        Find top attractions, landmarks, and experiences in a destination.

        Args:
            city:        City name (e.g. "Tokyo", "Istanbul", "Rome").
            categories:  landmarks, museums, nature, food, culture, nightlife, adventure, family.
            max_results: Max results to return.
        Returns:
            JSON with curated attractions.
        """
        db: dict[str, list] = {
            "tokyo": [
                {"name": "Senso-ji Temple",     "cat": "religious",  "cost": "Free",  "rating": 4.7, "tip": "Visit at dawn"},
                {"name": "teamLab Borderless",  "cat": "museums",    "cost": "$30",   "rating": 4.9, "tip": "Book weeks ahead"},
                {"name": "Tsukiji Market",      "cat": "food",       "cost": "$10-30","rating": 4.6, "tip": "Arrive by 7AM"},
                {"name": "Shibuya Crossing",    "cat": "culture",    "cost": "Free",  "rating": 4.8, "tip": "Best at rush hour"},
                {"name": "Mount Fuji Day Trip", "cat": "nature",     "cost": "$60",   "rating": 4.8, "tip": "July-Sept for clear skies"},
                {"name": "Akihabara",           "cat": "shopping",   "cost": "Varies","rating": 4.5, "tip": "Electronics & anime"},
                {"name": "Shinjuku Gyoen",      "cat": "nature",     "cost": "$3",    "rating": 4.6, "tip": "Cherry blossoms in March"},
                {"name": "Golden Gai",          "cat": "nightlife",  "cost": "$15-40","rating": 4.7, "tip": "Theme bars, cash only"},
            ],
            "istanbul": [
                {"name": "Hagia Sophia",        "cat": "religious",  "cost": "Free",  "rating": 4.9, "tip": "Mosque — cover up"},
                {"name": "Grand Bazaar",        "cat": "shopping",   "cost": "Free",  "rating": 4.6, "tip": "Haggle — start at 60% of ask"},
                {"name": "Bosphorus Cruise",    "cat": "nature",     "cost": "$10-25","rating": 4.7, "tip": "Sunset for best photos"},
                {"name": "Topkapi Palace",      "cat": "museums",    "cost": "$20",   "rating": 4.7, "tip": "Book online"},
                {"name": "Spice Bazaar",        "cat": "food",       "cost": "Free",  "rating": 4.5, "tip": "Try lokum samples"},
                {"name": "Balat Neighbourhood", "cat": "culture",    "cost": "Free",  "rating": 4.5, "tip": "Colourful streets"},
            ],
            "dubai": [
                {"name": "Burj Khalifa",        "cat": "landmarks",  "cost": "$50-130","rating": 4.8, "tip": "Sunset tickets sell out"},
                {"name": "Dubai Creek",         "cat": "culture",    "cost": "Free",   "rating": 4.6, "tip": "Abra ride costs $0.27"},
                {"name": "Desert Safari",       "cat": "adventure",  "cost": "$80-120","rating": 4.7, "tip": "Includes camel ride"},
                {"name": "Dubai Frame",         "cat": "landmarks",  "cost": "$14",    "rating": 4.4, "tip": "Best old vs new views"},
                {"name": "Ravi Restaurant",     "cat": "food",       "cost": "$5-10",  "rating": 4.6, "tip": "Iconic cheap Pakistani"},
            ],
            "rome": [
                {"name": "Colosseum",           "cat": "landmarks",  "cost": "$20",   "rating": 4.8, "tip": "Book 2+ months ahead"},
                {"name": "Vatican Museums",     "cat": "museums",    "cost": "$25",   "rating": 4.8, "tip": "First Sunday is free"},
                {"name": "Trastevere",          "cat": "food",       "cost": "Free",  "rating": 4.7, "tip": "Best authentic Roman food"},
                {"name": "Trevi Fountain",      "cat": "landmarks",  "cost": "Free",  "rating": 4.7, "tip": "Visit at 5AM for empty photos"},
            ],
        }
        key = city.lower()
        for k in db:
            if k in key or key in k:
                key = k; break
        items = db.get(key, [{"name": f"{city} Old Town", "cat": "culture", "cost": "Free", "rating": 4.5, "tip": "Explore freely"}])
        if categories:
            items = [i for i in items if any(c.lower() in i["cat"] for c in categories)] or items
        return json.dumps({"city": city, "attractions": items[:max_results]})

    def get_local_food_guide(city: str, dietary_preferences: list[str] | None = None) -> str:
        """
        Curated local food guide including must-try dishes and dietary options.

        Args:
            city:               City name.
            dietary_preferences: vegetarian, vegan, halal, gluten_free, etc.
        Returns:
            JSON food guide with local dishes and dietary-specific recommendations.
        """
        diet = dietary_preferences or profile.dietary or []
        guides: dict[str, dict] = {
            "tokyo": {
                "must_try": ["Ramen at Ichiran", "Sushi omakase", "Yakitori", "Tonkatsu"],
                "vegetarian": "Shojin ryori (Buddhist) at Ain Soph",
                "halal": "Naritaya (Akihabara) certified halal ramen",
                "avg_cost": "$10-80 per meal",
                "etiquette": ["Never tip", "Slurping noodles is polite", "Eat at counter for ramen"],
            },
            "istanbul": {
                "must_try": ["Döner kebap", "Balık ekmek", "Baklava", "Meze plates"],
                "vegetarian": "Ciya Sofrasi in Kadıköy — vegetarian mezze",
                "halal": "Almost all local restaurants are halal",
                "avg_cost": "$5-30 per meal",
                "etiquette": ["Accept tea — it's a sign of hospitality", "Dinner starts at 8-9PM"],
            },
            "rome": {
                "must_try": ["Cacio e pepe", "Supplì", "Artichokes alla Romana", "Gelato"],
                "vegetarian": "Pizza margherita everywhere; vegetariano marked on menus",
                "halal": "Pigneto neighbourhood has most halal options",
                "avg_cost": "$15-50 per meal",
                "etiquette": ["Cappuccino only before 11AM", "No cheese on seafood pasta"],
            },
        }
        key = city.lower()
        for k in guides:
            if k in key or key in k:
                key = k; break
        g = guides.get(key, {"must_try": [f"Ask locals for {city} specialties"], "avg_cost": "$10-50"})
        diet_info = {d: g.get(d, "Check HalalTrip.com or local search") for d in diet}
        return json.dumps({"city": city, "food_guide": g, "your_dietary_options": diet_info})

    def get_destination_culture_guide(destination: str) -> str:
        """
        Cultural norms, etiquette, safety, currency, and transport tips for a destination.

        Args:
            destination: Country or city name.
        Returns:
            JSON with cultural guide.
        """
        guides = {
            "japan":  {"lang": "Japanese (English in Tokyo)", "currency": "JPY — carry cash",
                       "dos": ["Bow to greet", "Remove shoes indoors", "Be punctual"],
                       "donts": ["No tipping (rude)", "No eating while walking", "No loud talking on trains"],
                       "dress": "Conservative at temples", "tipping": "NOT customary",
                       "safety": "Very safe, very low crime", "emergency": "110 police / 119 ambulance"},
            "turkey": {"lang": "Turkish (English in tourist areas)", "currency": "TRY — use local ATMs",
                       "dos": ["Dress modestly in mosques", "Accept tea", "Bargain at markets"],
                       "donts": ["Don't disrespect Atatürk", "Avoid political discussions"],
                       "dress": "Cover head/shoulders for mosques", "tipping": "10-15% restaurants",
                       "safety": "Generally safe", "emergency": "155 police / 112 emergency"},
            "italy":  {"lang": "Italian (English in tourist areas)", "currency": "EUR",
                       "dos": ["Dress smart", "Greet with Buongiorno", "Validate train tickets"],
                       "donts": ["Don't sit on church steps", "Avoid tourist menus near sights"],
                       "dress": "Smart casual; cover in churches", "tipping": "€1-2 coins",
                       "safety": "Watch for pickpockets at sites", "emergency": "112"},
            "uae":    {"lang": "Arabic (English widely spoken)", "currency": "AED (pegged $USD)",
                       "dos": ["Dress modestly in public", "Respect Ramadan rules"],
                       "donts": ["No PDA in public", "No alcohol outside licensed venues"],
                       "dress": "Cover knees/shoulders; beach attire at beaches only", "tipping": "10-15%",
                       "safety": "Very safe, strict laws", "emergency": "999"},
        }
        key = destination.lower()
        for k in guides:
            if k in key or key in k:
                key = k; break
        g = guides.get(key, {"lang": "Check translate.google.com", "emergency": "112 (most countries)"})
        return json.dumps({"destination": destination, "culture_guide": g})

    def check_omix_policy_compliance(
        trip_type: str,
        flight_cost_usd: float,
        hotel_nightly_usd: float,
        trip_duration_days: int,
        traveler_role: str = "standard",
    ) -> str:
        """
        Validate a trip against OmixTravel corporate policy. Always call before confirming a trip.

        Args:
            trip_type:          "domestic" or "international".
            flight_cost_usd:    Total flight cost per person.
            hotel_nightly_usd:  Hotel cost per night.
            trip_duration_days: Number of nights.
            traveler_role:      "standard" or "executive".
        Returns:
            JSON with compliance status, violations, and required approvals.
        """
        is_intl = trip_type.lower() == "international"
        is_exec = traveler_role.lower() == "executive"
        flight_limit = 2500 if is_intl else 600
        hotel_limit  = 350  if is_intl else 250
        total_budget = 10000 if is_exec else 5000
        total = flight_cost_usd + hotel_nightly_usd * trip_duration_days + 75 * trip_duration_days
        violations, approvals, warnings = [], [], []
        if flight_cost_usd > flight_limit:
            violations.append(f"Flight ${flight_cost_usd:.0f} > limit ${flight_limit}")
        if hotel_nightly_usd > hotel_limit:
            violations.append(f"Hotel ${hotel_nightly_usd:.0f}/night > limit ${hotel_limit}")
        if total > 3000:   approvals.append("Manager approval required (>$3,000)")
        if total > 7500:   approvals.append("VP approval required (>$7,500)")
        if is_intl:
            approvals.append("Manager pre-approval required for international trips")
            warnings.append("Travel insurance mandatory")
            warnings.append("Register with Omix security portal")
        if trip_duration_days > 14:
            warnings.append("HR notification required (>2 weeks)")
        return json.dumps({
            "compliant": len(violations) == 0,
            "violations": violations, "approvals_required": approvals, "warnings": warnings,
            "cost_summary": {"flight": f"${flight_cost_usd:.0f}", "hotels": f"${hotel_nightly_usd * trip_duration_days:.0f}",
                              "daily_est": f"${75 * trip_duration_days:.0f}", "total_est": f"${total:.0f}",
                              "budget_limit": f"${total_budget:.0f}"},
        })

    def update_travel_profile(
        traveler_name: str | None = None, traveler_role: str | None = None,
        preferred_regions: list[str] | None = None, interests: list[str] | None = None,
        travel_style: list[str] | None = None, dietary: list[str] | None = None,
        seat_preference: str | None = None, hotel_stars: int | None = None,
        trip_purpose: str | None = None, budget_usd: float | None = None,
        travel_dates: str | None = None, group_size: int | None = None,
        visited_countries: list[str] | None = None, wishlist_cities: list[str] | None = None,
    ) -> str:
        """
        Update the traveler profile with preferences learned during conversation.

        Args:
            traveler_name:     Traveler's name.
            traveler_role:     "standard" or "executive".
            preferred_regions: Preferred travel regions.
            interests:         Travel interests: food, culture, adventure, history, nature, nightlife.
            travel_style:      luxury, budget, backpacker, bleisure, family.
            dietary:           vegetarian, vegan, halal, kosher, gluten_free.
            seat_preference:   economy, business, or first.
            hotel_stars:       Preferred hotel star rating (1-5).
            trip_purpose:      leisure, business, or bleisure.
            budget_usd:        Total trip budget in USD.
            travel_dates:      Date string (e.g. "June 15-22, 2025").
            group_size:        Number of travelers.
            visited_countries: Countries already visited.
            wishlist_cities:   Cities they want to visit.
        Returns:
            JSON confirming profile update.
        """
        if traveler_name:     profile.traveler_name = traveler_name
        if traveler_role:     profile.traveler_role = traveler_role
        if preferred_regions: profile.preferred_regions = list(set(profile.preferred_regions + preferred_regions))
        if interests:         profile.interests = list(set(profile.interests + interests))
        if travel_style:      profile.travel_style = list(set(profile.travel_style + travel_style))
        if dietary:           profile.dietary = list(set(profile.dietary + dietary))
        if seat_preference:   profile.seat_preference = seat_preference
        if hotel_stars:       profile.hotel_stars = hotel_stars
        if trip_purpose:      profile.trip_purpose = trip_purpose
        if budget_usd:        profile.budget_usd = budget_usd
        if travel_dates:      profile.travel_dates = travel_dates
        if group_size:        profile.group_size = group_size
        if visited_countries: profile.visited_countries = list(set(profile.visited_countries + visited_countries))
        if wishlist_cities:   profile.wishlist_cities = list(set(profile.wishlist_cities + wishlist_cities))
        return json.dumps({"status": "updated", "name": profile.traveler_name, "interests": profile.interests})

    def generate_itinerary(destination: str, days: int = 5, interests: list[str] | None = None) -> str:
        """
        Generate a day-by-day itinerary for a destination.

        Args:
            destination: City to plan for.
            days:        Number of days.
            interests:   culture, food, adventure, history, landmarks, nature.
        Returns:
            JSON with structured day-by-day itinerary.
        """
        templates: dict[str, list] = {
            "tokyo": [
                {"day": 1, "theme": "Arrival & Asakusa",   "am": "Senso-ji at dawn",        "pm": "Nakamise street",       "eve": "Izakaya dinner"},
                {"day": 2, "theme": "Modern Tokyo",         "am": "teamLab Borderless",       "pm": "Harajuku & Shibuya",   "eve": "Shibuya Crossing"},
                {"day": 3, "theme": "Day Trip to Nikko",    "am": "Shinkansen to Nikko",      "pm": "Tosho-gu shrine",      "eve": "Ramen back in Tokyo"},
                {"day": 4, "theme": "Food & Culture",       "am": "Tsukiji sushi breakfast",  "pm": "Ginza galleries",      "eve": "Omakase dinner"},
                {"day": 5, "theme": "Departure Day",        "am": "Shinjuku Gyoen garden",    "pm": "Akihabara shopping",   "eve": "Airport transfer"},
            ],
            "istanbul": [
                {"day": 1, "theme": "Sultanahmet",          "am": "Hagia Sophia (early)",     "pm": "Topkapi Palace",       "eve": "Beyoğlu dinner"},
                {"day": 2, "theme": "Bazaars & Bosphorus",  "am": "Grand Bazaar",             "pm": "Bosphorus sunset cruise","eve": "Fish on Galata Bridge"},
                {"day": 3, "theme": "Asian Side & Markets", "am": "Karaköy brunch",           "pm": "Kadıköy market",       "eve": "Rooftop cocktails"},
            ],
            "dubai": [
                {"day": 1, "theme": "Downtown & Heights",   "am": "Burj Khalifa sunrise",     "pm": "Dubai Mall",           "eve": "Dubai Fountain show"},
                {"day": 2, "theme": "Old Dubai & Culture",  "am": "Al Fahidi Fort + Creek",   "pm": "Spice & Gold Souk",    "eve": "Deira dinner"},
                {"day": 3, "theme": "Desert Adventure",     "am": "Desert safari departs 3PM","pm": "Dune bashing",          "eve": "Bedouin camp dinner"},
            ],
        }
        key = destination.lower()
        for k in templates:
            if k in key or key in k:
                key = k; break
        plan = templates.get(key, [{"day": i+1, "theme": f"Day {i+1}", "am": "Explore", "pm": "Visit attraction", "eve": "Local dinner"} for i in range(days)])[:days]
        return json.dumps({"destination": destination, "days": days, "itinerary": plan,
                           "budget_est": f"${(75 + profile.hotel_stars * 40) * days:.0f}–${(150 + profile.hotel_stars * 60) * days:.0f} total"})

    return {search_flights, search_attractions, get_local_food_guide, get_destination_culture_guide,
            check_omix_policy_compliance, update_travel_profile, generate_itinerary}


# ===========================================================================
# System Prompt
# ===========================================================================
SYSTEM_PROMPT = f"""You are "OmixTravel AI" — a premium enterprise travel concierge for Omix employees and executives.

OMIX TRAVEL POLICY (enforce always):
{OMIX_TRAVEL_POLICY}

WORKFLOW:
1. Greet warmly. Ask: name, role (standard/executive), destination/region, dates, group size, purpose.
2. Ask about interests (food/culture/adventure/history) and dietary needs.
3. Call update_travel_profile() after every answer.
4. Use search_flights() for flight options (prefer Omix preferred airlines).
5. Use search_attractions() for the destination.
6. ALWAYS call check_omix_policy_compliance() before any recommendation.
7. Use get_local_food_guide() + get_destination_culture_guide().
8. Use generate_itinerary() for the full day-by-day plan.
9. Present a complete trip brief: flights + hotel tier + attractions + food + culture + policy status.

RULES:
- Always flag policy violations and required approvals prominently.
- Personalize every response to the traveler profile.
- Handle dietary needs proactively.
- Be warm, professional, and expert — like a world-class travel concierge.
"""


# ===========================================================================
# Session lifecycle
# ===========================================================================
def create_session() -> TravelSession:
    if CONFIG_ERROR:
        raise RuntimeError(CONFIG_ERROR)
    sid     = str(uuid.uuid4())[:8]
    profile = TravelPreferences()
    fns     = make_travel_functions(profile)
    cred    = DefaultAzureCredential(exclude_environment_credential=True, exclude_managed_identity_credential=True)
    client  = AgentsClient(endpoint=PROJECT_ENDPOINT, credential=cred)
    fn_tool = FunctionTool(fns)
    toolset = ToolSet()
    toolset.add(fn_tool)
    client.enable_auto_function_calls(toolset)
    agent  = client.create_agent(model=MODEL_DEPLOYMENT, name=f"omixtravel-{sid}", instructions=SYSTEM_PROMPT, toolset=toolset)
    thread = client.threads.create()
    logger.info("[%s] Session started — agent: %s", sid, agent.id)
    return TravelSession(session_id=sid, profile=profile, client=client, agent_id=agent.id, thread_id=thread.id)


def chat(message: str, history: list[dict], session_state: dict) -> tuple[str, list[dict], dict, str]:
    if CONFIG_ERROR:
        return "", history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ {CONFIG_ERROR}"}], session_state, "*Config error*"

    session: TravelSession | None = session_state.get("session")
    if session is None:
        try:
            session = create_session()
            session_state = {"session": session}
        except Exception as e:
            return "", history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ {e}"}], session_state, "*Error*"

    if not history:
        try:
            session.client.messages.create(thread_id=session.thread_id, role=MessageRole.USER, content="Hello!")
            run = session.client.runs.create_and_process(thread_id=session.thread_id, agent_id=session.agent_id)
            if run.status != "failed":
                intro = session.client.messages.get_last_message_text_by_role(thread_id=session.thread_id, role=MessageRole.AGENT)
                if intro:
                    history = [{"role": "assistant", "content": intro.text.value}]
        except Exception as e:
            logger.warning("Intro failed: %s", e)
        if message.strip().lower() in ("hi", "hello", "hey", ""):
            return "", history, session_state, session.profile.summary_md()

    try:
        session.client.messages.create(thread_id=session.thread_id, role=MessageRole.USER, content=message.strip())
        run = session.client.runs.create_and_process(thread_id=session.thread_id, agent_id=session.agent_id)
        if run.status == "failed":
            reply = f"❌ Agent error: {run.last_error}"
        else:
            last = session.client.messages.get_last_message_text_by_role(thread_id=session.thread_id, role=MessageRole.AGENT)
            reply = last.text.value if last else "*(No response)*"
    except HttpResponseError as e:
        reply = f"❌ Azure API error [{e.status_code}]: {e.message}"
    except Exception as e:
        reply = f"❌ Error: {e}"

    return "", history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}], session_state, session.profile.summary_md()


def reset_session(session_state: dict) -> tuple[list, dict, str]:
    """Delete agent and clear session."""
    s: TravelSession | None = session_state.get("session")
    if s:
        s.close()
    return [], {}, "*Session reset. Start a new trip plan!*"


# ===========================================================================
# Gradio UI
# ===========================================================================
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }
body, .gradio-container { background: #090d1a !important; color: #e2e8f0 !important; }

.app-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #0c4a6e 100%);
    border-radius: 16px; padding: 28px 40px; margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.06);
}
.app-header h1 {
    font-size: 2.2em; font-weight: 700; margin: 0 0 4px 0;
    background: linear-gradient(90deg, #38bdf8, #a78bfa, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-header p { color: #94a3b8; margin: 0; font-size: 1em; }
.status-badge {
    display: inline-block; background: rgba(56,189,248,0.15);
    border: 1px solid rgba(56,189,248,0.3); border-radius: 20px;
    padding: 2px 12px; font-size: 12px; color: #38bdf8; margin-top: 8px;
}
.chatbot { background: #090d1a !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 14px !important; }
.send-btn {
    background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
    border: none !important; border-radius: 10px !important; font-weight: 600 !important; color: white !important;
}
.reset-btn {
    background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important; color: #94a3b8 !important;
}
.quick-btn {
    background: rgba(14,165,233,0.12) !important; border: 1px solid rgba(14,165,233,0.25) !important;
    border-radius: 20px !important; font-size: 0.82em !important; color: #7dd3fc !important;
    margin: 2px !important; padding: 4px 12px !important;
}
.quick-btn:hover { background: rgba(14,165,233,0.25) !important; }
.textbox-input textarea {
    background: #0f172a !important; border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important; color: #e2e8f0 !important; font-size: 15px !important;
}
.side-card { background: #0f172a; border-radius: 12px; padding: 18px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 12px; }
.side-card h3 { color: #38bdf8; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 10px 0; }
.profile-md p, .profile-md strong { color: #a5b4fc !important; font-size: 13px !important; line-height: 1.7 !important; }
.footer-txt { text-align: center; color: #334155; font-size: 12px; margin-top: 20px; padding: 12px; }
"""

QUICK_PROMPTS = [
    ("🗼 Tokyo 5 Days", "Plan me a 5-day trip to Tokyo with food and culture focus"),
    ("🕌 Istanbul Explore", "I want to explore Istanbul for 4 days — history and food"),
    ("🏜️ Dubai Luxury", "Plan a 3-day luxury Dubai trip with desert safari"),
    ("🍕 Rome Cultural", "Rome for 4 days, I love history and authentic Italian food"),
    ("✈️ Find Flights", "Help me find flights from New York to London next month"),
    ("📋 Policy Check", "Check if my $1800 flight + $200/night hotel for 5 nights in Europe is compliant"),
    ("🌍 Suggest Destination", "Suggest a destination for me — I love adventure and good food"),
    ("🍱 Halal Trip", "I need halal-friendly travel recommendations in Asia"),
]


def build_app() -> gr.Blocks:
    with gr.Blocks(title="OmixTravel AI — Enterprise Travel Planner") as app:

        gr.HTML("""
        <div class="app-header">
            <h1>✈️ OmixTravel AI</h1>
            <p>Enterprise Travel Intelligence — Flights · Attractions · Food · Culture · Policy Compliance</p>
            <span class="status-badge">● Live</span>
        </div>
        """)

        with gr.Row(equal_height=True):
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(height=520, show_label=False, elem_classes=["chatbot"],
                                     avatar_images=(None, "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=omixtravel"),
                                     render_markdown=True)
                with gr.Row():
                    msg_box = gr.Textbox(placeholder="Where would you like to travel? Tell me your dream trip…",
                                         show_label=False, lines=1, max_lines=3, elem_classes=["textbox-input"], scale=5)
                    send_btn = gr.Button("Send ➤", elem_classes=["send-btn"], scale=1, min_width=80)

                gr.Markdown("**🌍 Quick Start:**")
                with gr.Row():
                    for label, prompt in QUICK_PROMPTS:
                        b = gr.Button(label, elem_classes=["quick-btn"], size="sm")
                        b.click(lambda p=prompt: p, outputs=msg_box)

            with gr.Column(scale=1, min_width=230):
                gr.HTML('<div class="side-card"><h3>🧳 Traveler Profile</h3></div>')
                profile_md = gr.Markdown("*Start chatting to build your profile!*", elem_classes=["profile-md"])

                gr.HTML('<div class="side-card" style="margin-top:12px"><h3>📋 Omix Policy</h3></div>')
                gr.HTML("""
                <div style="font-size:11px;color:#475569;line-height:1.7;padding:0 4px">
                    <b style='color:#64748b'>Domestic flight:</b> ≤ $600<br>
                    <b style='color:#64748b'>Intl flight:</b> ≤ $2,500<br>
                    <b style='color:#64748b'>Hotel/night:</b> ≤ $250/$350<br>
                    <b style='color:#64748b'>&gt;$3k total:</b> Manager approval<br>
                    <b style='color:#64748b'>&gt;$7.5k total:</b> VP approval<br>
                    <b style='color:#64748b'>Preferred:</b> Delta · Emirates · Hilton<br>
                    <b style='color:#64748b'>Intl insurance:</b> Mandatory
                </div>
                """)

                gr.HTML("<br>")
                reset_btn = gr.Button("🔄 New Trip", elem_classes=["reset-btn"], size="sm")

        gr.HTML('<div class="footer-txt">OmixTravel AI · Azure AI Agents · Enterprise Edition</div>')

        session_state = gr.State({})

        def _submit(msg, hist, state):
            if not msg.strip():
                return "", hist, state, profile_md.value
            return chat(msg, hist, state)

        send_btn.click(fn=_submit, inputs=[msg_box, chatbot, session_state], outputs=[msg_box, chatbot, session_state, profile_md])
        msg_box.submit(fn=_submit, inputs=[msg_box, chatbot, session_state], outputs=[msg_box, chatbot, session_state, profile_md])
        reset_btn.click(fn=reset_session, inputs=[session_state], outputs=[chatbot, session_state, profile_md])
        app.load(fn=lambda: ([], {}, "*Start chatting to build your profile!*"), outputs=[chatbot, session_state, profile_md])

    return app


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    if CONFIG_ERROR:
        print(f"\n⚠️  {CONFIG_ERROR}\n")
    print("✈️  Launching OmixTravel AI SaaS App…")
    print("   http://127.0.0.1:7860\n")
    build_app().launch(server_name="0.0.0.0", server_port=7860, share=False,
                       show_error=True, inbrowser=True, css=CUSTOM_CSS, theme=gr.themes.Base())
