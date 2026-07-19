import math
from src.utils.utils import log, error, logger

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

def _routeDistance(route: list) -> float:
    total = 0.0
    for i in range(len(route) - 1):
        lat1, lon1 = float(route[i]['lat']), float(route[i]['lon'])
        lat2, lon2 = float(route[i + 1]['lat']), float(route[i + 1]['lon'])
        total += math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)
    return total

def _twoOptImprove(route: list) -> list:
    if len(route) < 4:
        return route

    improved = True
    best = route
    while improved:
        improved = False
        bestDistance = _routeDistance(best)
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                candidateDistance = _routeDistance(candidate)
                if candidateDistance < bestDistance - 1e-9:
                    best = candidate
                    bestDistance = candidateDistance
                    improved = True
    return best

def optimizeRoutePoints(routePoints: list) -> list:
    validPoints = [p for p in routePoints if _isValidPoint(p)]
    skippedCount = len(routePoints) - len(validPoints)
    if skippedCount:
        logger.warning(f"Пропущено {skippedCount} точек маршрута без корректных координат lat/lon.")

    validPoints = _dedupePoints(validPoints)

    if len(validPoints) <= 2:
        return validPoints

    unvisitedPoints = list(validPoints)
    optimizedRoute = []
    
    currentPoint = unvisitedPoints.pop(0)
    optimizedRoute.append(currentPoint)
    
    while unvisitedPoints:
        closestPoint = None
        minDistance = float('inf')
        closestIndex = -1
        
        currentLat = float(currentPoint['lat'])
        currentLon = float(currentPoint['lon'])
        
        for idx, targetPoint in enumerate(unvisitedPoints):
            targetLat = float(targetPoint['lat'])
            targetLon = float(targetPoint['lon'])
 
            distance = math.sqrt((targetLat - currentLat) ** 2 + (targetLon - currentLon) ** 2)
            
            if distance < minDistance:
                minDistance = distance
                closestPoint = targetPoint
                closestIndex = idx
                
        if closestPoint is not None:
            currentPoint = unvisitedPoints.pop(closestIndex)
            optimizedRoute.append(currentPoint)
        else:
            logger.warning("Не удалось найти ближайшую точку. Прерывание оптимизации маршрута.")
            break

    optimizedRoute = _twoOptImprove(optimizedRoute)

    logger.info(f"Маршрут оптимизирован: исходных точек {len(routePoints)}, отсортировано {len(optimizedRoute)}")
    return optimizedRoute