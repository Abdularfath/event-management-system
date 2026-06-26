import os
import hmac
import hashlib
import qrcode
from io import BytesIO
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

def generate_qr_payload(registration_id, event_id):
    """Generates a secure HMAC-signed payload for the QR code."""
    secret = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key').encode('utf-8')
    base_string = f"reg:{registration_id}:ev:{event_id}"
    
    signature = hmac.new(secret, base_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{base_string}:sig:{signature}"

def generate_and_upload_qr(registration_id, event_id):
    """
    Generates a QR code image in memory and uploads it to Cloudinary.
    Returns: (cloudinary_url, qr_payload)
    """
    try:
        # 1. Generate the secure payload
        qr_payload = generate_qr_payload(registration_id, event_id)
        
        # 2. Create the QR Code image in memory
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save image to a bytes buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # 3. Upload to Cloudinary
        print(f"[DEBUG] Uploading QR to Cloudinary for Reg: {registration_id}")
        upload_result = cloudinary.uploader.upload(
            buffer,
            folder="ems_qr_codes",
            public_id=f"qr_{registration_id}",
            overwrite=True,
            resource_type="image"
        )
        
        # 4. Get the secure URL
        secure_url = upload_result.get('secure_url')
        print(f"[DEBUG] Cloudinary Upload Success: {secure_url}")
        
        return secure_url, qr_payload
        
    except Exception as e:
        print(f"[ERROR] QR Generation/Upload failed: {str(e)}")
        return None, None
def verify_qr_payload(payload):
    """
    Verifies the HMAC signature of a QR payload.
    Format: reg:{reg_id}:ev:{ev_id}:sig:{signature}
    Returns: (is_valid, reg_id, ev_id)
    """
    try:
        parts = payload.split(':')
        if len(parts) != 6 or parts[0] != 'reg' or parts[2] != 'ev' or parts[4] != 'sig':
            return False, None, None
        
        reg_id = parts[1]
        ev_id = parts[3]
        provided_signature = parts[5]
        
        secret = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key').encode('utf-8')
        base_string = f"reg:{reg_id}:ev:{ev_id}"
        expected_signature = hmac.new(secret, base_string.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Constant-time comparison prevents timing attacks
        if hmac.compare_digest(provided_signature, expected_signature):
            return True, reg_id, ev_id
        
        return False, None, None
    except Exception as e:
        print(f"[ERROR] QR Verification failed: {e}")
        return False, None, None    