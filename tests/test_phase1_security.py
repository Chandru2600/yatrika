"""
Phase 1 Security & Route Integrity Automated Regression Test Suite

Verifies:
1. Cross-user expense IDOR protection (add and delete).
2. Unauthorized private trip access control.
3. Cryptographically unguessable public share tokens and explicit sharing toggles.
4. Safe handling and enumeration defense for legacy numeric share URLs.
5. Isolated guest sessions preventing cross-guest data leakage.
6. Route redirects and canonical aliases (/destinations, /wizard, /new).
"""

import os
import tempfile
import unittest
import json

from app import create_app
from backend.database.db import get_db_connection, init_db
from backend.models.user import create_user, get_user_by_id
from backend.models.trip import (
    create_trip,
    get_trip_by_id,
    add_expense,
    get_expenses,
)


class Phase1SecurityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a dedicated temp database for isolated testing
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix="_phase1_test.db")
        os.close(cls.test_db_fd)

        # Set Flask app to testing mode pointing to temp DB
        cls.app = create_app("testing")
        cls.app.config["DATABASE_PATH"] = cls.test_db_path
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        with cls.app.app_context():
            init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except OSError:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            # Create distinct test users
            self.user1_id = create_user("Alice Traveler", "alice_test@test.local", "Password123!", role="user")
            self.user2_id = create_user("Bob Intruder", "bob_test@test.local", "Password123!", role="user")

            # Alice creates a private trip
            self.trip1_id = create_trip(self.user1_id, {
                "destination": "Mysore",
                "start_date": "2026-11-01",
                "end_date": "2026-11-03",
                "num_days": 3,
                "budget": 15000,
                "num_travelers": 2,
                "travel_style": "comfort",
                "transport": "car",
                "transit_mode": "car",
                "transit_cost": 2500,
                "arrival_time": "11:00",
                "interests": ["heritage", "culture"],
                "special_requirements": []
            })

    def tearDown(self):
        with self.app.app_context():
            from backend.database.db import execute_query
            execute_query("DELETE FROM expenses")
            execute_query("DELETE FROM saved_trips")
            execute_query("DELETE FROM trips")
            execute_query("DELETE FROM users")

    def _login_as(self, client, user_id: int, name: str, email: str, role: str = "user"):
        """Simulate an active logged-in session."""
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = name
            sess["user_email"] = email
            sess["user_role"] = role

    # ─────────────────────────────────────────────────────────────
    # 1. Expense IDOR Protection
    # ─────────────────────────────────────────────────────────────

    def test_expense_idor_cross_user_add_rejected(self):
        """User B (Bob) must not be allowed to add an expense to User A's (Alice) trip."""
        bob_client = self.app.test_client()
        self._login_as(bob_client, self.user2_id, "Bob Intruder", "bob_test@test.local")

        resp = bob_client.post(f"/planner/{self.trip1_id}/expense", data={
            "category": "activities",
            "amount": "9999",
            "description": "Unauthorized Bob expense"
        }, follow_redirects=False)

        # Must reject with redirect to dashboard (access denied)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers.get("Location", ""))

        # Verify expense was NOT recorded in database
        with self.app.app_context():
            expenses = get_expenses(self.trip1_id)
            bob_expenses = [e for e in expenses if e["description"] == "Unauthorized Bob expense"]
            self.assertEqual(len(bob_expenses), 0, "Bob's unauthorized expense was saved!")

    def test_expense_idor_cross_user_delete_rejected(self):
        """User B (Bob) must not be allowed to delete an expense from User A's (Alice) trip."""
        with self.app.app_context():
            exp_id = add_expense(self.trip1_id, "food", 450.0, "Alice genuine lunch")

        bob_client = self.app.test_client()
        self._login_as(bob_client, self.user2_id, "Bob Intruder", "bob_test@test.local")

        resp = bob_client.post(f"/planner/{self.trip1_id}/expense/{exp_id}/delete", follow_redirects=False)

        # Must reject with redirect to dashboard
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers.get("Location", ""))

        # Verify expense still exists
        with self.app.app_context():
            expenses = get_expenses(self.trip1_id)
            self.assertTrue(any(e["id"] == exp_id for e in expenses), "Expense was deleted by Bob!")

    def test_expense_legitimate_owner_can_add_and_delete(self):
        """Alice (legitimate owner) can add and delete expenses on her own trip."""
        alice_client = self.app.test_client()
        self._login_as(alice_client, self.user1_id, "Alice Traveler", "alice_test@test.local")

        # Add expense
        add_resp = alice_client.post(f"/planner/{self.trip1_id}/expense", data={
            "category": "food",
            "amount": "750",
            "description": "Mysore Thali"
        }, follow_redirects=False)
        self.assertEqual(add_resp.status_code, 302)
        self.assertIn(f"/planner/{self.trip1_id}", add_resp.headers.get("Location", ""))

        # Verify expense exists
        with self.app.app_context():
            expenses = get_expenses(self.trip1_id)
            added = [e for e in expenses if e["description"] == "Mysore Thali"]
            self.assertEqual(len(added), 1)
            exp_id = added[0]["id"]

        # Delete expense
        del_resp = alice_client.post(f"/planner/{self.trip1_id}/expense/{exp_id}/delete", follow_redirects=False)
        self.assertEqual(del_resp.status_code, 302)
        self.assertIn(f"/planner/{self.trip1_id}", del_resp.headers.get("Location", ""))

        with self.app.app_context():
            expenses_after = get_expenses(self.trip1_id)
            self.assertFalse(any(e["id"] == exp_id for e in expenses_after))

    # ─────────────────────────────────────────────────────────────
    # 2. Trip Access Control
    # ─────────────────────────────────────────────────────────────

    def test_unauthorized_user_cannot_view_private_trip(self):
        """User B (Bob) cannot view Alice's private trip via /planner/<trip_id>."""
        bob_client = self.app.test_client()
        self._login_as(bob_client, self.user2_id, "Bob Intruder", "bob_test@test.local")

        resp = bob_client.get(f"/planner/{self.trip1_id}", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers.get("Location", ""))

    def test_owner_can_view_trip(self):
        """Alice (owner) can view her trip via /planner/<trip_id>."""
        alice_client = self.app.test_client()
        self._login_as(alice_client, self.user1_id, "Alice Traveler", "alice_test@test.local")

        resp = alice_client.get(f"/planner/{self.trip1_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Mysore", resp.get_data(as_text=True))

    # ─────────────────────────────────────────────────────────────
    # 3. Cryptographically Unguessable Share Tokens & Explicit Controls
    # ─────────────────────────────────────────────────────────────

    def test_token_sharing_lifecycle(self):
        """Trips default to private; explicit toggle generates token and allows public viewing."""
        with self.app.app_context():
            trip = get_trip_by_id(self.trip1_id)
            share_token = trip["share_token"]
            self.assertEqual(trip["is_public"], 0, "Trip must default to is_public=0")
            self.assertGreaterEqual(len(share_token), 16, "Share token must be cryptographically long")

        anon_client = self.app.test_client()

        # 1. Accessing private trip via token before sharing is enabled redirects to home
        resp1 = anon_client.get(f"/planner/share/{share_token}", follow_redirects=False)
        self.assertEqual(resp1.status_code, 302)
        self.assertEqual(resp1.headers.get("Location"), "/")

        # 2. Alice toggles sharing ON
        alice_client = self.app.test_client()
        self._login_as(alice_client, self.user1_id, "Alice Traveler", "alice_test@test.local")
        toggle_on_resp = alice_client.post(f"/planner/{self.trip1_id}/share/toggle")
        self.assertEqual(toggle_on_resp.status_code, 200)
        data_on = toggle_on_resp.get_json()
        self.assertTrue(data_on["success"])
        self.assertTrue(data_on["is_public"])
        self.assertIn(share_token, data_on["share_url"])

        # 3. Anonymous visitor can now view the shared trip with token
        resp2 = anon_client.get(f"/planner/share/{share_token}")
        self.assertEqual(resp2.status_code, 200)
        content = resp2.get_data(as_text=True)
        self.assertIn("Mysore", content)
        # Public viewer should not see owner-only controls (like Delete Trip button)
        self.assertNotIn("Delete Trip", content)

        # 4. Bob cannot toggle Alice's trip sharing
        bob_client = self.app.test_client()
        self._login_as(bob_client, self.user2_id, "Bob Intruder", "bob_test@test.local")
        bob_toggle = bob_client.post(f"/planner/{self.trip1_id}/share/toggle")
        self.assertEqual(bob_toggle.status_code, 404)

        # 5. Alice toggles sharing OFF
        toggle_off_resp = alice_client.post(f"/planner/{self.trip1_id}/share/toggle")
        self.assertEqual(toggle_off_resp.status_code, 200)
        data_off = toggle_off_resp.get_json()
        self.assertTrue(data_off["success"])
        self.assertFalse(data_off["is_public"])

        # 6. Anonymous visitor is once again blocked
        resp3 = anon_client.get(f"/planner/share/{share_token}", follow_redirects=False)
        self.assertEqual(resp3.status_code, 302)
        self.assertEqual(resp3.headers.get("Location"), "/")

    def test_invalid_share_token_rejected(self):
        """Invalid or forged share token redirects safely to home."""
        anon_client = self.app.test_client()
        resp = anon_client.get("/planner/share/non_existent_fake_token_12345", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers.get("Location"), "/")

    # ─────────────────────────────────────────────────────────────
    # 4. Safe Handling of Legacy Numeric Share URLs
    # ─────────────────────────────────────────────────────────────

    def test_legacy_numeric_share_url_blocks_enumeration(self):
        """Sequential numeric share links /planner/share/<int> must reject third-party scrapers."""
        anon_client = self.app.test_client()
        resp = anon_client.get(f"/planner/share/{self.trip1_id}", follow_redirects=False)

        # Must redirect to home, never returning private trip details
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers.get("Location"), "/")

    def test_legacy_numeric_share_url_owner_redirect(self):
        """If the owner accidentally visits their own legacy numeric share link, redirect safely."""
        alice_client = self.app.test_client()
        self._login_as(alice_client, self.user1_id, "Alice Traveler", "alice_test@test.local")

        resp = alice_client.get(f"/planner/share/{self.trip1_id}", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/planner/{self.trip1_id}", resp.headers.get("Location", ""))

    # ─────────────────────────────────────────────────────────────
    # 5. Guest Session Isolation
    # ─────────────────────────────────────────────────────────────

    def test_guest_sessions_are_isolated(self):
        """Two anonymous visitors must receive distinct, isolated guest accounts."""
        client_guest1 = self.app.test_client()
        client_guest2 = self.app.test_client()

        # Visitor 1 hits /welcome
        resp1 = client_guest1.get("/welcome")
        self.assertEqual(resp1.status_code, 200)
        with client_guest1.session_transaction() as s1:
            g1_id = s1.get("user_id")
            g1_role = s1.get("user_role")

        # Visitor 2 hits /welcome
        resp2 = client_guest2.get("/welcome")
        self.assertEqual(resp2.status_code, 200)
        with client_guest2.session_transaction() as s2:
            g2_id = s2.get("user_id")
            g2_role = s2.get("user_role")

        self.assertIsNotNone(g1_id)
        self.assertIsNotNone(g2_id)
        self.assertEqual(g1_role, "guest")
        self.assertEqual(g2_role, "guest")
        self.assertNotEqual(g1_id, g2_id, "Guest 1 and Guest 2 must have distinct user IDs!")

        # Verify Guest 1 cannot access Alice's trip
        g1_view = client_guest1.get(f"/planner/{self.trip1_id}", follow_redirects=False)
        self.assertEqual(g1_view.status_code, 302)

    # ─────────────────────────────────────────────────────────────
    # 6. Route Integrity & Compatibility Aliases
    # ─────────────────────────────────────────────────────────────

    def test_destinations_route_redirect(self):
        """GET /destinations must redirect to /planner/destinations (302) and resolve cleanly (200)."""
        anon_client = self.app.test_client()
        resp = anon_client.get("/destinations", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/planner/destinations", resp.headers.get("Location", ""))

        # Verify target resolves cleanly
        target_resp = anon_client.get("/planner/destinations")
        self.assertEqual(target_resp.status_code, 200)

    def test_wizard_and_new_route_aliases(self):
        """GET /wizard redirects to /planner/wizard and GET /new redirects to /planner/new."""
        alice_client = self.app.test_client()
        self._login_as(alice_client, self.user1_id, "Alice Traveler", "alice_test@test.local")

        resp_wiz = alice_client.get("/wizard", follow_redirects=False)
        self.assertEqual(resp_wiz.status_code, 302)
        self.assertIn("/planner/wizard", resp_wiz.headers.get("Location", ""))

        resp_new = alice_client.get("/new", follow_redirects=False)
        self.assertEqual(resp_new.status_code, 302)
        self.assertIn("/planner/new", resp_new.headers.get("Location", ""))


if __name__ == "__main__":
    unittest.main()
