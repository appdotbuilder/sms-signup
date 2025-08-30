"""Mobile-first phone verification UI."""

import re
from nicegui import ui, app
from app.phone_verification_service import phone_verification_service
from app.user_service import user_service
from app.models import VerificationStatus


def create():
    """Create phone verification pages."""

    @ui.page("/phone-verification")
    async def phone_verification_page():
        """Mobile-optimized phone verification page."""
        await ui.context.client.connected()

        # Check if user is authenticated
        user_id = app.storage.tab.get("user_id")
        if not user_id:
            ui.navigate.to("/auth")
            return

        user = user_service.get_user_by_id(user_id)
        if user is None:
            ui.navigate.to("/auth")
            return

        # Check if phone is already verified
        if user.is_phone_verified and user.phone_number:
            ui.navigate.to("/verification-complete")
            return

        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50"):
            # Header
            with ui.row().classes("w-full justify-center mb-6 mt-4"):
                ui.icon("phone", size="3rem", color="primary")

            ui.label(f"Hi {user.first_name}!").classes("text-2xl font-bold text-center text-gray-800 mb-2")
            ui.label("Verify your phone number").classes("text-gray-600 text-center mb-6")

            # Phone verification card
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                ui.label("Enter your phone number").classes("text-lg font-semibold text-gray-700 mb-4")

                # Phone input
                phone_input = (
                    ui.input(label="Phone Number", placeholder="+1 (555) 123-4567")
                    .classes("w-full mb-4")
                    .props("type=tel")
                )

                # Format phone as user types
                def format_phone_input():
                    if phone_input.value:
                        # Remove all non-digit characters except +
                        digits = re.sub(r"[^\d+]", "", phone_input.value)

                        # Format US phone numbers
                        if digits.startswith("+1") and len(digits) > 2:
                            # +1 (123) 456-7890 format
                            base = digits[2:]  # Remove +1
                            if len(base) >= 6:
                                formatted = f"+1 ({base[:3]}) {base[3:6]}-{base[6:10]}"
                            elif len(base) >= 3:
                                formatted = f"+1 ({base[:3]}) {base[3:]}"
                            else:
                                formatted = f"+1 {base}"
                            phone_input.value = formatted
                        elif digits.startswith("1") and len(digits) == 11:
                            # Convert 1XXXXXXXXXX to +1 format
                            base = digits[1:]
                            formatted = f"+1 ({base[:3]}) {base[3:6]}-{base[6:10]}"
                            phone_input.value = formatted
                        elif len(digits) == 10:
                            # Convert XXXXXXXXXX to +1 format
                            formatted = f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:10]}"
                            phone_input.value = formatted

                phone_input.on("input", format_phone_input)

                # Error message area
                error_message = ui.label("").classes("text-red-500 text-sm mb-2").style("display: none")

                # Send code button
                async def send_verification_code():
                    if not phone_input.value:
                        error_message.set_text("Please enter your phone number")
                        error_message.style("display: block")
                        return

                    # Validate phone number format
                    phone_clean = re.sub(r"[^\d+]", "", phone_input.value)
                    if not re.match(r"^\+?1?[0-9]{10,15}$", phone_clean):
                        error_message.set_text("Please enter a valid phone number")
                        error_message.style("display: block")
                        return

                    error_message.style("display: none")

                    # Send verification code
                    verification = phone_verification_service.send_verification_code(user, phone_input.value)
                    if verification:
                        # Store phone number in tab storage
                        app.storage.tab["verification_phone"] = phone_input.value
                        # Navigate to code entry
                        ui.navigate.to("/verify-code")
                    else:
                        error_message.set_text("Unable to send verification code. Please try again.")
                        error_message.style("display: block")

                ui.button("Send Verification Code", on_click=send_verification_code).classes(
                    "w-full bg-primary text-white px-4 py-3 rounded-lg font-medium mb-4"
                )

                # Info about SMS
                with ui.row().classes("w-full p-3 bg-blue-50 rounded-lg"):
                    ui.icon("info", size="sm", color="primary")
                    ui.label("We'll send you a 6-digit code via SMS").classes("text-sm text-blue-700 ml-2")

    @ui.page("/verify-code")
    async def verify_code_page():
        """Mobile-optimized code verification page."""
        await ui.context.client.connected()

        # Check authentication and phone number
        user_id = app.storage.tab.get("user_id")
        verification_phone = app.storage.tab.get("verification_phone")

        if not user_id or not verification_phone:
            ui.navigate.to("/phone-verification")
            return

        user = user_service.get_user_by_id(user_id)
        if user is None:
            ui.navigate.to("/auth")
            return

        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50"):
            # Header
            with ui.row().classes("w-full justify-center mb-6 mt-4"):
                ui.icon("sms", size="3rem", color="primary")

            ui.label("Verify Your Phone").classes("text-2xl font-bold text-center text-gray-800 mb-2")
            ui.label(f"Enter the code sent to {verification_phone}").classes("text-gray-600 text-center mb-6")

            # Verification card
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                ui.label("Verification Code").classes("text-lg font-semibold text-gray-700 mb-4")

                # Code input
                code_input = (
                    ui.input(label="6-Digit Code", placeholder="000000")
                    .classes("w-full mb-4 text-center text-2xl")
                    .props("type=tel maxlength=6")
                )

                # Auto-format and limit code input
                def format_code_input():
                    if code_input.value:
                        # Only allow digits and limit to 6 characters
                        digits = re.sub(r"[^\d]", "", code_input.value)[:6]
                        code_input.value = digits

                code_input.on("input", format_code_input)

                # Error/status message
                status_message = ui.label("").classes("text-sm mb-4").style("display: none")

                # Verify button
                async def verify_code():
                    if not code_input.value or len(code_input.value) != 6:
                        status_message.set_text("Please enter the complete 6-digit code")
                        status_message.classes("text-red-500")
                        status_message.style("display: block")
                        return

                    # Verify the code
                    success, verification, message = phone_verification_service.verify_code(
                        user, verification_phone, code_input.value
                    )

                    if success:
                        # Success! Navigate to completion page
                        ui.navigate.to("/verification-complete")
                    else:
                        # Show error message
                        status_message.set_text(message)
                        status_message.classes("text-red-500")
                        status_message.style("display: block")

                        # Clear the input for retry
                        code_input.value = ""

                        # If maximum attempts reached, redirect back to phone entry
                        if verification and verification.status == VerificationStatus.FAILED:
                            app.storage.tab.pop("verification_phone", None)
                            ui.timer(2.0, lambda: ui.navigate.to("/phone-verification"))

                ui.button("Verify Code", on_click=verify_code).classes(
                    "w-full bg-primary text-white px-4 py-3 rounded-lg font-medium mb-4"
                )

                # Resend code option
                async def resend_code():
                    verification = phone_verification_service.send_verification_code(user, verification_phone)
                    if verification:
                        status_message.set_text("New code sent!")
                        status_message.classes("text-green-600")
                        status_message.style("display: block")
                        code_input.value = ""
                        # Hide message after 3 seconds
                        ui.timer(3.0, lambda: status_message.style("display: none"))
                    else:
                        status_message.set_text("Unable to resend code. Please try again.")
                        status_message.classes("text-red-500")
                        status_message.style("display: block")

                ui.button("Resend Code", on_click=resend_code).classes(
                    "w-full border border-gray-300 text-gray-700 px-4 py-2 rounded-lg"
                ).props("outline")

                # Back button
                ui.button("Change Phone Number", on_click=lambda: ui.navigate.to("/phone-verification")).classes(
                    "w-full text-gray-500 mt-2"
                ).props("flat")

    @ui.page("/verification-complete")
    async def verification_complete():
        """Mobile-optimized verification completion page."""
        await ui.context.client.connected()

        # Check if user is authenticated and verified
        user_id = app.storage.tab.get("user_id")
        if not user_id:
            ui.navigate.to("/auth")
            return

        user = user_service.get_user_by_id(user_id)
        if user is None:
            ui.navigate.to("/auth")
            return

        if not user.is_phone_verified:
            ui.navigate.to("/phone-verification")
            return

        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50 text-center"):
            # Success animation/icon
            with ui.row().classes("w-full justify-center mb-8 mt-16"):
                ui.icon("check_circle", size="4rem", color="positive")

            ui.label("Thank you for verifying your phone number.").classes("text-2xl font-bold text-gray-800 mb-6")

            # Success card
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl bg-green-50 border border-green-200"):
                ui.label("🎉 All Set!").classes("text-lg font-semibold text-green-800 mb-2")
                ui.label(f"Your phone number {user.phone_number} has been successfully verified.").classes(
                    "text-green-700 mb-4"
                )
                ui.label("You're now ready to receive SMS notifications from our service.").classes("text-green-600")

            # Action buttons
            with ui.column().classes("w-full mt-8 gap-3"):
                ui.button("Continue to Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).classes(
                    "w-full bg-primary text-white px-4 py-3 rounded-lg font-medium"
                )

                ui.button("Sign Out", on_click=lambda: ui.navigate.to("/auth/logout")).classes(
                    "w-full border border-gray-300 text-gray-700 px-4 py-2 rounded-lg"
                ).props("outline")

    @ui.page("/dashboard")
    async def dashboard():
        """Simple dashboard for verified users."""
        await ui.context.client.connected()

        # Check if user is authenticated and verified
        user_id = app.storage.tab.get("user_id")
        if not user_id:
            ui.navigate.to("/auth")
            return

        user = user_service.get_user_by_id(user_id)
        if user is None:
            ui.navigate.to("/auth")
            return

        if not user.is_phone_verified:
            ui.navigate.to("/phone-verification")
            return

        with ui.column().classes("w-full max-w-sm mx-auto p-6 min-h-screen bg-gray-50"):
            # Header with user info
            with ui.row().classes("w-full justify-between items-center mb-6 mt-4"):
                ui.label(f"Hello, {user.first_name}!").classes("text-xl font-bold text-gray-800")
                ui.button(icon="logout", on_click=lambda: ui.navigate.to("/auth/logout")).classes(
                    "text-gray-600"
                ).props("flat round")

            # Status card
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl mb-4"):
                with ui.row().classes("items-center mb-3"):
                    ui.icon("verified", size="md", color="positive")
                    ui.label("SMS Service Active").classes("text-lg font-semibold text-gray-800 ml-2")

                ui.label(f"Phone: {user.phone_number}").classes("text-gray-600 mb-2")
                ui.label(f"Email: {user.email}").classes("text-gray-600 mb-2")
                ui.label("Status: Verified ✅").classes("text-green-600 font-medium")

            # Service info
            with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                ui.label("What's Next?").classes("text-lg font-semibold text-gray-800 mb-3")
                ui.label(
                    "Your phone number is verified and you'll start receiving SMS notifications based on your preferences."
                ).classes("text-gray-600 leading-relaxed")
