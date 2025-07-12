# Tool stubs for agent actions

from .vectorstore_pg import vectorstore
from .utils import create_google_calendar_event
from django.conf import settings
from google.oauth2.credentials import Credentials
from .utils import send_gmail_message

def add_ongoing_instruction(user_id, instruction):
    # TODO: Save instruction to DB or local store
    print(f"[TOOL] Add instruction for user {user_id}: {instruction}")
    return True

def get_ongoing_instructions(user_id):
    # TODO: Retrieve instructions from DB or local store
    print(f"[TOOL] Get instructions for user {user_id}")
    return ["When someone emails me that is not in Hubspot, create a contact."]

def get_contacts(user_id):
    print(f"[TOOL] Get contacts for user {user_id}")
    results = vectorstore.similarity_search("contacts", k=10, filter={"type": "contact"})
    return [doc.metadata.get("name", doc.page_content) for doc in results]

def get_recent_emails(user_id):
    print(f"[TOOL] Get recent emails for user {user_id}")
    results = vectorstore.similarity_search("recent emails", k=5, filter={"type": "email"})
    return [doc.metadata.get("subject", doc.page_content) for doc in results]

def get_upcoming_events(user_id):
    print(f"[TOOL] Get upcoming events for user {user_id}")
    results = vectorstore.similarity_search("upcoming events", k=5, filter={"type": "calendar_event"})
    return [doc.metadata.get("title", doc.page_content) for doc in results]

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
        'description': 'Add an ongoing instruction for the user.',
        'function': add_ongoing_instruction,
    },
    {
        'name': 'get_ongoing_instructions',
        'description': 'Get all ongoing instructions for the user.',
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