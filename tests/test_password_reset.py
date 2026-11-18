import pytest
import time
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from debunkit_app import app, generate_password_reset_token, verify_password_reset_token
from Core.database import db
from Core.user_model import User


@pytest.fixture
def client():
    from debunkit_app import limiter
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    orig_limiter_state = limiter.enabled
    limiter.enabled = False

    orig_engines = db._app_engines.get(app)
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    db._app_engines[app] = {None: test_engine}

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

    if orig_engines:
        db._app_engines[app] = orig_engines
    limiter.enabled = orig_limiter_state


def create_test_user(username="testreset", email="reset@example.com", password="Password123!"):
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


class TestPasswordReset:
    def test_unknown_email_returns_identical_response(self, client):
        """Avoid account enumeration: unknown email gets exact same success response."""
        res = client.post("/forgot-password", json={"email": "nonexistent@example.com"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert "If that email is registered" in data["message"]

    def test_registered_email_returns_success_and_logs_in_dev(self, client, caplog):
        user = create_test_user()
        with caplog.at_level("INFO"):
            res = client.post("/forgot-password", json={"email": user.email})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        # Reset link is logged in dev / test when SMTP unset
        assert any("Password reset link for reset@example.com:" in record.message for record in caplog.records)

    def test_reset_link_not_logged_in_production(self, client, caplog):
        user = create_test_user()
        with patch.dict("os.environ", {"FLASK_ENV": "production"}):
            with caplog.at_level("INFO"):
                res = client.post("/forgot-password", json={"email": user.email})
        assert res.status_code == 200
        assert not any("Password reset link" in record.message for record in caplog.records)

    def test_smtp_delivery_when_env_configured(self, client):
        user = create_test_user()
        with patch.dict("os.environ", {"SMTP_HOST": "smtp.testmail.local", "SMTP_USER": "u", "SMTP_PASSWORD": "p"}):
            with patch("smtplib.SMTP") as mock_smtp:
                server_instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = server_instance
                res = client.post("/forgot-password", json={"email": user.email})
                assert res.status_code == 200
                server_instance.send_message.assert_called_once()

    def test_valid_token_resets_password_and_authenticates(self, client):
        user = create_test_user(password="OldPassword123!")
        token = generate_password_reset_token(user)

        # GET form works
        get_res = client.get(f"/reset-password/{token}")
        assert get_res.status_code == 200
        assert b"RESET PASSWORD" in get_res.data

        # POST new password
        post_res = client.post(f"/reset-password/{token}", json={"password": "NewSecretPass456!"})
        assert post_res.status_code == 200
        assert post_res.get_json()["status"] == "success"

        # Verify new password works
        db.session.expire_all()
        updated_user = db.session.get(User, user.id)
        assert updated_user.check_password("NewSecretPass456!")
        assert not updated_user.check_password("OldPassword123!")

    def test_expired_token_rejected(self, client):
        user = create_test_user()
        token = generate_password_reset_token(user)

        # Directly verify expiration logic via negative max_age
        assert verify_password_reset_token(token, max_age=-1) is None

        # Expired token in route
        with patch("debunkit_app.verify_password_reset_token", return_value=None):
            res = client.post(f"/reset-password/{token}", json={"password": "NewSecretPass456!"})
            assert res.status_code == 400
            assert "Invalid or expired" in res.get_json()["error"]

    def test_reused_token_rejected(self, client):
        """Once reset, the token bound to old pw_hash cannot be used again."""
        user = create_test_user(password="InitialPass123!")
        token = generate_password_reset_token(user)

        # First use succeeds
        res1 = client.post(f"/reset-password/{token}", json={"password": "ChangedPass123!"})
        assert res1.status_code == 200

        # Second use with same token fails
        res2 = client.post(f"/reset-password/{token}", json={"password": "AnotherPass789!"})
        assert res2.status_code == 400
        assert "Invalid or expired" in res2.get_json()["error"]
