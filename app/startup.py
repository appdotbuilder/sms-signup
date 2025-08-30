from app.database import create_tables
from nicegui import ui
import app.mobile_auth
import app.mobile_phone_verification


def startup() -> None:
    # this function is called before the first request
    create_tables()

    # Register all modules
    app.mobile_auth.create()
    app.mobile_phone_verification.create()

    @ui.page("/")
    def index():
        """Root page redirects to auth."""
        ui.navigate.to("/auth")
