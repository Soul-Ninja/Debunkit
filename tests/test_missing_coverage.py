import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from debunkit_app import app, CSRF_SESSION_KEY, limiter
from Core.database import db, Analysis, Review
from Core.user_model import User


@pytest.fixture
def test_db():
    orig_engines = db._app_engines.get(app)
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    db._app_engines[app] = {None: test_engine}

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()

    if orig_engines:
        db._app_engines[app] = orig_engines


class TestCSRFProtection:
    @pytest.mark.parametrize("method,path", [
        ("POST", "/register"),
        ("POST", "/login"),
        ("POST", "/logout"),
        ("POST", "/forgot-password"),
        ("POST", "/reset-password/dummy-token"),
        ("POST", "/analyze"),
        ("POST", "/api/clear-database"),
        ("PUT", "/api/user/profile"),
        ("PUT", "/api/user/settings"),
        ("DELETE", "/api/user/delete"),
        ("POST", "/api/reviews"),
    ])
    def test_unsafe_routes_block_without_csrf_and_allow_with_csrf(self, test_db, method, path):
        orig_testing = app.config.get("TESTING")
        orig_csrf = app.config.get("WTF_CSRF_ENABLED")
        orig_limiter = limiter.enabled

        try:
            app.config["TESTING"] = False
            app.config["WTF_CSRF_ENABLED"] = True
            limiter.enabled = False

            with app.test_client() as client:
                # 1. Unsafe call without CSRF token must return 403
                res_blocked = client.open(path, method=method, json={})
                assert res_blocked.status_code == 403
                assert res_blocked.get_json()["error"] == "Invalid or missing CSRF token"

                # 2. Unsafe call with valid CSRF session token must pass CSRF check (return != 403)
                token = "valid-csrf-token-xyz"
                with client.session_transaction() as sess:
                    sess[CSRF_SESSION_KEY] = token

                res_allowed = client.open(
                    path,
                    method=method,
                    json={},
                    headers={"X-CSRFToken": token}
                )
                assert res_allowed.status_code != 403
        finally:
            app.config["TESTING"] = orig_testing
            app.config["WTF_CSRF_ENABLED"] = orig_csrf
            limiter.enabled = orig_limiter_state if 'orig_limiter_state' in locals() else orig_limiter


class TestAccountLifecycle:
    def test_duplicate_username_returns_400(self, test_db):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        limiter.enabled = False

        with app.test_client() as client:
            res1 = client.post("/register", json={
                "username": "duplicate_user",
                "email": "user1@example.com",
                "password": "Password123!"
            })
            assert res1.status_code == 201

            # Duplicate username with different email
            res2 = client.post("/register", json={
                "username": "duplicate_user",
                "email": "user2@example.com",
                "password": "Password123!"
            })
            assert res2.status_code in (400, 409)
            assert "already taken" in res2.get_json().get("error", "").lower()

    def test_duplicate_email_returns_400(self, test_db):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        limiter.enabled = False

        with app.test_client() as client:
            res1 = client.post("/register", json={
                "username": "unique_user_a",
                "email": "shared@example.com",
                "password": "Password123!"
            })
            assert res1.status_code == 201

            # Duplicate email with different username
            res2 = client.post("/register", json={
                "username": "unique_user_b",
                "email": "shared@example.com",
                "password": "Password123!"
            })
            assert res2.status_code in (400, 409)
            assert "already registered" in res2.get_json().get("error", "").lower()

    def test_deleting_user_cascades_analyses_and_reviews(self, test_db):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        limiter.enabled = False

        with app.test_client() as client:
            # Register & login
            client.post("/register", json={
                "username": "cascade_user",
                "email": "cascade@example.com",
                "password": "SecurePassword123!"
            })
            client.post("/login", json={
                "email": "cascade@example.com",
                "password": "SecurePassword123!"
            })

            user = User.query.filter_by(username="cascade_user").first()
            assert user is not None

            # Create an analysis for this user
            analysis = Analysis(
                text_analyzed="Some fake news claim",
                verdict="REFUTED",
                confidence=90,
                user_id=user.id
            )
            # Create a review authored by this user
            review = Review(
                author_name=user.username,
                rating=5,
                content="Great verification service!"
            )
            db.session.add(analysis)
            db.session.add(review)
            db.session.commit()

            user_id = user.id
            username = user.username

            assert Analysis.query.filter_by(user_id=user_id).count() == 1
            assert Review.query.filter_by(author_name=username).count() == 1

            # Delete account with valid password
            del_res = client.delete("/api/user/delete", json={"password": "SecurePassword123!"})
            assert del_res.status_code == 200

            # Verify user, analysis, and reviews are completely removed
            db.session.expire_all()
            assert db.session.get(User, user_id) is None
            assert Analysis.query.filter_by(user_id=user_id).count() == 0
            assert Review.query.filter_by(author_name=username).count() == 0


class TestRateLimiterSeparation:
    def test_rate_limiting_isolated_by_x_forwarded_for(self, test_db):
        app.config["TESTING"] = True
        orig_limiter_state = limiter.enabled
        try:
            limiter.enabled = True
            limiter.reset()

            with app.test_client() as client:
                ip_blocked = "198.51.100.42"
                ip_fresh = "198.51.100.99"

                # /register is limited to 5 per minute
                for _ in range(5):
                    client.post("/register", json={}, headers={"X-Forwarded-For": ip_blocked})

                # 6th attempt from blocked IP should be rate limited (429)
                res_blocked = client.post("/register", json={}, headers={"X-Forwarded-For": ip_blocked})
                assert res_blocked.status_code == 429
                assert "Too Many Requests" in res_blocked.get_data(as_text=True) or res_blocked.status_code == 429

                # 1st attempt from fresh IP should NOT be rate limited
                res_fresh = client.post("/register", json={}, headers={"X-Forwarded-For": ip_fresh})
                assert res_fresh.status_code != 429
                assert res_fresh.status_code == 400
        finally:
            limiter.enabled = orig_limiter_state
