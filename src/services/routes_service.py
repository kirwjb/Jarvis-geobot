import aiohttp
from src.utils.utils import log, error
from src.services.map_service import build_google_maps_link
from src.utils.API_codes import get_api_error_message


async def get_distance_osrm(lat1: float, lon1: float, lat2: float, lon2: float) -> float | None:
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "false", "annotations": "false"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("routes"):
                        distance_m = data["routes"][0]["distance"]
                        return distance_m / 1000
                else:
                    error_msg = f"Ошибка OSRM {response.status} при запросе маршрута: {await response.text()}"
                    error(error_msg)
                    return None
        return None
    except Exception as e:
        error(f"Ошибка OSRM через aiohttp: {e}")
        return None

async def build_route_text(selected_attractions: list) -> str:
    if len(selected_attractions) < 2:
        return "Недостаточно точек для маршрута (нужно минимум 2)."
        
    text = "Ваш маршрут:\n\n"
    total_distance = 0.0
    
    for i in range(len(selected_attractions) - 1):
        a = selected_attractions[i]
        b = selected_attractions[i + 1]
        
        dist = await get_distance_osrm(a['lat'], a['lon'], b['lat'], b['lon'])
        if dist is None:
            dist = 1.0
            error(f"Не удалось получить расстояние между {a['name']} и {b['name']}, использована заглушка")
            
        text += f"{i+1}. {a['name']} -> {i+2}. {b['name']} (~{dist:.1f} км)\n"
        total_distance += dist
        
    text += f"\nОбщее расстояние: ~{total_distance:.1f} км"
    text += f"\nКоличество точек: {len(selected_attractions)}"
    
    map_link = build_google_maps_link(selected_attractions)
    if map_link:
        text += f"\n\nКарта маршрута: [открыть в Google Maps]({map_link})"
    
    return text