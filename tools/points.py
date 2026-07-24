# ============================================================
#  tools/points.py — points calculator and state tracker
# ============================================================
import json
import os
from datetime import datetime
from langchain.tools import tool
from config import OUTPUT_DIR, POINTS_GOAL_EOY, PARTY_SIZE

# Chase UR transfer partners with cents-per-point estimates
TRANSFER_PARTNERS = {
    "United MileagePlus":    {"ratio": 1.0, "cpp_economy": 1.3, "cpp_business": 2.1},
    "Air Canada Aeroplan":   {"ratio": 1.0, "cpp_economy": 1.5, "cpp_business": 2.4},
    "British Airways Avios": {"ratio": 1.0, "cpp_economy": 1.2, "cpp_business": 1.8},
    "Air France/KLM":        {"ratio": 1.0, "cpp_economy": 1.1, "cpp_business": 1.9},
    "Singapore KrisFlyer":   {"ratio": 1.0, "cpp_economy": 1.4, "cpp_business": 3.0},
    "Hyatt":                 {"ratio": 1.0, "cpp_hotel":   1.7},
    "Marriott Bonvoy":       {"ratio": 1.0, "cpp_hotel":   0.7},
}

# LAX→SYD award costs per person round trip (approximate, economy)
AWARD_COSTS = {
    "United MileagePlus":  {"economy": 38000, "business": 80000},
    "Air Canada Aeroplan": {"economy": 35000, "business": 75000},
    "Singapore KrisFlyer": {"economy": 43000, "business": 86000},
}


@tool
def calc_points_vs_cash(
    cash_price_per_person: float,
    points_balance: int,
    cabin: str = "economy",
    partner: str = "Air Canada Aeroplan",
) -> str:
    """
    Compare using points vs paying cash for LAX→SYD flights for 4 people.
    Shows total cost each way and which is better value.

    Args:
        cash_price_per_person: Current cash price per person (one way or round trip)
        points_balance: Your current Chase UR points balance
        cabin: 'economy' or 'business'
        partner: Transfer partner name (default: Air Canada Aeroplan)
    """
    total_cash = cash_price_per_person * PARTY_SIZE

    if partner not in AWARD_COSTS:
        available = ", ".join(AWARD_COSTS.keys())
        return f"Partner not found. Available: {available}"

    pts_per_person = AWARD_COSTS[partner].get(cabin, 0)
    total_pts_needed = pts_per_person * PARTY_SIZE
    pts_data = TRANSFER_PARTNERS.get(partner, {})
    cpp = pts_data.get(f"cpp_{cabin}", 1.2)
    points_value_usd = (total_pts_needed * cpp) / 100

    has_enough = points_balance >= total_pts_needed
    shortage   = max(0, total_pts_needed - points_balance)

    months_left = max(1, 12 - datetime.now().month)

    lines = [
        f"── Points vs Cash: LAX→SYD ×{PARTY_SIZE} ({cabin.upper()}) ──",
        f"",
        f"CASH OPTION",
        f"  ${cash_price_per_person:,.0f}/person × {PARTY_SIZE} = ${total_cash:,.0f} total",
        f"",
        f"POINTS OPTION via {partner}",
        f"  {pts_per_person:,} pts/person × {PARTY_SIZE} = {total_pts_needed:,} pts total",
        f"  Effective value: ${points_value_usd:,.0f} (at {cpp}¢/pt)",
        f"  Your balance: {points_balance:,} pts",
    ]

    if has_enough:
        savings = total_cash - points_value_usd
        lines.append(f"  ✓ You have enough points! Saves ~${savings:,.0f} vs cash")
    else:
        lines.append(f"  ✗ Short by {shortage:,} pts")
        monthly_needed = shortage / months_left
        lines.append(f"  Need ~{monthly_needed:,.0f} pts/month for {months_left} months to close gap")

    lines += [
        f"",
        f"VERDICT: {'Points win' if points_value_usd > total_cash * 0.8 else 'Check cash prices'} "
        f"— points worth {cpp}¢ each here vs 1¢ for cash back",
    ]
    return "\n".join(lines)


@tool
def update_points_balance(
    balance: int,
    card: str = "Chase Sapphire Preferred",
    note: str = "",
) -> str:
    """
    Update your current points balance in output/points_state.json.
    Call this whenever you check your Chase account.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "points_state.json")
    existing = {}
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)

    history = existing.get("history", [])
    history.append({
        "recorded_at": datetime.now().isoformat(),
        "card":        card,
        "balance":     balance,
        "note":        note,
    })

    months_left   = max(1, 12 - datetime.now().month)
    gap           = max(0, POINTS_GOAL_EOY - balance)
    needed_monthly = gap / months_left

    state = {
        "last_updated":     datetime.now().isoformat(),
        "current_balance":  balance,
        "card":             card,
        "goal_eoy":         POINTS_GOAL_EOY,
        "gap":              gap,
        "months_remaining": months_left,
        "needed_per_month": round(needed_monthly),
        "on_track":         needed_monthly < 15000,
        "history":          history,
    }

    with open(path, "w") as f:
        json.dump(state, f, indent=2)

    return (
        f"Balance updated: {balance:,} pts\n"
        f"Goal: {POINTS_GOAL_EOY:,} pts by EOY\n"
        f"Gap: {gap:,} pts over {months_left} months "
        f"= {needed_monthly:,.0f} pts/month needed\n"
        f"On track: {'✓ yes' if state['on_track'] else '✗ need to accelerate'}"
    )


@tool
def project_points(
    monthly_grocery: float = 600,
    monthly_amazon: float = 200,
    monthly_dining: float = 300,
    monthly_other: float = 500,
    include_signup_bonus: bool = True,
) -> str:
    """
    Project total Chase UR points earned by EOY based on monthly spend.
    Uses CSP earn rates: 3× dining/delivery, 3× streaming, 2× travel,
    1× everything else. Amex Gold 4× grocery is separate (not Chase).

    Args:
        monthly_grocery: Monthly supermarket spend
        monthly_amazon:  Monthly Amazon/online spend
        monthly_dining:  Monthly restaurant/dining spend
        monthly_other:   All other monthly spend
        include_signup_bonus: Count the 60k signup bonus (first 3 months $4k spend)
    """
    months_left = max(1, 12 - datetime.now().month)

    # CSP earn rates
    dining_pts   = monthly_dining   * 3
    amazon_pts   = monthly_amazon   * 1   # Amazon is 1× on CSP (not a bonus cat)
    grocery_pts  = monthly_grocery  * 1   # CSP is 1× grocery (Amex Gold is better here)
    other_pts    = monthly_other    * 1

    monthly_earn = dining_pts + amazon_pts + grocery_pts + other_pts
    projected    = monthly_earn * months_left
    signup_bonus = 60000 if include_signup_bonus else 0
    total        = projected + signup_bonus

    lines = [
        f"── Points Projection: {months_left} months remaining ──",
        f"",
        f"MONTHLY EARN (Chase Sapphire Preferred)",
        f"  Dining    {monthly_dining:>7,.0f}/mo × 3× = {dining_pts:>7,.0f} pts",
        f"  Amazon    {monthly_amazon:>7,.0f}/mo × 1× = {amazon_pts:>7,.0f} pts",
        f"  Grocery   {monthly_grocery:>7,.0f}/mo × 1× = {grocery_pts:>7,.0f} pts",
        f"  Other     {monthly_other:>7,.0f}/mo × 1× = {other_pts:>7,.0f} pts",
        f"  ─────────────────────────────────────────",
        f"  Monthly total:              {monthly_earn:>7,.0f} pts/mo",
        f"",
        f"PROJECTION",
        f"  {months_left} months × {monthly_earn:,.0f}  = {projected:>10,.0f} pts",
    ]
    if include_signup_bonus:
        lines.append(f"  Signup bonus (60k, $4k/3mo) = {signup_bonus:>10,.0f} pts")
    lines += [
        f"  ─────────────────────────────────────────",
        f"  TOTAL by EOY:               {total:>10,.0f} pts",
        f"  Goal:                       {POINTS_GOAL_EOY:>10,.0f} pts",
        f"  Gap:                        {max(0, POINTS_GOAL_EOY - total):>10,.0f} pts",
        f"",
        f"⚠  NOTE: CSP earns only 1× on groceries. Adding Amex Gold (4× grocery)",
        f"   would add ~{monthly_grocery * 3 * months_left:,.0f} pts over {months_left} months.",
    ]
    return "\n".join(lines)
