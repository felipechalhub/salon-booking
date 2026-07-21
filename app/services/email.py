"""
Email notification service via Resend.
All functions are fire-and-forget (called with asyncio.create_task).
"""
import asyncio
import logging

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


def _build_reschedule_html(
    client_name: str,
    service_name: str,
    staff_name: str,
    old_slot_display: str,
    new_slot_display: str,
    appointment_id: int,
) -> str:
    return f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>Your appointment has been rescheduled</h2>
      <p>Hi {client_name},</p>
      <p>Your appointment has been moved to a new time:</p>
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
          <td style="padding: 8px 0; color: #666;">Previous time</td>
          <td style="padding: 8px 0; text-decoration: line-through; color: #999;">{old_slot_display}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #666;">New time</td>
          <td style="padding: 8px 0;"><strong>{new_slot_display}</strong></td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #666;">Booking ref</td>
          <td style="padding: 8px 0;">#{appointment_id}</td>
        </tr>
      </table>
      <p style="margin-top: 24px; color: #666; font-size: 0.9em;">
        Questions? Reply to this email or contact us directly.
      </p>
    </div>
    """


async def _send(params: dict) -> None:
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: resend.Emails.send(params)
    )


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
        await _send({
            "from": settings.resend_from,
            "to": [to_email],
            "subject": f"Booking confirmed: {service_name} on {slot_display}",
            "html": _build_confirmation_html(
                client_name, service_name, staff_name, slot_display, appointment_id
            ),
        })
        logger.info("Confirmation email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send confirmation email to %s", to_email)


async def send_reschedule_notification(
    to_email: str,
    client_name: str,
    service_name: str,
    staff_name: str,
    old_slot_display: str,
    new_slot_display: str,
    appointment_id: int,
) -> None:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email.")
        return
    try:
        await _send({
            "from": settings.resend_from,
            "to": [to_email],
            "subject": f"Appointment rescheduled: {service_name} now on {new_slot_display}",
            "html": _build_reschedule_html(
                client_name, service_name, staff_name,
                old_slot_display, new_slot_display, appointment_id
            ),
        })
        logger.info("Reschedule email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send reschedule email to %s", to_email)