"""
TCX (Training Center XML) analysis for BikeCommute Analytics
Garmin TCX format parser with full GPS and heart rate data
"""
import xml.etree.ElementTree as ET
import math
from datetime import datetime
from haversine import haversine
from config import HOME, OFFICE, ROUTE_DETECTION_RADIUS


class TCXAnalyzer:
    def __init__(self, tcx_file_path):
        self.tcx_file_path = tcx_file_path
        self.root = None
        self.namespace = {
            '': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
            'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
        }
        self._parse_tcx()

    def _parse_tcx(self):
        """Parse TCX file"""
        try:
            tree = ET.parse(self.tcx_file_path)
            self.root = tree.getroot()
        except Exception as e:
            raise ValueError(f"Error parsing TCX file: {e}")

    def _get_text(self, element, tag):
        """Safely get text from XML element"""
        if element is None:
            return None
        found = element.find(tag, self.namespace)
        return found.text if found is not None else None

    def _detect_route_type(self, start_coords):
        """Detect if ride is 'To Work' or 'Return' based on start location"""
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
        """Calculate bearing between two points"""
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

        bearing = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing) + 360) % 360
        return bearing_deg

    def _calculate_avg_bearing(self, trackpoints):
        """Calculate average bearing across the ride"""
        if len(trackpoints) < 2:
            return None

        bearings = []
        for i in range(len(trackpoints) - 1):
            tp1 = trackpoints[i]
            tp2 = trackpoints[i + 1]

            bearing = self._calculate_bearing(
                tp1['lat'], tp1['lon'],
                tp2['lat'], tp2['lon']
            )
            bearings.append(bearing)

        # Average bearing using circular mean
        sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
        cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
        avg_bearing = math.atan2(sin_sum / len(bearings), cos_sum / len(bearings))
        avg_bearing_deg = (math.degrees(avg_bearing) + 360) % 360

        return avg_bearing_deg

    def _calculate_wind_component(self, avg_bearing, wind_direction, wind_speed):
        """Calculate wind component (headwind/tailwind)"""
        if wind_speed is None:
            return None

        angle_diff = (wind_direction - avg_bearing) % 360
        if angle_diff > 180:
            angle_diff -= 360

        wind_component = wind_speed * math.cos(math.radians(angle_diff))
        return wind_component

    def analyze(self):
        """Analyze TCX file and extract metrics"""
        # Find Activity element
        activities = self.root.findall('.//Activity', self.namespace)
        if not activities:
            raise ValueError("No Activity found in TCX file")

        activity = activities[0]

        # Find Lap element
        laps = activity.findall('.//Lap', self.namespace)
        if not laps:
            raise ValueError("No Lap found in TCX file")

        lap = laps[0]

        # Extract basic metrics from Lap
        metrics = {
            "date": None,
            "duration": 0,
            "distance": 0,
            "avg_hr": 0,
            "max_hr": 0,
            "avg_speed": 0,
            "calories": 0,
            "route_type": "Other",
            "avg_bearing": None,
        }

        # Get start time from Lap attribute
        start_time = lap.get("StartTime")
        if start_time:
            metrics["date"] = start_time

        # Total time in seconds
        time_str = self._get_text(lap, "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}TotalTimeSeconds")
        if time_str:
            metrics["duration"] = int(float(time_str))

        # Distance in meters
        dist_str = self._get_text(lap, "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}DistanceMeters")
        if dist_str:
            metrics["distance"] = float(dist_str) / 1000  # Convert to km

        # Calories
        cal_str = self._get_text(lap, "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Calories")
        if cal_str:
            metrics["calories"] = int(cal_str)

        # Average HR
        avg_hr_bpm = lap.find('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}AverageHeartRateBpm')
        if avg_hr_bpm is None:
            avg_hr_bpm = lap.find('.//AverageHeartRateBpm')
        if avg_hr_bpm is not None:
            avg_hr_elem = avg_hr_bpm.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Value')
            if avg_hr_elem is None:
                avg_hr_elem = avg_hr_bpm.find('Value')
            if avg_hr_elem is not None and avg_hr_elem.text:
                try:
                    metrics["avg_hr"] = int(avg_hr_elem.text)
                except ValueError:
                    pass

        # Max HR
        max_hr_bpm = lap.find('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}MaximumHeartRateBpm')
        if max_hr_bpm is None:
            max_hr_bpm = lap.find('.//MaximumHeartRateBpm')
        if max_hr_bpm is not None:
            max_hr_elem = max_hr_bpm.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Value')
            if max_hr_elem is None:
                max_hr_elem = max_hr_bpm.find('Value')
            if max_hr_elem is not None and max_hr_elem.text:
                try:
                    metrics["max_hr"] = int(max_hr_elem.text)
                except ValueError:
                    pass

        # Parse trackpoints
        trackpoints = []
        heart_rates = []

        for tp_elem in lap.findall(".//Trackpoint", self.namespace):
            # Time
            time_elem = tp_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Time")
            if time_elem is None:
                time_elem = tp_elem.find("Time")

            # Position (Lat/Lon)
            pos_elem = tp_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Position", self.namespace)
            if pos_elem is None:
                pos_elem = tp_elem.find("Position")

            if pos_elem is not None:
                lat_elem = pos_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LatitudeDegrees")
                lon_elem = pos_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LongitudeDegrees")
                if lat_elem is None:
                    lat_elem = pos_elem.find("LatitudeDegrees")
                if lon_elem is None:
                    lon_elem = pos_elem.find("LongitudeDegrees")

                if lat_elem is not None and lon_elem is not None:
                    trackpoints.append({
                        "lat": float(lat_elem.text),
                        "lon": float(lon_elem.text),
                        "time": time_elem.text if time_elem is not None else None
                    })

            # Heart rate
            hr_bpm = tp_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}HeartRateBpm")
            if hr_bpm is None:
                hr_bpm = tp_elem.find("HeartRateBpm")
            if hr_bpm is not None:
                hr_elem = hr_bpm.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Value")
                if hr_elem is None:
                    hr_elem = hr_bpm.find("Value")
                if hr_elem is not None and hr_elem.text:
                    try:
                        heart_rates.append(int(hr_elem.text))
                    except ValueError:
                        pass

        # Calculate speed if we have distance and duration
        if metrics["duration"] > 0 and metrics["distance"] > 0:
            metrics["avg_speed"] = (metrics["distance"] / metrics["duration"]) * 3600  # km/h

        # Detect route type
        if trackpoints:
            start_coords = (trackpoints[0]["lat"], trackpoints[0]["lon"])
            metrics["route_type"] = self._detect_route_type(start_coords)

        # Calculate average bearing
        if len(trackpoints) >= 2:
            metrics["avg_bearing"] = self._calculate_avg_bearing(trackpoints)

        return metrics

    def get_efficiency_factor(self, metrics):
        """Calculate Efficiency Factor (EF) = Speed / Avg HR"""
        if not metrics.get("avg_hr") or metrics["avg_hr"] == 0:
            return 0
        ef = metrics["avg_speed"] / metrics["avg_hr"]
        return round(ef, 3)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tcx_file = sys.argv[1]
        analyzer = TCXAnalyzer(tcx_file)
        metrics = analyzer.analyze()

        print(f"Route Type: {metrics['route_type']}")
        print(f"Date: {metrics['date']}")
        print(f"Duration: {metrics['duration']}s ({metrics['duration']//60}m)")
        print(f"Distance: {metrics['distance']:.2f} km")
        print(f"Avg Speed: {metrics['avg_speed']:.2f} km/h")
        print(f"Avg HR: {metrics['avg_hr']} bpm")
        print(f"Max HR: {metrics['max_hr']} bpm")
        print(f"Calories: {metrics['calories']}")
        print(f"Avg Bearing: {metrics['avg_bearing']:.1f}°" if metrics['avg_bearing'] else "Avg Bearing: N/A")
        print(f"EF: {analyzer.get_efficiency_factor(metrics)}")
    else:
        print("Usage: python tcx_analyzer.py <tcx_file>")
