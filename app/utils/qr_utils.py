import hmac, hashlib, os
import qrcode
from io import BytesIO
import base64
 
# ── QR payload format ────────────────────────────────────────────────
# reg:{registration_id}:ev:{event_id}:sig:{hmac_signature}
# Example: reg:ABC123:ev:XYZ789:sig:a1b2c3d4e5f6...
 
 
def _get_secret():
    secret = os.getenv('QR_HMAC_SECRET','dev-secret-change-in-production')
    return secret.encode()
 
 
def build_qr_payload(registration_id, event_id):
    """Build a signed payload string for a registration QR code."""
    raw = f'reg:{registration_id}:ev:{event_id}'
    sig = hmac.new(_get_secret(),raw.encode(),hashlib.sha256).hexdigest()
    return f'{raw}:sig:{sig}'
 
 
def verify_qr_payload(payload):
    """
    Verify a scanned QR payload.
    Returns (registration_id, event_id) if valid, or (None, None) if invalid.
    """
    try:
        # Expected format: reg:{reg_id}:ev:{ev_id}:sig:{signature}
        parts = payload.split(':')
        # parts = ['reg', reg_id, 'ev', ev_id, 'sig', signature]
        if len(parts) != 6 or parts[0] != 'reg' or parts[2] != 'ev' or parts[4] != 'sig':
            return None, None
 
        registration_id = parts[1]
        event_id        = parts[3]
        received_sig    = parts[5]
 
        # Recompute expected signature
        raw = f'reg:{registration_id}:ev:{event_id}'
        expected_sig = hmac.new(_get_secret(),raw.encode(),hashlib.sha256).hexdigest()
 
        # Constant-time comparison prevents timing attacks
        if not hmac.compare_digest(expected_sig, received_sig):
            return None, None
 
        return registration_id, event_id
 
    except Exception:
        return None, None
 
 
def generate_qr_image_base64(payload):
    """
    Generate a QR code PNG and return as base64 string.
    Used to embed QR codes in HTML pages and emails.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
 
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()
