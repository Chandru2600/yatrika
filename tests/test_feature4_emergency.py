import unittest
import uuid
from app import create_app
from backend.database.db import init_db
from backend.services.emergency.emergency_service import (
    get_emergency_contacts,
    attach_emergency_strip_to_trip,
    CURATED_EMERGENCY_HOSPITALS
)
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary


class Feature4EmergencyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        with cls.app.app_context():
            init_db()
        cls.client = cls.app.test_client()

    def test_curated_emergency_contacts(self):
        # Coorg
        coorg_info = get_emergency_contacts("Coorg, Karnataka")
        self.assertIn("District Hospital Madikeri", coorg_info["hospital_name"])
        self.assertEqual(coorg_info["police_helpline"], "112")
        self.assertEqual(coorg_info["ambulance_helpline"], "108")
        self.assertIn("08272", coorg_info["hospital_phone"])

        # Goa
        goa_info = get_emergency_contacts("Goa, India")
        self.assertIn("Goa Medical College", goa_info["hospital_name"])
        self.assertEqual(goa_info["police_helpline"], "112")
        self.assertEqual(goa_info["ambulance_helpline"], "108")

        # Delhi
        delhi_info = get_emergency_contacts("New Delhi, Delhi")
        self.assertIn("AIIMS", delhi_info["hospital_name"])
        self.assertEqual(delhi_info["police_helpline"], "112")

    def test_fallback_emergency_contacts_unknown_destination(self):
        info = get_emergency_contacts("UnknownVillage99, RemoteState")
        self.assertEqual(info["police_helpline"], "112")
        self.assertEqual(info["ambulance_helpline"], "108")
        self.assertIn("Civil District Hospital", info["hospital_name"])
        self.assertEqual(info["destination"], "UnknownVillage99, RemoteState")

    def test_attach_emergency_strip_to_trip(self):
        trip = {"destination": "Jaipur, Rajasthan", "num_days": 3}
        enriched = attach_emergency_strip_to_trip(trip)
        self.assertIn("emergency", enriched)
        self.assertIn("Sawai Man Singh", enriched["emergency"]["hospital_name"])
        self.assertEqual(enriched["emergency"]["police_helpline"], "112")

    def test_view_trip_emergency_rendering(self):
        with self.app.app_context():
            unique_email = f"emer_{uuid.uuid4().hex[:8]}@example.com"
            user_id = create_user("EmergencyUser", unique_email, "SecurePassword123!", role="user")

            trip_id = create_trip(user_id, {
                "title": "Emergency Strip Test Trip",
                "destination": "Munnar, Kerala",
                "source": "Kochi",
                "start_date": "2026-11-15",
                "end_date": "2026-11-17",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 20000,
                "travel_style": "mid_range",
                "transport": "taxi"
            })
            update_trip_itinerary(
                trip_id,
                itinerary={
                    "days": [
                        {
                            "day_number": 1,
                            "date": "2026-11-15",
                            "morning": {"attraction": "Tea Museum", "type": "Sightseeing", "cost": 150, "time": "09:00 - 12:00"},
                            "afternoon": {"attraction": "Mattupetty Dam", "type": "Sightseeing", "cost": 50, "time": "13:30 - 16:30"},
                            "evening": {"attraction": "Echo Point", "type": "Nature", "cost": 0, "time": "17:00 - 18:30"}
                        }
                    ]
                },
                weather={},
                budget={"total_budget_inr": 20000, "breakdown": {}},
                hotels={"base_camp": {"name": "Munnar Tea Resort", "price_per_night": 2500}}
            )

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = "EmergencyUser"
            sess["user_email"] = unique_email
            sess["user_role"] = "user"

        resp = client.get(f"/planner/{trip_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("24x7 EMERGENCY", html)
        self.assertIn("112", html)
        self.assertIn("108", html)
        self.assertIn("Tata Tea General Hospital Munnar", html)
        self.assertIn("Share Live Location", html)


if __name__ == "__main__":
    unittest.main()
