import math
from src.utils.utils import logger

def _isValidPoint(point: dict) -> bool:
    lat = point.get('lat')
    lon = point.get('lon')
    if lat is None or lon is None:
        return False
    try:
        float(lat)
        float(lon)
    except (TypeError, ValueError):
        return False
    return True

def _dedupePoints(routePoints: list) -> list:
    seen = set()
    result = []
    for point in routePoints:
        key = (round(float(point['lat']), 6), round(float(point['lon']), 6))
        if key in seen:
            continue
        seen.add(key)
        result.append(point)
    return result

def _twoOptImprove(route: list) -> list:
    if len(route) < 4:
        return route

    coords = [(float(p['lat']), float(p['lon'])) for p in route]
    improved = True
    best = list(route)

    while improved:
        improved = False
        n = len(best)
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                p_prev = coords[i - 1]
                p_i = coords[i]
                p_j = coords[j]
                p_next = coords[j + 1]

                current_dist = (
                    math.hypot(p_i[0] - p_prev[0], p_i[1] - p_prev[1])
                    + math.hypot(p_next[0] - p_j[0], p_next[1] - p_j[1])
                )
                new_dist = (
                    math.hypot(p_j[0] - p_prev[0], p_j[1] - p_prev[1])
                    + math.hypot(p_next[0] - p_i[0], p_next[1] - p_i[1])
                )

                if new_dist < current_dist - 1e-9:
                    best[i : j + 1] = reversed(best[i : j + 1])
                    coords[i : j + 1] = reversed(coords[i : j + 1])
                    improved = True
                    break
            if improved:
                break
    return best

def optimizeRoutePoints(routePoints: list) -> list:
    validPoints = [p for p in routePoints if _isValidPoint(p)]
    skippedCount = len(routePoints) - len(validPoints)
    if skippedCount:
        logger.warning(f"Пропущено {skippedCount} точек маршрута без корректных координат lat/lon.")

    validPoints = _dedupePoints(validPoints)

    if len(validPoints) <= 2:
        return validPoints

    unvisited = [(float(p['lat']), float(p['lon']), p) for p in validPoints]
    currentLat, currentLon, currentPoint = unvisited.pop(0)
    optimizedRoute = [currentPoint]

    while unvisited:
        best_idx = 0
        min_sq = float('inf')

        for idx, (tLat, tLon, _) in enumerate(unvisited):
            d_sq = (tLat - currentLat) ** 2 + (tLon - currentLon) ** 2
            if d_sq < min_sq:
                min_sq = d_sq
                best_idx = idx

        currentLat, currentLon, currentPoint = unvisited.pop(best_idx)
        optimizedRoute.append(currentPoint)

    optimizedRoute = _twoOptImprove(optimizedRoute)
    logger.info(f"Маршрут оптимизирован: исходных точек {len(routePoints)}, отсортировано {len(optimizedRoute)}")
    return optimizedRoute
