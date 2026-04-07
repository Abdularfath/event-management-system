"""
QR Code generation utility with Cloudinary upload support.
Generates QR codes for event check-in and uploads them to Cloudinary.
"""

import logging
import os
from io import BytesIO

import cloudinary
import cloudinary.uploader
import qrcode
from dotenv import load_dotenv
from qrcode.constants import ERROR_CORRECT_H

load_dotenv()

logger = logging.getLogger(__name__)

# ── Module-level constants ───────────────────────────────────────────────────
QR_CODE_SIZE = 300  # Width and height in pixels


def _configure_cloudinary():
    """Configure Cloudinary from environment variables, raising if any are missing."""
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')

    missing = [
        name for name, val in (
            ('CLOUDINARY_CLOUD_NAME', cloud_name),
            ('CLOUDINARY_API_KEY', api_key),
            ('CLOUDINARY_API_SECRET', api_secret),
        )
        if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required Cloudinary environment variable(s): {', '.join(missing)}"
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
    )


def generate_and_upload_qr_code(registration_id: str, checkin_url: str) -> str:
    """
    Generate a QR code and upload to Cloudinary.

    Args:
        registration_id: Unique registration ID
        checkin_url: Check-in verification URL

    Returns:
        str: Public URL of uploaded QR code on Cloudinary

    Raises:
        EnvironmentError: If required Cloudinary environment variables are missing.
        ValueError: If the Cloudinary upload response does not contain a secure URL.
        Exception: If QR generation or the Cloudinary upload fails for any other reason.
    """
    # Ensure Cloudinary is configured before every call (idempotent after first call)
    _configure_cloudinary()

    # ── Step 1: Generate QR code image ──────────────────────────────────
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(checkin_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')

    # Resize to QR_CODE_SIZE × QR_CODE_SIZE pixels
    img = img.resize((QR_CODE_SIZE, QR_CODE_SIZE))

    # ── Step 2: Write image to an in-memory buffer ───────────────────────
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # ── Step 3: Upload to Cloudinary ─────────────────────────────────────
    try:
        upload_result = cloudinary.uploader.upload(
            buffer,
            folder='event-management/qrcodes',
            public_id=f'qr_{registration_id}',
            overwrite=True,
            resource_type='image',
            format='png',
        )
        qr_url = upload_result.get('secure_url')
        if not qr_url:
            raise ValueError(
                f'Cloudinary upload response missing secure_url for registration {registration_id}'
            )
        logger.info(
            '[QR] Uploaded QR code for registration %s: %s',
            registration_id, qr_url,
        )
        return qr_url
    except Exception as e:
        logger.error(
            '[QR] Cloudinary upload failed for registration %s: %s',
            registration_id, str(e),
        )
        raise
