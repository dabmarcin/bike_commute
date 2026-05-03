"""
BikeCommute Analytics Dashboard
NiceGUI-based interface for bike commute analytics
"""
from nicegui import ui
import plotly.graph_objects as go
from datetime import datetime, timedelta
from drive_manager import GoogleDriveManager
from tcx_analyzer import TCXAnalyzer
from weather import WeatherManager
from database import BikeCommuteDB
from config import APP_TITLE, DARK_MODE, HOME, OFFICE
import os


class BikeCommuteDashboard:
    def __init__(self):
        print("\n=== DASHBOARD INIT ===")
        print("Initializing database...")
        self.db = BikeCommuteDB()
        print("Initializing Google Drive...")
        self.drive_manager = GoogleDriveManager()
        print("Initializing weather...")
        self.weather_manager = WeatherManager()
        self.sync_in_progress = False
        print("Setting up UI...")
        self.setup_ui()
        print("Dashboard ready!\n")

    def setup_ui(self):
        """Initialize the UI layout"""
        # Header
        with ui.header().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(APP_TITLE).classes("text-2xl font-bold")

                with ui.row():
                    ui.button("Sync with Google Drive", on_click=self.sync_rides).props(
                        "color=primary"
                    )
                    ui.switch("Dark Mode", value=DARK_MODE, on_change=self.toggle_dark_mode)

        # Main content
        with ui.column().classes("w-full p-4 gap-4"):
            # Stats cards
            with ui.row().classes("w-full gap-4"):
                self.last_time_card = self.create_stat_card("Last Time", "—", "text-xl")
                self.streak_card = self.create_stat_card("Current Streak", "—", "text-xl")
                self.pr_card = self.create_stat_card("Best Time (PR)", "—", "text-xl")

            # Charts
            with ui.card().classes("w-full"):
                ui.label("Ride Duration Trend").classes("text-lg font-bold")
                self.chart = ui.plotly(go.Figure()).classes("w-full")
                self.refresh_chart()

            # Stats table
            with ui.card().classes("w-full"):
                ui.label("Recent Rides").classes("text-lg font-bold")
                self.rides_table = ui.table(
                    columns=[
                        {"name": "date", "label": "Date", "field": "date"},
                        {"name": "duration", "label": "Duration", "field": "duration_str"},
                        {"name": "distance", "label": "Distance (km)", "field": "distance"},
                        {"name": "avg_speed", "label": "Avg Speed (km/h)", "field": "avg_speed"},
                        {"name": "avg_hr", "label": "HR (bpm)", "field": "avg_hr"},
                        {"name": "calories", "label": "Calories", "field": "calories"},
                        {"name": "wind_component", "label": "Wind (km/h)", "field": "wind_component"},
                        {"name": "route_type", "label": "Route", "field": "route_type"},
                    ],
                    rows=[],
                ).classes("w-full")

        self.refresh_dashboard()

    def create_stat_card(self, title, value, value_class=""):
        """Create a stat card component"""
        with ui.card().classes("flex-1"):
            ui.label(title).classes("text-sm text-gray-500")
            value_label = ui.label(value).classes(f"{value_class} font-bold")
        return value_label

    def format_duration(self, seconds):
        """Format duration in seconds to mm:ss"""
        if not seconds:
            return "—"
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    def format_wind(self, wind_speed_ms, wind_component):
        """Format wind information"""
        if wind_speed_ms is None:
            return "—"
        wind_kmh = self.weather_manager.convert_wind_speed_ms_to_kmh(wind_speed_ms)
        if wind_component is None:
            return f"{wind_kmh:.1f}"
        return f"{wind_component:.1f}"

    def refresh_dashboard(self):
        """Refresh all dashboard components"""
        print("  [refresh_dashboard] Getting all rides from DB...")
        rides = self.db.get_all_rides()
        print(f"  [refresh_dashboard] Found {len(rides)} rides")

        if not rides:
            print("  ⚠️  No rides in database!")
            return

        # Last time
        print("  [refresh_dashboard] Updating stats cards...")
        last_ride = rides[0]
        self.last_time_card.set_text(
            self.format_duration(last_ride["duration"])
        )
        print(f"    ✓ Last time: {last_ride['duration']}s")

        # Streak
        streak = self.db.get_current_streak("To Work")
        self.streak_card.set_text(str(streak))
        print(f"    ✓ Streak: {streak}")

        # PR (best time)
        best_ride = self.db.get_best_time("To Work")
        if best_ride:
            self.pr_card.set_text(
                self.format_duration(best_ride["duration"])
            )
            print(f"    ✓ PR: {best_ride['duration']}s")

        # Update table
        print("  [refresh_dashboard] Updating table with rides...")
        table_data = []
        for ride in rides[:20]:  # Show last 20 rides
            table_data.append(
                {
                    "date": ride["date"][:10],
                    "duration_str": self.format_duration(ride["duration"]),
                    "distance": f"{ride['distance']:.2f}",
                    "avg_speed": f"{ride['avg_speed']:.1f}",
                    "avg_hr": ride["avg_hr"] or "—",
                    "calories": ride.get("calories") or "—",
                    "wind_component": self.format_wind(ride["wind_speed"], ride["wind_component"]),
                    "route_type": ride["route_type"],
                }
            )
        self.rides_table.rows = table_data
        print(f"    ✓ Table updated with {len(table_data)} rows")

    def refresh_chart(self):
        """Refresh the ride duration chart"""
        rides = self.db.get_all_rides()

        if not rides:
            self.chart.update_figure(go.Figure())
            return

        # Prepare data
        dates = [datetime.fromisoformat(ride["date"][:19]).strftime("%Y-%m-%d") for ride in rides]
        durations = [ride["duration"] / 60 for ride in rides]  # Convert to minutes
        wind_components = [ride["wind_component"] or 0 for ride in rides]

        # Color by wind component (red for headwind, green for tailwind)
        colors = []
        for wc in wind_components:
            if wc > 5:
                colors.append("red")  # Headwind
            elif wc < -5:
                colors.append("green")  # Tailwind
            else:
                colors.append("gray")  # Neutral

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=durations,
                mode="lines+markers",
                name="Duration",
                marker=dict(size=8, color=colors, line=dict(width=2, color="white")),
                line=dict(color="lightblue", width=2),
            )
        )

        fig.update_layout(
            title="Ride Duration Over Time",
            xaxis_title="Date",
            yaxis_title="Duration (minutes)",
            hovermode="x unified",
            template="plotly_dark" if DARK_MODE else "plotly",
            margin=dict(l=50, r=50, t=50, b=50),
        )

        self.chart.update_figure(fig)

    def sync_rides(self):
        """Sync new rides from Google Drive"""
        print("\n\n╔════════════════════════════════════╗")
        print("║  SYNC BUTTON CLICKED - STARTING!  ║")
        print("╚════════════════════════════════════╝\n")

        if self.sync_in_progress:
            print("⚠️  Sync already in progress!")
            ui.notify("Sync already in progress...", type="warning")
            return

        self.sync_in_progress = True
        print("✓ Sync flag set to True")
        ui.notify("Starting sync with Google Drive...", type="info")

        try:
            print("\n=== SYNC START ===")
            print("Step 1: Downloading GPX files from Google Drive...")
            # Download new GPX files
            downloaded_files = self.drive_manager.sync_new_files()
            print(f"Downloaded files: {len(downloaded_files)} files")
            for f in downloaded_files:
                print(f"  - {f}")

            if not downloaded_files:
                ui.notify("No new rides to sync", type="info")
                self.sync_in_progress = False
                return

            new_prs = []

            # Process each downloaded file
            print("Step 2: Analyzing TCX files...")
            for tcx_file in downloaded_files:
                try:
                    print(f"  Processing: {tcx_file}")
                    # Analyze TCX
                    analyzer = TCXAnalyzer(tcx_file)
                    metrics = analyzer.analyze()
                    print(f"    ✓ GPS parsed: {metrics['distance']:.2f}km, {metrics['duration']}s, HR: {metrics['avg_hr']}bpm")

                    # Get weather data
                    weather = self.weather_manager.get_weather_for_ride(metrics["date"])

                    # Calculate wind component
                    wind_component = None
                    if metrics["avg_bearing"] is not None and weather["wind_direction"] is not None:
                        wind_component = analyzer._calculate_wind_component(
                            metrics["avg_bearing"],
                            weather["wind_direction"],
                            weather["wind_speed"],
                        )

                    # Check for PR before inserting
                    best_time = self.db.get_best_time(metrics["route_type"])
                    is_pr = False
                    if best_time is None or metrics["duration"] < best_time["duration"]:
                        is_pr = True
                        new_prs.append({
                            "route": metrics["route_type"],
                            "time": self.format_duration(metrics["duration"]),
                        })

                    # Insert into database
                    print(f"    Saving to database...")
                    success = self.db.insert_ride(
                        drive_file_id=tcx_file,  # Use file path as ID
                        date=metrics["date"],
                        duration=metrics["duration"],
                        distance=metrics["distance"],
                        avg_hr=metrics["avg_hr"],
                        max_hr=metrics["max_hr"],
                        avg_speed=metrics["avg_speed"],
                        calories=metrics.get("calories"),
                        temp=weather.get("temp"),
                        wind_speed=weather.get("wind_speed"),
                        wind_direction=weather.get("wind_direction"),
                        wind_component=wind_component,
                        route_type=metrics["route_type"],
                    )

                    if success:
                        print(f"    ✓ Saved successfully")
                        ui.notify(f"Processed: {os.path.basename(tcx_file)}", type="positive")
                    else:
                        print(f"    ⚠ Already processed or duplicate")
                        ui.notify(f"Already processed: {os.path.basename(tcx_file)}", type="warning")

                except Exception as e:
                    print(f"    ✗ ERROR: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    ui.notify(f"Error processing {tcx_file}: {str(e)}", type="negative")

            # Show PR notifications
            print(f"Step 3: New PRs: {len(new_prs)}")
            for pr in new_prs:
                ui.notify(
                    f"🎉 New PR on {pr['route']}: {pr['time']}!",
                    type="positive",
                    position="top",
                )

            # Refresh dashboard
            print("Step 4: Refreshing dashboard...")
            self.refresh_dashboard()
            self.refresh_chart()

            print("=== SYNC COMPLETE ===\n")
            ui.notify(f"Sync complete! Processed {len(downloaded_files)} ride(s)", type="positive")

        except Exception as e:
            print(f"=== SYNC ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            ui.notify(f"Sync error: {str(e)}", type="negative")
        finally:
            self.sync_in_progress = False

    def toggle_dark_mode(self, value):
        """Toggle dark mode"""
        # Refresh chart theme to match new mode
        self.refresh_chart()


# Initialize the app
app = None


@ui.page("/")
def index():
    print("\n>>> PAGE LOAD: index() called")
    global app
    app = BikeCommuteDashboard()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title=APP_TITLE, dark=DARK_MODE, reload=False, port=9000)
