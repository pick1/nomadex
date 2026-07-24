from tools.deals  import fetch_deals
from tools.flights import search_flights, watch_route
from tools.points  import calc_points_vs_cash, update_points_balance, project_points

ALL_TOOLS = [
    fetch_deals,
    search_flights,
    watch_route,
    calc_points_vs_cash,
    update_points_balance,
    project_points,
]
