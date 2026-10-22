from urllib.parse import quote

def build_google_maps_link(route_points: list[dict]) -> str | None:
    if len(route_points) < 2:
        return None

    origin = (
        f"{route_points[0]['lat']},"
        f"{route_points[0]['lon']}"
    )

    destination = (
        f"{route_points[-1]['lat']},"
        f"{route_points[-1]['lon']}"
    )

    waypoints_list = [
        f"{point['lat']},{point['lon']}"
        for point in route_points[1:-1]
    ]

    params = [
        f"api=1",
        f"origin={quote(origin)}",
        f"destination={quote(destination)}",
    ]

    if waypoints_list:
        waypoints = "|".join(waypoints_list)
        params.append(
            f"waypoints={quote(waypoints)}"
        )

    return (
        "https://www.google.com/maps/dir/?"
        + "&".join(params)
    )
