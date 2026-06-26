import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_ticket_email(to_email, subject, html_content):
    """Sends an HTML email using SendGrid."""
    sg_api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_SENDER_EMAIL')
    
    print(f"[DEBUG EMAIL] Starting email send to {to_email}", flush=True)
    print(f"[DEBUG EMAIL] API Key exists: {bool(sg_api_key)}", flush=True)
    print(f"[DEBUG EMAIL] Sender Email: {from_email}", flush=True)
    
    if not sg_api_key or not from_email:
        print("[ERROR EMAIL] SendGrid API Key or Sender Email is missing in .env", flush=True)
        return False

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(sg_api_key)
        response = sg.send(message)
        print(f"[INFO EMAIL] Email sent successfully! Status Code: {response.status_code}", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR EMAIL] Failed to send email: {str(e)}", flush=True)
        # If there's an API error, this prints the exact reason from SendGrid
        if hasattr(e, 'body'):
            print(f"[ERROR EMAIL] SendGrid API Response: {e.body}", flush=True)
        return False