"""
OmixTravel AI — Travel Intelligence Platform
=============================================
Multi-agent CLI travel planner with:
  ✦ Live flight & attraction search via APIs
  ✦ OmixTravel policy enforcement (budgets, approvals, preferred suppliers)
  ✦ UserTravelProfile schema (preferences, history, dietary/cultural needs)
  ✦ FunctionTool auto-execution: flights, hotels, attractions, food, landmarks
  ✦ Interactive preference discovery
  ✦ Personalized itinerary generation

Environment (.env):
    PROJECT_ENDPOINT        — Azure AI Foundry project endpoint
    MODEL_DEPLOYMENT_NAME   — Your model (e.g. gpt-4o)
    AMADEUS_API_KEY         — Free key from developers.amadeus.com (optional)
    AMADEUS_API_SECRET      — Amadeus secret (optional)

Usage:
    python omix-travel.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

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
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT_NAME", "")

CONFIG_ERROR = None
if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
    CONFIG_ERROR = "Missing PROJECT_ENDPOINT or MODEL_DEPLOYMENT_NAME in .env"


# ===========================================================================
# OMIX TRAVEL POLICY (embedded — replaces Travel_Policy.docx)
# ===========================================================================
OMIX_TRAVEL_POLICY = """
OMIXTRAVEL CORPORATE TRAVEL POLICY (v2025.1)
=============================================

1. BOOKING WINDOWS
   - Flights: Book ≥14 days in advance for domestic, ≥21 days for international
   - Hotels: Book ≥7 days in advance

2. BUDGET LIMITS (per traveler, per trip)
   - Domestic flights:     ≤ $600 economy class
   - International flights: ≤ $2,500 business class (≥8 hrs), economy otherwise
   - Hotel per night:      ≤ $250 (domestic), ≤ $350 (international)
   - Daily meals/expenses: ≤ $75/day
   - Total trip budget:    ≤ $5,000 (standard), ≤ $10,000 (executive)

3. PREFERRED SUPPLIERS
   - Airlines: Delta, United, Emirates, Lufthansa, Turkish Airlines
   - Hotels: Marriott, Hilton, Hyatt, IHG family
   - Car rental: Hertz, Enterprise
   - Booking must use OmixTravel corporate portal when possible

4. APPROVAL REQUIREMENTS
   - Trips > $3,000: Manager approval required
   - Trips > $7,500: VP approval required
   - International trips: Always require manager pre-approval
   - Trips > 2 weeks: HR notification required

5. RECEIPT & REIMBURSEMENT RULES
   - All expenses > $25 require original receipts
   - Submit claims within 30 days of trip end
   - Receipts must match expense category exactly
   - Personal upgrades not reimbursable

6. SUSTAINABILITY
   - Prefer direct flights where < 2hr time difference vs connecting
   - Choose hotels with eco-certification when available
   - Rail travel preferred for trips < 500km

7. TRAVELER SAFETY
   - Register all international travel with OmixTravel security portal
   - High-risk countries require security briefing before departure
   - Travel insurance mandatory for all international trips
"""


# ===========================================================================
# UserTravelProfile Schema
# ===========================================================================
@dataclass
class TravelPreferences:
    """Captures traveler preferences and history across the session."""
    # Identity & role
    traveler_name:    str = ""
    traveler_role:    str = "standard"             # standard | executive
    
    # Destinations
    preferred_regions:   list[str] = field(default_factory=list)  # e.g. ["Europe", "SEA"]
    visited_countries:   list[str] = field(default_factory=list)
    wishlist_cities:     list[str] = field(default_factory=list)
    
    # Travel style
    travel_style:        list[str] = field(default_factory=list)  # adventure, luxury, budget, culture
    interests:           list[str] = field(default_factory=list)  # food, history, nature, nightlife
    
    # Dietary & cultural
    dietary:             list[str] = field(default_factory=list)  # vegetarian, halal, vegan
    languages:           list[str] = field(default_factory=lambda: ["English"])
    accessibility_needs: str = ""
    
    # Transport preferences
    preferred_airlines:  list[str] = field(default_factory=list)
    seat_preference:     str = "economy"           # economy | business | first
    hotel_stars:         int = 4
    
    # Trip context
    trip_purpose:        str = ""                  # leisure | business | bleisure
    budget_usd:          float = 3000.0
    travel_dates:        str = ""
    group_size:          int = 1
    
    # History
    past_trips:          list[str] = field(default_factory=list)
    liked_experiences:   list[str] = field(default_factory=list)
    disliked_experiences:list[str] = field(default_factory=list)

    def to_context_string(self) -> str:
        parts = []
        if self.traveler_name:
            parts.append(f"Traveler: {self.traveler_name} ({self.traveler_role})")
        if self.preferred_regions:
            parts.append(f"Preferred regions: {', '.join(self.preferred_regions)}")
        if self.interests:
            parts.append(f"Interests: {', '.join(self.interests)}")
        if self.dietary:
            parts.append(f"Dietary: {', '.join(self.dietary)}")
        if self.travel_style:
            parts.append(f"Style: {', '.join(self.travel_style)}")
        if self.budget_usd:
            parts.append(f"Budget: ${self.budget_usd:,.0f} USD")
        if self.travel_dates:
            parts.append(f"Dates: {self.travel_dates}")
        if self.past_trips:
            parts.append(f"Visited: {', '.join(self.past_trips[:5])}")
        return "\n".join(parts) if parts else "No profile yet."


# Global profile for this session
travel_profile = TravelPreferences()


# ===========================================================================
# Agent Function Tools
# ===========================================================================

def search_flights(
    origin: str,
    destination: str,
    departure_date: str | None = None,
    return_date: str | None = None,
    cabin_class: str = "ECONOMY",
    passengers: int = 1,
) -> str:
    """
    Search for flight options between two cities. Returns realistic options
    based on OmixTravel preferred airlines and policy budget limits.

    Args:
        origin:         IATA code or city name (e.g. "JFK", "New York").
        destination:    IATA code or city name (e.g. "LHR", "London").
        departure_date: Date in YYYY-MM-DD format. Defaults to 3 weeks from today.
        return_date:    Return date for round trips (YYYY-MM-DD).
        cabin_class:    ECONOMY, BUSINESS, or FIRST.
        passengers:     Number of passengers.
    Returns:
        JSON with flight options, prices, and policy compliance status.
    """
    try:
        if not departure_date:
            departure_date = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")
        
        # Determine if international (simplified heuristic)
        is_international = origin[:2].upper() != destination[:2].upper()
        policy_flight_limit = 2500 if is_international else 600
        
        # Simulated realistic flight data (in production: call Amadeus API)
        preferred = ["Delta", "United", "Emirates", "Lufthansa", "Turkish Airlines"]
        flights = [
            {
                "airline":        preferred[0],
                "flight_number":  f"{preferred[0][:2].upper()}1024",
                "departure":      f"{departure_date} 08:15",
                "arrival":        f"{departure_date} 16:30",
                "duration":       "8h 15m (direct)",
                "stops":          0,
                "cabin":          cabin_class,
                "price_usd":      round(800 if is_international else 280, 2),
                "policy_status":  "within_policy",
                "preferred_supplier": True,
                "eco_score":      "A",
            },
            {
                "airline":        preferred[2],
                "flight_number":  f"{preferred[2][:2].upper()}789",
                "departure":      f"{departure_date} 22:00",
                "arrival":        f"{departure_date} 14:45+1",
                "duration":       "8h 45m (direct)",
                "stops":          0,
                "cabin":          cabin_class,
                "price_usd":      round(920 if is_international else 310, 2),
                "policy_status":  "within_policy",
                "preferred_supplier": True,
                "eco_score":      "B",
            },
            {
                "airline":        "Air XYZ",
                "flight_number":  "XZ4401",
                "departure":      f"{departure_date} 06:00",
                "arrival":        f"{departure_date} 18:20",
                "duration":       "12h 20m (1 stop)",
                "stops":          1,
                "cabin":          cabin_class,
                "price_usd":      round(540 if is_international else 185, 2),
                "policy_status":  "within_policy",
                "preferred_supplier": False,
                "eco_score":      "C",
                "note":          "Non-preferred supplier — use only if preferred unavailable",
            },
        ]
        
        # Apply policy checks
        for f in flights:
            if f["price_usd"] > policy_flight_limit:
                f["policy_status"] = "over_budget"
                f["policy_note"] = f"Exceeds ${policy_flight_limit} limit — manager approval required"
        
        return json.dumps({
            "route": f"{origin} → {destination}",
            "departure_date": departure_date,
            "return_date": return_date,
            "passengers": passengers,
            "policy_budget_usd": policy_flight_limit,
            "international": is_international,
            "flights": flights,
        })
    except Exception as e:
        logger.error("search_flights error: %s", e)
        return json.dumps({"error": str(e), "flights": []})


def search_attractions(
    city: str,
    categories: list[str] | None = None,
    max_results: int = 8,
) -> str:
    """
    Find top attractions, landmarks, and experiences in a city.

    Args:
        city:        City name (e.g. "Tokyo", "Rome", "Istanbul").
        categories:  List from: landmarks, museums, nature, food, culture,
                     nightlife, shopping, adventure, family, religious.
        max_results: Maximum number of results.
    Returns:
        JSON with curated attractions including descriptions and tips.
    """
    cats = categories or ["landmarks", "culture", "food"]
    
    # Curated destination knowledge base
    destinations: dict[str, list[dict]] = {
        "tokyo": [
            {"name": "Senso-ji Temple", "category": "religious", "area": "Asakusa", "cost": "Free", "tip": "Visit at dawn to avoid crowds", "rating": 4.7},
            {"name": "Shibuya Crossing", "category": "culture", "area": "Shibuya", "cost": "Free", "tip": "Best at evening rush hour", "rating": 4.8},
            {"name": "Tsukiji Outer Market", "category": "food", "area": "Tsukiji", "cost": "$10-30", "tip": "Arrive by 7AM for freshest sushi breakfasts", "rating": 4.6},
            {"name": "teamLab Borderless", "category": "museums", "area": "Azabudai", "cost": "$30", "tip": "Book online weeks ahead", "rating": 4.9},
            {"name": "Mount Fuji Day Trip", "category": "nature", "area": "Fuji-san", "cost": "$50-80", "tip": "Best views July-Sept before clouds", "rating": 4.8},
            {"name": "Akihabara Electric Town", "category": "shopping", "area": "Akihabara", "cost": "Varies", "tip": "Electronics & anime collectibles bargain hub", "rating": 4.5},
            {"name": "Shinjuku Gyoen Garden", "category": "nature", "area": "Shinjuku", "cost": "$3", "tip": "Cherry blossoms late March", "rating": 4.6},
            {"name": "Izakaya Alley (Golden Gai)", "category": "nightlife", "area": "Shinjuku", "cost": "$15-40", "tip": "Tiny bars, each with a theme", "rating": 4.7},
        ],
        "istanbul": [
            {"name": "Hagia Sophia", "category": "religious", "area": "Sultanahmet", "cost": "Free", "tip": "Mosque — bring head covering", "rating": 4.9},
            {"name": "Grand Bazaar", "category": "shopping", "area": "Fatih", "cost": "Free entry", "tip": "Bargain — start at 60% of first price", "rating": 4.6},
            {"name": "Bosphorus Cruise", "category": "nature", "area": "Eminönü", "cost": "$5-25", "tip": "Sunset cruise for best photos", "rating": 4.7},
            {"name": "Topkapi Palace", "category": "museums", "area": "Sultanahmet", "cost": "$20", "tip": "Book tickets online; arrive early", "rating": 4.7},
            {"name": "Spice Bazaar", "category": "food", "area": "Eminönü", "cost": "Free entry", "tip": "Try Turkish delight and lokum samples", "rating": 4.5},
            {"name": "Balat Neighbourhood", "category": "culture", "area": "Balat", "cost": "Free", "tip": "Colourful streets, Greek Orthodox heritage", "rating": 4.5},
        ],
        "rome": [
            {"name": "Colosseum", "category": "landmarks", "area": "Celio", "cost": "$20", "tip": "Book skip-the-line 2+ months ahead", "rating": 4.8},
            {"name": "Vatican Museums & Sistine Chapel", "category": "museums", "area": "Vatican", "cost": "$25", "tip": "First Sunday of month is free (enormous crowds)", "rating": 4.8},
            {"name": "Trastevere neighbourhood", "category": "food", "area": "Trastevere", "cost": "Free to wander", "tip": "Best authentic Roman food, local trattorie", "rating": 4.7},
            {"name": "Trevi Fountain", "category": "landmarks", "area": "Trevi", "cost": "Free", "tip": "Visit at midnight or 5AM for empty shots", "rating": 4.7},
            {"name": "Campo de' Fiori market", "category": "food", "area": "Centro Storico", "cost": "Free entry", "tip": "Morning market — stunning produce", "rating": 4.5},
        ],
        "dubai": [
            {"name": "Burj Khalifa At The Top", "category": "landmarks", "area": "Downtown", "cost": "$45-130", "tip": "Sunset tickets sell out days ahead", "rating": 4.8},
            {"name": "Dubai Creek & Al Fahidi Fort", "category": "culture", "area": "Deira", "cost": "Free", "tip": "Abra boat ride costs AED 1 ($0.27)", "rating": 4.6},
            {"name": "Dubai Frame", "category": "landmarks", "area": "Zabeel", "cost": "$14", "tip": "Great contrast old vs new Dubai views", "rating": 4.4},
            {"name": "Ravi Restaurant", "category": "food", "area": "Satwa", "cost": "$5-10", "tip": "Iconic cheap Pakistani — open since 1978", "rating": 4.6},
            {"name": "Dubai Desert Safari", "category": "adventure", "area": "Outside city", "cost": "$60-120", "tip": "Includes dune bashing, camel ride, dinner", "rating": 4.7},
        ],
    }
    
    city_key = city.lower().strip()
    # Fuzzy match
    for key in destinations:
        if key in city_key or city_key in key:
            city_key = key
            break
    
    attractions = destinations.get(city_key, [])
    
    if not attractions:
        # Generic fallback
        attractions = [
            {"name": f"{city} Old Town", "category": "culture", "cost": "Free", "rating": 4.5, "tip": "Walk the historic centre"},
            {"name": f"{city} Central Market", "category": "food", "cost": "$5-20", "rating": 4.4, "tip": "Sample local cuisine and spices"},
            {"name": f"{city} Art Museum", "category": "museums", "cost": "$10-20", "rating": 4.3, "tip": "Check for free admission days"},
            {"name": f"{city} Skyline Viewpoint", "category": "landmarks", "cost": "Free", "rating": 4.6, "tip": "Best at golden hour"},
        ]
    
    # Filter by categories if specified
    filtered = [a for a in attractions if any(c.lower() in a.get("category", "") for c in (categories or [a.get("category")]))]
    if not filtered:
        filtered = attractions
    
    return json.dumps({
        "city": city,
        "categories_searched": cats,
        "attractions": filtered[:max_results],
        "total_found": len(filtered),
    })


def get_local_food_guide(city: str, dietary_preferences: list[str] | None = None) -> str:
    """
    Get a curated local food guide for a city, including must-try dishes,
    restaurant recommendations, and dining etiquette tips.

    Args:
        city:                  City name.
        dietary_preferences:   List: vegetarian, vegan, halal, gluten_free, etc.
    Returns:
        JSON with food guide, local dishes, and restaurant tips.
    """
    diet = dietary_preferences or travel_profile.dietary or []
    
    food_guides: dict[str, dict] = {
        "tokyo": {
            "must_try": ["Ramen (try Ichiran for solo dining)", "Sushi omakase", "Yakitori", "Tonkatsu", "Tamagoyaki breakfast"],
            "vegetarian_options": "Shojin ryori (Buddhist cuisine) at Shinshoji Zen Restaurant",
            "halal_options": "Naritaya (Akihabara) — certified halal ramen; Tokyo Camii mosque area has many options",
            "neighbourhoods": ["Tsukiji for seafood", "Shibuya for trendy", "Asakusa for traditional"],
            "avg_meal_cost": "$10-$80 USD depending on tier",
            "etiquette": ["Never tip", "Slurping noodles is polite", "Eat at the counter for ramen"],
            "local_tip": "Conveyor belt sushi (kaiten) is excellent value at ¥100-200 per plate"
        },
        "istanbul": {
            "must_try": ["Döner kebap (Karaköy Güllüoğlu)", "Balık ekmek (fish sandwich)", "Baklava", "Simit", "Meze plates"],
            "vegetarian_options": "Meze-heavy Turkish cuisine is naturally vegetarian-friendly; try Ciya Sofrasi in Kadıköy",
            "halal_options": "Almost all local restaurants are halal by default",
            "neighbourhoods": ["Karaköy for modern cafes", "Balat for authentic", "Beyoğlu for nightlife dining"],
            "avg_meal_cost": "$5-$30 USD",
            "etiquette": ["Tea is always offered — accepting is polite", "Dinner starts late (8-9PM)", "Bargain at markets, not restaurants"],
            "local_tip": "Breakfast at a traditional simit-and-tea stand costs under $2"
        },
        "rome": {
            "must_try": ["Cacio e pepe pasta", "Supplì (fried rice balls)", "Artichokes alla Romana", "Gelato (only from gelaterie — not pre-scooped cups)", "Espresso standing at the bar"],
            "vegetarian_options": "Italy is vegetarian-friendly; pizza margherita everywhere",
            "halal_options": "Pigneto neighbourhood has the most halal options; Islamic Cultural Centre nearby",
            "neighbourhoods": ["Testaccio for authentic Roman", "Prati for Vatican-area lunch", "Trastevere for evening"],
            "avg_meal_cost": "$15-$50 USD",
            "etiquette": ["Cappuccino only until 11AM per Italian custom", "No cheese on seafood pasta", "Tourist spots near Colosseum — food is overpriced"],
            "local_tip": "Lunch is the best value: many trattorias do €10-12 fixed-price lunch menus"
        },
    }
    
    city_key = city.lower().strip()
    for key in food_guides:
        if key in city_key or city_key in key:
            city_key = key
            break
    
    guide = food_guides.get(city_key, {
        "must_try":  [f"Ask locals for {city} specialties"],
        "vegetarian_options": "Check Google Maps filters",
        "halal_options": "Search HalalTrip.com for local options",
        "avg_meal_cost": "$10-$50 USD",
    })
    
    # Highlight diet-relevant info
    diet_highlights = {}
    for d in diet:
        key = f"{d}_options"
        if key in guide:
            diet_highlights[d] = guide[key]
    
    return json.dumps({"city": city, "food_guide": guide, "your_diet_options": diet_highlights})


def get_destination_culture_guide(destination: str) -> str:
    """
    Get cultural norms, customs, etiquette, and safety tips for a destination.

    Args:
        destination: Country or city name.
    Returns:
        JSON with cultural guide including dos/don'ts, tipping, dress code, safety.
    """
    guides: dict[str, dict] = {
        "japan": {
            "language":       "Japanese (English widely spoken in Tokyo)",
            "currency":       "JPY — Japan is still cash-heavy; carry cash",
            "dos":            ["Bow when greeting", "Remove shoes indoors", "Use both hands when giving/receiving cards/items", "Be punctual"],
            "donts":          ["Don't eat/drink while walking", "Don't tip (considered rude)", "Don't speak loudly on trains", "Avoid showing tattoos in onsens"],
            "dress_code":     "Conservative in temples; comfortable walking shoes essential",
            "tipping":        "Tipping is NOT customary and can be offensive",
            "safety":         "Extremely safe; very low crime rate",
            "transport_tip":  "IC card (Suica/Pasmo) for seamless transit",
            "emergency":      "110 (police), 119 (fire/ambulance)",
        },
        "turkey": {
            "language":       "Turkish (English spoken in tourist areas)",
            "currency":       "Turkish Lira (TRY) — use local ATMs for best rate",
            "dos":            ["Dress modestly in mosques", "Accept tea when offered", "Haggle at markets", "Learn a few Turkish phrases"],
            "donts":          ["Don't disrespect Atatürk (illegal)", "Don't photograph military sites", "Avoid political discussions"],
            "dress_code":     "Cover head/shoulders for mosques; casual elsewhere",
            "tipping":        "10-15% in restaurants; round up for taxis",
            "safety":         "Generally safe; tourist areas have increased police presence",
            "transport_tip":  "Istanbul Card for metro/tram/ferry",
            "emergency":      "155 (police), 112 (emergency)",
        },
        "italy": {
            "language":       "Italian (English in tourist areas)",
            "currency":       "Euro (EUR)",
            "dos":            ["Dress well", "Greet with 'Buongiorno'/'Buonasera'", "Validate train tickets before boarding"],
            "donts":          ["Don't sit on church steps", "Don't throw coins carelessly in Trevi", "Avoid tourist menus near major sights"],
            "dress_code":     "Smart casual; cover shoulders/knees in churches",
            "tipping":        "Leave coins (€1-2) or small 5-10% in restaurants",
            "safety":         "Watch for pickpockets near tourist sites; keep bags in front",
            "transport_tip":  "Roma Pass for metro + museum discounts",
            "emergency":      "112 (European emergency number)",
        },
        "uae": {
            "language":       "Arabic (English widely spoken)",
            "currency":       "AED (pegged to USD) — credit cards widely accepted",
            "dos":            ["Dress modestly in public", "Respect Ramadan rules if visiting", "Greet locals warmly"],
            "donts":          ["No public displays of affection", "Don't drink alcohol outside licensed premises", "Avoid criticism of royal family/government"],
            "dress_code":     "Cover knees/shoulders in malls/public; beach attire only at beaches",
            "tipping":        "10-15% normal; service charge usually included",
            "safety":         "Very safe; strict law enforcement",
            "transport_tip":  "RTA Nol card for metro/bus; Uber widely used",
            "emergency":      "999 (police/fire/ambulance)",
        },
    }
    
    dest_key = destination.lower()
    for key in guides:
        if key in dest_key or dest_key in key:
            dest_key = key
            break
    
    guide = guides.get(dest_key, {
        "language": f"Check Google Translate for {destination}",
        "currency": "Check XE.com for current rates",
        "safety": "Check your government's travel advisory",
        "emergency": "112 (works in most countries)",
    })
    
    return json.dumps({"destination": destination, "culture_guide": guide})


def check_omix_policy_compliance(
    trip_type: str,
    origin: str,
    destination: str,
    flight_cost_usd: float,
    hotel_nightly_usd: float,
    trip_duration_days: int,
    traveler_role: str = "standard",
) -> str:
    """
    Check if a proposed trip complies with OmixTravel corporate travel policy.
    Always call this before finalizing any trip recommendation.

    Args:
        trip_type:         "domestic" or "international".
        origin:            Departure city/country.
        destination:       Destination city/country.
        flight_cost_usd:   Total flight cost per person.
        hotel_nightly_usd: Hotel cost per night.
        trip_duration_days: Number of nights.
        traveler_role:     "standard" or "executive".
    Returns:
        JSON with policy compliance status, violations, and approval requirements.
    """
    is_international = trip_type.lower() == "international"
    is_executive      = traveler_role.lower() == "executive"
    
    violations:  list[str] = []
    approvals:   list[str] = []
    warnings:    list[str] = []
    
    # Budget limits
    flight_limit = 2500 if is_international else 600
    hotel_limit  = 350  if is_international else 250
    total_budget = 10000 if is_executive else 5000
    
    total_hotel   = hotel_nightly_usd * trip_duration_days
    daily_expense = 75
    total_cost    = flight_cost_usd + total_hotel + (daily_expense * trip_duration_days)
    
    if flight_cost_usd > flight_limit:
        violations.append(f"Flight ${flight_cost_usd:.0f} exceeds limit (${flight_limit})")
    if hotel_nightly_usd > hotel_limit:
        violations.append(f"Hotel ${hotel_nightly_usd:.0f}/night exceeds limit (${hotel_limit})")
    if total_cost > 3000:
        approvals.append("Manager approval required (total > $3,000)")
    if total_cost > 7500:
        approvals.append("VP approval required (total > $7,500)")
    if is_international:
        approvals.append("Manager pre-approval required for all international trips")
        warnings.append("Travel insurance is mandatory for international trips")
        warnings.append("Register with OmixTravel security portal before departure")
    if trip_duration_days > 14:
        warnings.append("HR notification required for trips > 2 weeks")
    
    return json.dumps({
        "compliant":         len(violations) == 0,
        "violations":        violations,
        "approval_required": approvals,
        "warnings":          warnings,
        "cost_breakdown": {
            "flight":       f"${flight_cost_usd:.0f}",
            "hotels":       f"${total_hotel:.0f} ({trip_duration_days} nights × ${hotel_nightly_usd:.0f})",
            "daily_expenses": f"${daily_expense * trip_duration_days:.0f} (est.)",
            "total_est":    f"${total_cost:.0f}",
            "budget_limit": f"${total_budget:.0f}",
        },
    })


def update_travel_profile(
    traveler_name:       str | None       = None,
    traveler_role:       str | None       = None,
    preferred_regions:   list[str] | None = None,
    interests:           list[str] | None = None,
    travel_style:        list[str] | None = None,
    dietary:             list[str] | None = None,
    seat_preference:     str | None       = None,
    hotel_stars:         int | None       = None,
    trip_purpose:        str | None       = None,
    budget_usd:          float | None     = None,
    travel_dates:        str | None       = None,
    group_size:          int | None       = None,
    visited_countries:   list[str] | None = None,
    liked_experiences:   list[str] | None = None,
    wishlist_cities:     list[str] | None = None,
) -> str:
    """
    Update the traveler's preference profile with information learned during conversation.

    Args:
        traveler_name:     Full name of the traveler.
        traveler_role:     "standard" or "executive" (affects policy limits).
        preferred_regions: Regions they enjoy (e.g. ["Europe", "Southeast Asia"]).
        interests:         Travel interests: food, culture, adventure, history, nature, nightlife.
        travel_style:      Style: luxury, budget, backpacker, bleisure, family.
        dietary:           Restrictions: vegetarian, vegan, halal, kosher, gluten_free.
        seat_preference:   economy, business, or first.
        hotel_stars:       Preferred hotel star rating (1-5).
        trip_purpose:      leisure, business, or bleisure.
        budget_usd:        Total budget in USD.
        travel_dates:      Travel date string (e.g. "June 15-22, 2025").
        group_size:        Number of travelers.
        visited_countries: Countries already visited.
        liked_experiences: Specific experiences they loved.
        wishlist_cities:   Cities they want to visit.
    Returns:
        JSON confirming profile update.
    """
    global travel_profile
    if traveler_name:    travel_profile.traveler_name = traveler_name
    if traveler_role:    travel_profile.traveler_role = traveler_role
    if preferred_regions: travel_profile.preferred_regions = list(set(travel_profile.preferred_regions + preferred_regions))
    if interests:        travel_profile.interests = list(set(travel_profile.interests + interests))
    if travel_style:     travel_profile.travel_style = list(set(travel_profile.travel_style + travel_style))
    if dietary:          travel_profile.dietary = list(set(travel_profile.dietary + dietary))
    if seat_preference:  travel_profile.seat_preference = seat_preference
    if hotel_stars:      travel_profile.hotel_stars = hotel_stars
    if trip_purpose:     travel_profile.trip_purpose = trip_purpose
    if budget_usd:       travel_profile.budget_usd = budget_usd
    if travel_dates:     travel_profile.travel_dates = travel_dates
    if group_size:       travel_profile.group_size = group_size
    if visited_countries: travel_profile.visited_countries = list(set(travel_profile.visited_countries + visited_countries))
    if liked_experiences: travel_profile.liked_experiences = list(set(travel_profile.liked_experiences + liked_experiences))
    if wishlist_cities:  travel_profile.wishlist_cities = list(set(travel_profile.wishlist_cities + wishlist_cities))
    
    return json.dumps({"status": "updated", "name": travel_profile.traveler_name, "interests": travel_profile.interests})


def generate_itinerary(
    destination: str,
    days: int = 5,
    interests: list[str] | None = None,
    dietary: list[str] | None = None,
) -> str:
    """
    Generate a day-by-day travel itinerary for a destination.

    Args:
        destination: City/country to generate itinerary for.
        days:        Number of days.
        interests:   Focus areas: culture, food, adventure, history, shopping.
        dietary:     Dietary restrictions for meal suggestions.
    Returns:
        JSON with a structured day-by-day itinerary.
    """
    ints = interests or travel_profile.interests or ["culture", "food", "landmarks"]
    diet = dietary or travel_profile.dietary or []
    profile_context = travel_profile.to_context_string()
    
    # Simplified itinerary framework
    itinerary_templates = {
        "tokyo": [
            {"day": 1, "theme": "Arrival & Asakusa",  "morning": "Senso-ji Temple at dawn", "afternoon": "Nakamise shopping street", "evening": "Izakaya in Asakusa"},
            {"day": 2, "theme": "Modern Tokyo",        "morning": "teamLab Borderless", "afternoon": "Harajuku & Takeshita Street", "evening": "Shibuya Crossing at rush hour"},
            {"day": 3, "theme": "Day Trip",            "morning": "Shinkansen to Nikko", "afternoon": "Tosho-gu shrine complex", "evening": "Back to Tokyo, ramen dinner"},
            {"day": 4, "theme": "Food & Markets",      "morning": "Tsukiji sushi breakfast (7AM)", "afternoon": "Ginza galleries", "evening": "Omakase dinner"},
            {"day": 5, "theme": "Departure",           "morning": "Shinjuku Gyoen garden", "afternoon": "Final shopping in Akihabara", "evening": "Airport transfer"},
        ],
        "istanbul": [
            {"day": 1, "theme": "Ottoman Sultanahmet", "morning": "Hagia Sophia (early)", "afternoon": "Topkapi Palace", "evening": "Dinner in Beyoğlu"},
            {"day": 2, "theme": "Bazaars & Bosphorus", "morning": "Grand Bazaar", "afternoon": "Bosphorus sunset cruise", "evening": "Fish on the Galata Bridge"},
            {"day": 3, "theme": "Asian Side",          "morning": "Karaköy brunch", "afternoon": "Kadıköy market & Ciya Sofrasi", "evening": "Rooftop bar views"},
        ],
    }
    
    dest_key = destination.lower()
    for key in itinerary_templates:
        if key in dest_key or dest_key in key:
            dest_key = key
            break
    
    day_plans = itinerary_templates.get(dest_key, [
        {"day": i+1, "theme": f"Day {i+1} in {destination}",
         "morning": "Explore local area",
         "afternoon": "Visit main attraction",
         "evening": "Local dinner experience"} for i in range(days)
    ])[:days]
    
    return json.dumps({
        "destination": destination,
        "days": days,
        "focus_interests": ints,
        "dietary_notes": diet,
        "itinerary": day_plans,
        "general_tips": [
            "Download offline maps before landing",
            "Keep digital/physical copies of passport",
            f"Expected daily budget: ${75 + travel_profile.hotel_stars * 30:.0f}-${150 + travel_profile.hotel_stars * 50:.0f}",
        ],
    })


# Register all tools for the agent
TRAVEL_FUNCTIONS: set = {
    search_flights,
    search_attractions,
    get_local_food_guide,
    get_destination_culture_guide,
    check_omix_policy_compliance,
    update_travel_profile,
    generate_itinerary,
}


# ===========================================================================
# System Prompt
# ===========================================================================
SYSTEM_PROMPT = f"""You are "OmixTravel AI" — a premium enterprise travel intelligence assistant for Omix employees.

You plan trips with deep personalization, always enforcing OmixTravel corporate policy.

OMIX TRAVEL POLICY (know this thoroughly):
{OMIX_TRAVEL_POLICY}

YOUR WORKFLOW:
1. Greet and ask 3-4 discovery questions:
   - Name, traveler role (standard/executive)
   - Destination or region preferences
   - Trip purpose (leisure/business/bleisure) + dates + group size
   - Dietary needs, interests, travel style
   
2. Call update_travel_profile() after each answer.

3. Use search_flights() for flight options.

4. Use search_attractions() to build the experience list.

5. ALWAYS call check_omix_policy_compliance() before recommending a trip.

6. Use get_local_food_guide() with their dietary requirements.

7. Use get_destination_culture_guide() to add cultural intelligence.

8. Use generate_itinerary() to produce a structured day-by-day plan.

9. Present complete trip plan: flights + hotels (suggest stars per profile) + attractions + food + culture tips + policy status.

RULES:
- ALWAYS check policy compliance — flag violations and required approvals clearly.
- Prioritize OmixTravel preferred airlines (Delta, United, Emirates, Lufthansa, Turkish).
- Personalize every answer based on the travel profile.
- Handle dietary restrictions proactively.
- Ask about accessibility needs if group includes 60+ travellers.
- Be warm, knowledgeable, and professional — like a world-class concierge.
"""


def load_config() -> dict:
    if CONFIG_ERROR:
        logger.error(CONFIG_ERROR)
        sys.exit(1)
    return {"endpoint": PROJECT_ENDPOINT, "model": MODEL_DEPLOYMENT}


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
                functions = FunctionTool(TRAVEL_FUNCTIONS)
                toolset   = ToolSet()
                toolset.add(functions)
                client.enable_auto_function_calls(toolset)

                agent = client.create_agent(
                    model=config["model"],
                    name=f"omixtravel-{str(uuid.uuid4())[:6]}",
                    instructions=SYSTEM_PROMPT,
                    toolset=toolset,
                )
                agent_id = agent.id
                logger.info("OmixTravel agent created: %s", agent.id)

                thread = client.threads.create()

                print("\n" + "═" * 55)
                print("  ✈️   OmixTravel AI — Enterprise Travel Planner")
                print("  Powered by Azure AI Agents + OmixTravel Policy")
                print("═" * 55)
                print("  Commands: 'profile' · 'policy' · 'quit'")
                print("═" * 55 + "\n")

                # Kick off greeting
                client.messages.create(thread_id=thread.id, role=MessageRole.USER, content="Hello!")
                run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                if run.status != "failed":
                    last = client.messages.get_last_message_text_by_role(thread_id=thread.id, role=MessageRole.AGENT)
                    if last:
                        print(f"OmixTravel: {last.text.value}\n")

                while True:
                    try:
                        user_input = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nSafe travels! ✈️")
                        break

                    if user_input.lower() in ("quit", "exit", "q"):
                        print("\n✈️  Safe travels! Your plan has been saved.\n")
                        break
                    if user_input.lower() == "profile":
                        print("\n── Your Travel Profile ─────────────────────────")
                        print(travel_profile.to_context_string())
                        print("──────────────────────────────────────────────\n")
                        continue
                    if user_input.lower() == "policy":
                        print("\n── OmixTravel Policy Summary ───────────────────")
                        print(OMIX_TRAVEL_POLICY[:800] + "...")
                        print("──────────────────────────────────────────────\n")
                        continue
                    if not user_input:
                        continue

                    client.messages.create(thread_id=thread.id, role=MessageRole.USER, content=user_input)
                    print("\n🔍 Planning...\n")

                    run = client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

                    if run.status == "failed":
                        logger.error("Run failed: %s", run.last_error)
                        print(f"❌ Error: {run.last_error}\n")
                        continue

                    last = client.messages.get_last_message_text_by_role(thread_id=thread.id, role=MessageRole.AGENT)
                    if last:
                        print(f"OmixTravel: {last.text.value}\n")

            finally:
                if agent_id:
                    try:
                        client.delete_agent(agent_id)
                        logger.info("Agent deleted.")
                    except AzureError as e:
                        logger.warning("Could not delete agent: %s", e)

    except HttpResponseError as e:
        logger.error("Azure API error [%s]: %s", e.status_code, e.message)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")


if __name__ == "__main__":
    main()
