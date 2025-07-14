# Tool stubs for agent actions

from .vectorstore import vectorstore, query_user_documents, add_documents_to_vectorstore
from .utils import create_google_calendar_event
from django.conf import settings
from google.oauth2.credentials import Credentials
from .utils import send_gmail_message
import json

def add_ongoing_instruction(args):
    """
    Args should be a dict or JSON string with at least 'user_id' and 'instruction'.
    """
    if isinstance(args, str):
        args = json.loads(args)
    user_id = args.get('user_id')
    instruction = args.get('instruction')
    if not user_id or not instruction:
        raise ValueError('user_id and instruction are required')
    doc = {
        'text': instruction,
        'external_id': f'instruction:{hash(instruction)}',
        'type': 'ongoing_instruction',
    }
    add_documents_to_vectorstore(user_id, [doc], source='ongoing_instruction')
    print(f"[TOOL] Add instruction for user {user_id}: {instruction}")
    return True

def get_ongoing_instructions(args):
    """
    Args should be a dict or JSON string with at least 'user_id'.
    """
    if isinstance(args, str):
        args = json.loads(args)
    user_id = args.get('user_id')
    if not user_id:
        raise ValueError('user_id is required')
    result = query_user_documents(user_id, "ongoing instructions", top_k=20, type="ongoing_instruction")
    docs = result.get('documents', [])
    instructions = [doc[0] for doc in docs]
    print(f"[TOOL] Get instructions for user {user_id}: {instructions}")
    return instructions

def get_contacts(user_id):
    print(f"[TOOL] Get contacts for user {user_id}")
    results = vectorstore.similarity_search("contacts", k=10, filter={"type": "contact"})
    return [doc.metadata.get("name", doc.page_content) for doc in results]

def get_recent_emails(user_id):
    print(f"[TOOL] Get recent emails for user {user_id}")
    # Use query_user_documents for correct filtering
    result = query_user_documents(user_id, "recent emails", top_k=5, type="email")
    docs = result.get('documents', [])
    metadatas = result.get('metadatas', [])
    # Return subject if available, else page_content
    emails = []
    for doc, meta in zip(docs, metadatas):
        meta_dict = meta[0] if meta else {}
        subject = meta_dict.get('subject')
        emails.append(subject if subject else doc[0])
    return emails

def get_upcoming_events(user_id):
    print(f"[TOOL] Get upcoming events for user {user_id}")
    result = query_user_documents(user_id, "upcoming events", top_k=5, type="calendar_event")
    docs = result.get('documents', [])
    metadatas = result.get('metadatas', [])
    events = []
    for doc, meta in zip(docs, metadatas):
        meta_dict = meta[0] if meta else {}
        title = meta_dict.get('title')
        events.append(title if title else doc[0])
    return events

# def import_gmail_for_user(user_id):
#     # This should be called after OAuth is complete
#     emails = fetch_and_store_all_emails(user_id)
#     # TODO: Actually store emails in vectorstore here
#     print(f"Imported {len(emails)} emails for user {user_id}")
#     return emails

def schedule_calendar_event(user_id, summary, start, end, attendees=None, description=None, location=None, timezone='UTC', creds_data=None):
    """
    Schedule a Google Calendar event using provided credentials (creds_data).
    creds_data should be a dict with token, refresh_token, token_uri, client_id, client_secret, scopes.
    """
    if creds_data is None:
        raise ValueError("Google credentials must be provided as creds_data.")
    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=creds_data['scopes'],
    )
    event = create_google_calendar_event(
        creds, summary, start, end, attendees, description, location, timezone
    )
    return event

def ask_human(prompt: str) -> str:
    """
    Tool for the agent to request clarification or more input from the user.
    Returns the prompt to the user and expects a reply before continuing.
    """
    return f"[HUMAN INPUT NEEDED] {prompt}"

# Register this as a tool for the agent
TOOLS = [
    {
        'name': 'add_ongoing_instruction',
        'description': 'Add an ongoing instruction for the user. Args: user_id, instruction',
        'function': add_ongoing_instruction,
    },
    {
        'name': 'get_ongoing_instructions',
        'description': 'Get all ongoing instructions for the user. Args: user_id',
        'function': get_ongoing_instructions,
    },
    {
        'name': 'get_contacts',
        'description': 'Get all contacts for the user.',
        'function': get_contacts,
    },
    {
        'name': 'get_recent_emails',
        'description': 'Get the most recent emails for the user.',
        'function': get_recent_emails,
    },
    {
        'name': 'get_upcoming_events',
        'description': 'Get upcoming calendar events for the user.',
        'function': get_upcoming_events,
    },
    # {
    #     'name': 'import_gmail_for_user',
    #     'description': 'Import all emails from the user\'s Gmail account.',
    #     'function': import_gmail_for_user,
    # },
    {
        'name': 'schedule_calendar_event',
        'description': 'Schedule a Google Calendar event. Args: summary, start (ISO8601), end (ISO8601), attendees (list of emails), description, location, timezone',
        'function': schedule_calendar_event,
    },
    {
        'name': 'ask_human',
        'func': ask_human,
        'description': 'Ask the user for clarification or more information when the agent is unsure how to proceed.'
    },
]

def send_email(user_id, to, subject, body, cc=None, bcc=None, attachments=None, creds_data=None):
    if creds_data is None:
        raise ValueError("Google credentials must be provided as creds_data.")
    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=creds_data['scopes'],
    )
    return send_gmail_message(creds, to, subject, body, cc, bcc, attachments)

TOOLS.append({
    'name': 'send_email',
    'description': 'Send an email via Gmail. Args: to, subject, body, cc, bcc, attachments',
    'function': send_email,
}) 