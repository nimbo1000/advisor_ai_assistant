from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def create_google_calendar_event(creds, summary, start, end, attendees=None, description=None, location=None, timezone='UTC'):
    event = {
        'summary': summary,
        'start': {'dateTime': start, 'timeZone': timezone},
        'end': {'dateTime': end, 'timeZone': timezone},
    }
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    if description:
        event['description'] = description
    if location:
        event['location'] = location
    service = build('calendar', 'v3', credentials=creds)
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

def send_gmail_message(creds, to, subject, body, cc=None, bcc=None, attachments=None):
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    if cc:
        message['cc'] = ','.join(cc) if isinstance(cc, list) else cc
    if bcc:
        message['bcc'] = ','.join(bcc) if isinstance(bcc, list) else bcc
    message.attach(MIMEText(body, 'plain'))
    # Attach files if any
    if attachments:
        for file_path in attachments:
            part = MIMEBase('application', 'octet-stream')
            with open(file_path, 'rb') as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={file_path}')
            message.attach(part)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service = build('gmail', 'v1', credentials=creds)
    sent_message = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return sent_message 