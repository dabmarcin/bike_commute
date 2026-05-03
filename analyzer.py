"""
GPS and GPX analysis for BikeCommute Analytics
Parses GPX files and calculates ride metrics including wind component
"""
import gpxpy
import math
from datetime import datetime, timedelta
from haversine import haversine
from config import HOME, OFFICE, ROUTE_DETECTION_RADIUS


class BikeRideAnalyzer:
    def __init__(self, gpx_file_path):
        self.gpx_file_path = gpx_file_path
        self.gpx = None
        self.track = None
        self.segments = None
        self._parse_gpx()

    def _parse_gpx(self):
        """Parse GPX file"""
        try:
            with open(self.gpx_file_path, "r", encoding="utf-8") as gpx_file:
                self.gpx = gpxpy.parse(gpx_file)
                if self.gpx.tracks:
                    self.track = self.gpx.tracks[0]
                    self.segments = self.track.segments
        except Exception as e:
            raise ValueError(f"Error parsing GPX file: {e}")

    def _get_heart_rate(self, point):
        """Extract heart rate from Samsung/Garmin extensions"""
        if hasattr(point, "extensions"):
            for ext in point.extensions:
                if "hr" in ext.tag.lower():
                    try:
                        return int(ext.text)
                    except (ValueError, AttributeError):
                        continue
        return None

    def _detect_route_type(self):
        """Detect if ride is 'To Work' (from HOME) or 'Return' (from OFFICE)"""
        if not self.segments or not self.segments[0].points:
            return "unknown"

        start_point = self.segments[0].points[0]
        start_coords = (start_point.latitude, start_point.longitude)

        # Distance to HOME
        dist_to_home = haversine(start_coords, (HOME["lat"], HOME["lon"]), unit="m")

        # Distance to OFFICE
        dist_to_office = haversine(start_coords, (OFFICE["lat"], OFFICE["lon"]), unit="m")

        # Determine route type based on proximity
        if dist_to_home <= ROUTE_DETECTION_RADIUS:
            return "To Work"
        elif dist_to_office <= ROUTE_DETECTION_RADIUS:
            return "Return"
        else:
            return "Other"

    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing (direction) between two points in degrees (0-360)"""
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
            lat2_rad
        ) * math.cos(dlon)

        bearing = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing) + 360) % 360
        return bearing_deg

    def _calculate_wind_component(self, avg_bearing, wind_direction, wind_speed):
        """
        Calculate wind component (headwind/tailwind)
        Positive = headwind (slowing you down)
        Negative = tailwind (speeding you up)
        """
        if wind_speed is None:
            return None

        # Angle between movement direction and wind direction
        angle_diff = (wind_direction - avg_bearing) % 360

        # Normalize to -180 to 180
        if angle_diff > 180:
            angle_diff -= 360

        # Component along direction of travel
        # Headwind when wind comes from ahead (0°), tailwind when from behind (180°)
        wind_component = wind_speed * math.cos(math.radians(angle_diff))

        return wind_component

    def _calculate_avg_bearing(self):
        """Calculate average bearing across the entire ride"""
        if not self.segments or not self.segments[0].points or len(self.segments[0].points) < 2:
            return None

        bearings = []
        points = self.segments[0].points

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            bearing = self._calculate_bearing(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            bearings.append(bearing)

        # Average bearing using circular mean
        if not bearings:
            return None

        sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
        cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
        avg_bearing = math.atan2(sin_sum / len(bearings), cos_sum / len(bearings))
        avg_bearing_deg = (math.degrees(avg_bearing) + 360) % 360

        return avg_bearing_deg

    def analyze(self):
        """Analyze the GPX file and return ride metrics"""
        if not self.track or not self.segments:
            raise ValueError("No track data found in GPX file")

        metrics = {
            "date": None,
            "duration": 0,
            "distance": 0,
            "avg_hr": 0,
            "max_hr": 0,
            "avg_speed": 0,
            "route_type": self._detect_route_type(),
            "avg_bearing": self._calculate_avg_bearing(),
            "heart_rates": [],
        }

        heart_rates = []
        all_points = []

        # Collect all points and heart rates
        for segment in self.segments:
            for point in segment.points:
                all_points.append(point)
                hr = self._get_heart_rate(point)
                if hr is not None:
                    heart_rates.append(hr)

        if not all_points:
            raise ValueError("No track points found in GPX file")

        # Date and time
        metrics["date"] = all_points[0].time.isoformat() if all_points[0].time else None

        # Duration
        if all_points[0].time and all_points[-1].time:
            duration = all_points[-1].time - all_points[0].time
            metrics["duration"] = int(duration.total_seconds())

        # Distance
        metrics["distance"] = self.track.length_3d() / 1000  # Convert to km

        # Heart rate stats
        if heart_rates:
            metrics["avg_hr"] = int(sum(heart_rates) / len(heart_rates))
            metrics["max_hr"] = max(heart_rates)
            metrics["heart_rates"] = heart_rates

        # Speed (km/h)
        if metrics["duration"] > 0:
            metrics["avg_speed"] = (metrics["distance"] / metrics["duration"]) * 3600

        return metrics

    def get_efficiency_factor(self, metrics, wind_component=0):
        """
        Calculate Efficiency Factor (EF)
        EF = Average Speed / Average Heart Rate
        """
        if not metrics.get("avg_hr") or metrics["avg_hr"] == 0:
            return 0

        ef = metrics["avg_speed"] / metrics["avg_hr"]
        return round(ef, 3)


if __name__ == "__main__":
    # Test analyzer
    import sys

    if len(sys.argv) > 1:
        gpx_file = sys.argv[1]
        analyzer = BikeRideAnalyzer(gpx_file)
        metrics = analyzer.analyze()

        print(f"Route Type: {metrics['route_type']}")
        print(f"Date: {metrics['date']}")
        print(f"Duration: {metrics['duration']}s ({metrics['duration']//60}m)")
        print(f"Distance: {metrics['distance']:.2f} km")
        print(f"Avg Speed: {metrics['avg_speed']:.2f} km/h")
        print(f"Avg HR: {metrics['avg_hr']} bpm")
        print(f"Max HR: {metrics['max_hr']} bpm")
        print(f"Avg Bearing: {metrics['avg_bearing']:.1f}°")
        print(f"EF: {analyzer.get_efficiency_factor(metrics)}")
    else:
        print("Usage: python analyzer.py <gpx_file>")
