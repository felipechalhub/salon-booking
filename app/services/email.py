"""
Email notification service via Resend.
All functions are fire-and-forget (called with asyncio.create_task).
"""
import asyncio
import logging
from datetime import datetime

import resend

from app.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key


def _build_confirmation_html(
    client_name: str,
    service_name: str,
    staff_name: str,
    slot_display: str,
    appointment_id: int,
) -> str:
    return f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>Your appointment is confirmed!</h2>
      <p>Hi {client_name},</p>
      <p>Here are your booking details:</p>
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px 0; color: #666;">Service</td>
          <td style="padding: 8px 0;"><strong>{service_name}</strong></td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #666;">With</td>
          <td style="padding: 8px 0;"><strong>{staff_name}</strong></td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #666;">When</td>
          <td style="padding: 8px 0;"><strong>{slot_display}</strong></td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #666;">Booking ref</td>
          <td style="padding: 8px 0;">#{appointment_id}</td>
        </tr>
      </table>
      <p style="margin-top: 24px; color: #666; font-size: 0.9em;">
        Need to reschedule? Reply to this email or contact us directly.
      </p>
    </div>
    """


async def send_booking_confirmation(
    to_email: str,
    client_name: str,
    service_name: str,
    staff_name: str,
    slot_display: str,
    appointment_id: int,
) -> None:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email.")
        return

    try:
        params = {
            "from": settings.resend_from,
            "to": [to_email],
            "subject": f"Booking confirmed: {service_name} on {slot_display}",
            "html": _build_confirmation_html(
                client_name, service_name, staff_name, slot_display, appointment_id
            ),
        }
        # resend.Emails.send is synchronous, run in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: resend.Emails.send(params)
        )
        logger.info("Confirmation email sent to %s", to_email)
    except Exception:
        # Never let email failure break the booking
        logger.exception("Failed to send confirmation email to %s", to_email)