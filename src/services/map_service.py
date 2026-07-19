from src.services.optimizer_service import optimizeRoutePoints

def build_google_maps_link(route_points):
    if len(route_points) < 2:
        return None
    optimizedPoints = optimizeRoutePoints(route_points)

    origin = f"{optimizedPoints[0]['lat']},{optimizedPoints[0]['lon']}"
    destination = f"{optimizedPoints[-1]['lat']},{optimizedPoints[-1]['lon']}"

    waypoints_list = [f"{p['lat']},{p['lon']}" for p in optimizedPoints[1:-1]]
    
    if waypoints_list:
        waypoints = "|".join(waypoints_list)
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}"
        
    return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"

#DON'T DELETE: These functions are commented out because they are not currently used in the codebase. They may be useful in the future for generating map links for Yandex and OpenStreetMap, but for now, they are kept as comments to avoid cluttering the code with unused functions.
#def build_yandex_map_link(route_points):
    #if len(route_points) < 2:
        #return None
    #points = "~".join([f"{p['lon']},{p['lat']}" for p in route_points])
    #return f"https://yandex.by/maps/?rtext={points}&rtt=auto"

#def build_osm_map_link(route_points):
    #if len(route_points) < 2:
        #return None
    #coords = ";".join([f"{p['lon']},{p['lat']}" for p in route_points])
    #return f"https://www.openstreetmap.org/directions?route={coords}"