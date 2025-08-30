"""Mobile-first OAuth authentication UI."""

from nicegui import ui, app
from app.oauth_service import oauth_service
from app.models import OAuthProvider


def create():
    """Create OAuth authentication pages."""

    @ui.page("/auth")
    async def auth_page():
        """Mobile-optimized OAuth sign-in page."""
        # Apply mobile-first theme
        ui.colors(
            primary="#2563eb",
            secondary="#64748b",
            accent="#10b981",
            positive="#10b981",
            negative="#ef4444",
            warning="#f59e0b",
        )

        # Wait for connection to access tab storage
        await ui.context.client.connected()

        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50"):
            # Header
            with ui.row().classes("w-full justify-center mb-8 mt-8"):
                ui.icon("sms", size="3rem", color="primary")

            ui.label("Join Our SMS Service").classes("text-2xl font-bold text-center text-gray-800 mb-2")
            ui.label("Sign in to get started").classes("text-gray-600 text-center mb-8")

            # Sign-in card
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                ui.label("Sign in with your account").classes("text-lg font-semibold text-gray-700 mb-4")

                # OAuth buttons
                def handle_google_signin():
                    # In a real app, this would redirect to Google OAuth
                    # For demo, we'll simulate the callback
                    ui.navigate.to("/auth/callback?code=demo_code&state=demo_state")

                ui.button("Continue with Google", on_click=handle_google_signin).classes(
                    "w-full bg-white border border-gray-300 text-gray-700 px-4 py-3 rounded-lg mb-3 hover:bg-gray-50"
                ).props("icon=account_circle")

                # Demo notice
                with ui.row().classes("w-full mt-4 p-3 bg-blue-50 rounded-lg"):
                    ui.icon("info", size="sm", color="primary")
                    ui.label("Demo Mode: Click button to simulate OAuth flow").classes("text-sm text-blue-700 ml-2")

    @ui.page("/auth/callback")
    async def auth_callback():
        """Handle OAuth callback and redirect to phone verification."""
        # Wait for connection to access tab storage
        await ui.context.client.connected()

        # Simulate OAuth processing
        code = (
            getattr(ui.context.client.request, "query_params", {}).get("code", "") if ui.context.client.request else ""
        )

        if code:
            # Exchange code for tokens (simulated)
            tokens = await oauth_service.exchange_code_for_tokens(code)
            if tokens:
                # Get user info (simulated)
                user_info = await oauth_service.get_user_info(tokens["access_token"])
                if user_info:
                    # Create or update user
                    user = oauth_service.create_or_update_user(user_info, OAuthProvider.GOOGLE)
                    if user and user.id is not None:
                        # Store user info in tab storage
                        app.storage.tab["user_id"] = user.id
                        app.storage.tab["user_email"] = user.email
                        app.storage.tab["user_first_name"] = user.first_name

                        # Redirect to phone verification
                        ui.navigate.to("/phone-verification")
                        return

        # Error case
        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50"):
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl text-center"):
                ui.icon("error", size="3rem", color="negative").classes("mb-4")
                ui.label("Authentication Failed").classes("text-xl font-bold text-gray-800 mb-2")
                ui.label("There was an error signing you in. Please try again.").classes("text-gray-600 mb-4")

                ui.button("Try Again", on_click=lambda: ui.navigate.to("/auth")).classes(
                    "bg-primary text-white px-6 py-2 rounded-lg"
                )

    @ui.page("/auth/logout")
    async def logout():
        """Clear session and redirect to auth."""
        await ui.context.client.connected()

        # Clear all tab storage
        app.storage.tab.clear()

        # Redirect to auth page
        ui.navigate.to("/auth")
