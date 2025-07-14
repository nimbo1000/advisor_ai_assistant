from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import html2text
from google.oauth2.credentials import Credentials
from .vectorstore import add_documents_to_vectorstore
# Management command for polling Gmail for all users
import logging
from django.contrib.auth import get_user_model


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


def fetch_gmail_messages(creds_data, user_id, since_history_id=None, max_results=100):
    """
    Fetch Gmail messages for a user. If since_history_id is provided, only fetch messages since that history ID.
    Always stores emails to the vectorstore.
    Returns (messages, last_history_id)
    """
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data['refresh_token'],
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )
    service = build('gmail', 'v1', credentials=creds)
    user = 'me'
    # Get the latest historyId for future polling
    profile = service.users().getProfile(userId=user).execute()
    last_history_id = profile.get('historyId')
    # Fetch messages
    if since_history_id:
        # Use history API to get new messages since last_history_id
        history = service.users().history().list(userId=user, startHistoryId=since_history_id, historyTypes=['messageAdded'], maxResults=max_results).execute()
        message_ids = []
        for h in history.get('history', []):
            for m in h.get('messagesAdded', []):
                message_ids.append(m['message']['id'])
    else:
        # Fetch most recent messages
        results = service.users().messages().list(userId=user, maxResults=max_results).execute()
        message_ids = [msg['id'] for msg in results.get('messages', [])]
    full_messages = []
    docs = []
    for msg_id in message_ids:
        email = get_full_message(service, user, msg_id)
        body = email.get('body', '')
        if '<' in body and '>' in body:
            body_text = html2text.html2text(body)
        else:
            body_text = body
        full_messages.append(email)
        docs.append({
            'text': body_text,
            'external_id': email['id'],
            'subject': email.get('subject'),
            'from': email.get('from'),
            'to': email.get('to'),
            'date': email.get('date'),
            'type': 'email',
        })
    print(f"FETCHED emails for {user_id}, docs {docs}")
    if user_id and docs:
        add_documents_to_vectorstore(user_id, docs, source='gmail')
    return full_messages, last_history_id


def get_full_message(service, user_id, msg_id):
    message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
    headers = message['payload'].get('headers', [])
    header_dict = {h['name']: h['value'] for h in headers}
    subject = header_dict.get('Subject')
    sender = header_dict.get('From')
    to = header_dict.get('To')
    date = header_dict.get('Date')
    # Extract body (plain text or html)
    body = ""
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    else:
        body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
    return {
        'id': msg_id,
        'subject': subject,
        'from': sender,
        'to': to,
        'date': date,
        'body': body,
    }

# Management command for polling Gmail for all users
def poll_gmail_for_all_users():
    from .models import GmailPollingState
    User = get_user_model()
    for user in User.objects.all():
        try:
            polling_state, _ = GmailPollingState.objects.get_or_create(user=user)
            creds_data = polling_state.get_google_credentials()
            # If credentials are not available, skip
            if not creds_data:
                continue
            since_history_id = polling_state.last_history_id
            _, last_history_id = fetch_gmail_messages(creds_data, user.id, since_history_id=since_history_id)
            polling_state.last_history_id = last_history_id
            polling_state.save()
        except Exception as e:
            logging.exception(f"Failed to poll Gmail for user {user.id}: {e}") 