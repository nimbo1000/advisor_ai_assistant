import time
import base64
import datetime
from django.utils import timezone
import jwt
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .utils import create_google_calendar_event
import requests
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import HubspotIntegration
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model, login
from .forms import ContactForm, NoteForm
import html2text
from .vectorstore import add_documents_to_vectorstore
from google.auth.exceptions import RefreshError
from .models import GmailPollingState
from .utils import fetch_gmail_messages
# Create your views here.

def chat_view(request):
    is_logged_in = 'google_credentials' in request.session
    user_name = None
    user_email = None
    if is_logged_in:
        creds = request.session.get('google_credentials', {})
        user_name = creds.get('user_name')
        user_email = creds.get('user_email')
    return render(request, 'advisor_agent/chat.html', {
        'is_logged_in': is_logged_in,
        'user_name': user_name,
        'user_email': user_email,
    })




def google_auth_init(request):
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "scopes": settings.GOOGLE_OAUTH2_SCOPES
            }
        },
        scopes=settings.GOOGLE_OAUTH2_SCOPES
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    request.session['oauth_state'] = state
    return redirect(authorization_url)

def google_auth_callback(request):
    state = request.session.get('oauth_state')
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "scopes": settings.GOOGLE_OAUTH2_SCOPES
            }
        },
        scopes=settings.GOOGLE_OAUTH2_SCOPES,
        state=state
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    # Decode id_token for user info
    id_token = flow.credentials.id_token if hasattr(flow.credentials, 'id_token') else None
    user_name = None
    user_email = None
    id_token_decoded = None
    if id_token:
        id_token_decoded = jwt.decode(id_token, options={"verify_signature": False})
        print(id_token_decoded)
        user_email = id_token_decoded.get('email')
        user_name = id_token_decoded.get('name') or id_token_decoded.get('given_name')
    # Create or get Django user and log them in
    if user_email:
        User = get_user_model()
        user, created = User.objects.get_or_create(email=user_email, defaults={
            'username': user_email,
            'first_name': user_name or '',
        })
        login(request, user)
        # Gmail polling on sign-in
        from .models import GmailPollingState
        from .utils import fetch_gmail_messages
        polling_state, _ = GmailPollingState.objects.get_or_create(user=user)
        creds_data = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            'scopes': flow.credentials.scopes,
        }
        # Persist credentials for background polling
        polling_state.token = flow.credentials.token
        polling_state.refresh_token = flow.credentials.refresh_token
        polling_state.token_uri = flow.credentials.token_uri
        polling_state.client_id = flow.credentials.client_id
        polling_state.client_secret = settings.GOOGLE_OAUTH2_CLIENT_SECRET
        polling_state.scopes = ','.join(flow.credentials.scopes) if flow.credentials.scopes else ''
        polling_state.save()
        since_history_id = polling_state.last_history_id
        _, last_history_id = fetch_gmail_messages(creds_data, user.id, since_history_id=since_history_id)
        polling_state.last_history_id = last_history_id
        polling_state.save()
    # Store credentials and user info in session
    request.session['google_credentials'] = {
        'token': flow.credentials.token,
        'refresh_token': flow.credentials.refresh_token,
        'token_uri': flow.credentials.token_uri,
        'client_id': flow.credentials.client_id,
        "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        'scopes': flow.credentials.scopes,
        'id_token': id_token,
        'id_token_decoded': id_token_decoded,
        'user_name': user_name,
        'user_email': user_email,
    }
    request.session['user_name'] = user_name
    request.session['user_email'] = user_email
    return redirect('chat')

def ensure_refreshable_credentials(credentials):
    required = ['refresh_token', 'token_uri', 'client_id', 'client_secret']
    missing = [k for k in required if not credentials.get(k)]
    if missing:
        raise Exception(f"Missing fields for token refresh: {missing}. Please re-authenticate.")

def read_gmail(request):
    credentials = request.session.get('google_credentials')
    user_id = request.user.id
    try:
        ensure_refreshable_credentials(credentials)
        polling_state, _ = GmailPollingState.objects.get_or_create(user=request.user)
        since_history_id = polling_state.last_history_id
        messages, last_history_id = fetch_gmail_messages(credentials, user_id, since_history_id=since_history_id)
        # Update polling state
        polling_state.last_history_id = last_history_id
        polling_state.save()
        return JsonResponse({'messages': messages})
    except (RefreshError, Exception) as e:
        print(f"Google token refresh failed or credentials missing: {e}")
        request.session.pop('google_credentials', None)
        return redirect('google-auth')

def create_calendar_event(request):
    credentials = request.session.get('google_credentials')
    creds = Credentials(
        token=credentials['token'],
        refresh_token=credentials['refresh_token'],
        token_uri=credentials['token_uri'],
        client_id=credentials['client_id'],
        scopes=credentials['scopes']
    )
    # For now, use hardcoded values as before
    summary = 'Meeting Jump'
    start = '2025-12-25T10:00:00'
    end = '2025-12-25T11:00:00'
    event = create_google_calendar_event(creds, summary, start, end)
    return JsonResponse(event)

def read_calendar(request):
    # Check for credentials in session
    creds_data = request.session.get('google_credentials')
    if not creds_data:
        return JsonResponse({'error': 'Not authenticated with Google'}, status=401)
    creds = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        # client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=creds_data['scopes'],
    )
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=20, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    event_list = []
    for event in events:
        event_list.append({
            'id': event.get('id'),
            'summary': event.get('summary'),
            'description': event.get('description'),
            'start': event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
            'end': event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
            'attendees': [a.get('email') for a in event.get('attendees', [])] if 'attendees' in event else [],
            'organizer': event.get('organizer', {}).get('email'),
            'location': event.get('location'),
        })
    return JsonResponse({'events': event_list})

def logout_view(request):
    request.session.flush()
    return redirect('chat')

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


HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

# @login_required
def hubspot_auth(request):
    params = {
        'client_id': settings.HUBSPOT_CLIENT_ID,
        'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
        'scope': 'crm.objects.contacts.read crm.schemas.contacts.read crm.objects.companies.read crm.objects.contacts.write crm.objects.owners.read oauth',
    }
    url = f"{HUBSPOT_AUTH_URL}?{'&'.join([f'{k}={v}' for k,v in params.items()])}"
    return redirect(url)

# @login_required
def hubspot_callback(request):
    code = request.GET.get('code')
    if not code:
        return render(request, 'error.html', {'error': 'Authorization failed'})
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': settings.HUBSPOT_CLIENT_ID,
        'client_secret': settings.HUBSPOT_CLIENT_SECRET,
        'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
        'code': code
    }
    
    response = requests.post(HUBSPOT_TOKEN_URL, data=data)
    if response.status_code != 200:
        return render(request, 'error.html', {'error': 'Token exchange failed'})
    
    token_data = response.json()
    HubspotIntegration.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_in': token_data['expires_in'],
        }
    )
    return redirect('hubspot_contacts')

def refresh_tokens(user):
    try:
        integration = HubspotIntegration.objects.get(user=user)
        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.HUBSPOT_CLIENT_ID,
            'client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'refresh_token': integration.refresh_token
        }
        
        response = requests.post(HUBSPOT_TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        integration.access_token = token_data['access_token']
        integration.refresh_token = token_data['refresh_token']
        integration.expires_in = token_data['expires_in']
        integration.token_created = timezone.now()
        integration.save()
        
        return token_data['access_token']
    except HubspotIntegration.DoesNotExist:
        return None
    except requests.exceptions.RequestException as e:
        print(f"Token refresh failed: {str(e)}")
        # logger.error(f"Token refresh failed: {str(e)}")
        return None

# @login_required
def hubspot_contacts(request):
    try:
        integration = HubspotIntegration.objects.get(user=request.user)
    except HubspotIntegration.DoesNotExist:
        return redirect('hubspot_auth')
    
    # Check token expiration
    token_age = datetime.now() - integration.token_created.replace(tzinfo=None)
    if token_age > timedelta(seconds=integration.expires_in - 300):
        access_token = refresh_tokens(request.user)
        if not access_token:
            return redirect('hubspot_auth')
    else:
        access_token = integration.access_token
    
    # Fetch contacts
    headers = {'Authorization': f'Bearer {access_token}'}
    contacts_response = requests.get(
        'https://api.hubapi.com/crm/v3/objects/contacts',
        headers=headers,
        params={'limit': 100}
    )
    
    if contacts_response.status_code == 401:
        access_token = refresh_tokens(request.user)
        headers['Authorization'] = f'Bearer {access_token}'
        contacts_response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers=headers,
            params={'limit': 100}
        )
    
    contacts = contacts_response.json().get('results', [])
    # Store contacts in vectorstore
    contact_docs = []
    user_id = request.user.id
    for contact in contacts:
        props = contact.get('properties', {})
        name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
        email = props.get('email', '')
        phone = props.get('phone', '')
        company = props.get('company', '')
        summary = f"{name} <{email}> | Phone: {phone} | Company: {company}"
        contact_docs.append({
            'text': summary,
            'external_id': contact['id'],
            'name': name,
            'email': email,
            'phone': phone,
            'company': company,
            'type': 'contact',
        })
    if user_id and contact_docs:
        add_documents_to_vectorstore(user_id, contact_docs, source='hubspot_contact')
    
    # Fetch contact notes with actual content
    contact_notes = {}
    all_note_ids = set()
    
    # First pass: Get all note IDs associated with contacts
    for contact in contacts:
        contact_id = contact["id"]
        notes_response = requests.get(
            f'https://api.hubapi.com/crm/v4/objects/contacts/{contact_id}/associations/notes',
            headers=headers,
            params={'limit': 100}
        )
        if notes_response.status_code == 200:
            associations = notes_response.json().get('results', [])
            print(associations)
            note_ids = [assoc['toObjectId'] for assoc in associations]
            contact_notes[contact_id] = note_ids
            all_note_ids.update(note_ids)
    
    # Batch fetch note content in bulk (more efficient)
    notes_content = {}
    if all_note_ids:
        # Convert to list and chunk into batches of 100
        note_ids_list = list(all_note_ids)
        for i in range(0, len(note_ids_list), 100):
            batch_ids = note_ids_list[i:i+100]
            
            # Batch read endpoint for notes
            batch_url = "https://api.hubapi.com/crm/v3/objects/notes/batch/read"
            payload = {
                "inputs": [{"id": note_id} for note_id in batch_ids],
                "properties": ["hs_note_body", "hs_timestamp", "hubspot_owner_id"]
            }
            batch_response = requests.post(batch_url, headers=headers, json=payload)
            
            if batch_response.status_code == 200:
                print(batch_response.json())
                for note in batch_response.json().get('results', []):
                    notes_content[note['id']] = {
                        'content': note['properties'].get('hs_note_body', ''),
                        'created_at': note['properties'].get('hs_timestamp', ''),
                        'owner_id': note['properties'].get('hubspot_owner_id', '')
                    }
    
    # {'status': 'COMPLETE', 'results': [{'id': '155251621624', 'properties': {'hs_createdate': '2025-07-12T18:17:00.301Z', 'hs_lastmodifieddate': '2025-07-12T18:17:00.301Z', 'hs_note_body': '<div style="" dir="auto" data-top-level="true"><p style="margin:0;">Sample note for sample contact. He want to sell Tesla stock because of Elon\'s political views.</p></div>', 'hs_object_id': '155251621624', 'hs_timestamp': '2025-07-12T18:17:00.301Z', 'hubspot_owner_id': '159516863'}, 'createdAt': '2025-07-12T18:17:00.301Z', 'updatedAt': '2025-07-12T18:17:00.301Z', 'archived': False}], 'startedAt': '2025-07-12T19:55:25.228Z', 'completedAt': '2025-07-12T19:55:25.235Z'}

    # Now create a mapping of contact to actual note content
    contact_notes_data = {}
    print(f"NOTES CONTENT: {notes_content}")
    for contact_id, note_ids in contact_notes.items():
        contact_notes_data[contact_id] = [notes_content.get(str(note_id), {}) for note_id in note_ids]
    print(f"NOTES DATA: {contact_notes_data}")
    docs = []
    user_id = request.user.id
    for contact_id, note_ids in contact_notes.items():
        for note_id in note_ids:
            note = notes_content.get(str(note_id), {})
            content = note.get('content', '')
            # Convert HTML to text if needed
            if '<' in content and '>' in content:
                text = html2text.html2text(content)
            else:
                text = content
            docs.append({
                'text': text,
                'external_id': note_id,
                'contact_id': contact_id,
                'created_at': note.get('created_at'),
                'owner_id': note.get('owner_id'),
                'type': 'contact_note',
            })
    if user_id and docs:
        add_documents_to_vectorstore(user_id, docs, source='hubspot_note')
    return render(request, 'contacts.html', {
        'contacts': contacts,
        'contact_notes': contact_notes_data
    })


# hubspot_integration/views.py
@login_required
def create_contact(request):
    try:
        integration = HubspotIntegration.objects.get(user=request.user)
        access_token = get_valid_token(integration)
    except HubspotIntegration.DoesNotExist:
        return redirect('hubspot_auth')
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Prepare contact data for HubSpot
            contact_data = {
                "properties": {
                    "firstname": form.cleaned_data['firstname'],
                    "lastname": form.cleaned_data['lastname'],
                    "email": form.cleaned_data['email'],
                    "phone": form.cleaned_data.get('phone', ''),
                    "company": form.cleaned_data.get('company', ''),
                    "website": form.cleaned_data.get('website', '')
                }
            }
            
            # Create contact in HubSpot
            response = requests.post(
                'https://api.hubapi.com/crm/v3/objects/contacts',
                headers=headers,
                json=contact_data
            )
            if response.status_code == 201:
                return redirect('hubspot_contacts')
            else:
                error_msg = f"Failed to create contact: {response.json().get('message', 'Unknown error')}"
                return render(request, 'create_contact.html', {'form': form, 'error': error_msg})
    else:
        form = ContactForm()
    
    return render(request, 'create_contact.html', {'form': form})

# hubspot_integration/views.py
@login_required
def create_note(request, contact_id):
    try:
        integration = HubspotIntegration.objects.get(user=request.user)
        access_token = get_valid_token(integration)
    except HubspotIntegration.DoesNotExist:
        return redirect('hubspot_auth')
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Get contact details for context
    contact_response = requests.get(
        f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}',
        headers=headers,
        params={'properties': 'firstname,lastname,email'}
    )
    
    if contact_response.status_code != 200:
        messages.error(request, 'Contact not found')
        return redirect('hubspot_contacts')
    
    contact = contact_response.json()
    
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            # Prepare note data for HubSpot
            # timestamp = str(int(time.time() * 1000))  # Current time in milliseconds

            note_data = {
                "properties": {
                    "hs_note_body": form.cleaned_data['content'],
                    "hs_timestamp": "2025-07-13T08:29:53.885Z",  # Required timestamp
                    # "hs_note_title": form.cleaned_data.get('hs_note_title', 'Note from Django App'),  # Optional but recommended
                    # "hs_note_status": form.cleaned_data.get('hs_note_status', 'PUBLISHED'),  # Default to published
                    # "hubspot_owner_id": "default"  # Often required
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [{
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 201  # Note to contact association type
                        }]
                    }
                ]
            }
            
            # Create note in HubSpot
            response = requests.post(
                'https://api.hubapi.com/crm/v3/objects/notes',
                headers=headers,
                json=note_data
            )
            
            if response.status_code == 201:
                messages.success(request, 'Note added successfully!')
                return redirect('hubspot_contacts')
            else:
                print(response.json())
                error_msg = f"Failed to add note: {response.json().get('message', 'Unknown error')}"
                messages.error(request, error_msg)
    else:
        form = NoteForm()
    
    contact_name = (
        f"{contact['properties'].get('firstname', '')} "
        f"{contact['properties'].get('lastname', '')}"
    ).strip() or contact['properties'].get('email', 'Contact')
    
    return render(request, 'create_note.html', {
        'form': form,
        'contact': contact,
        'contact_name': contact_name
    })


def get_valid_token(hubspot_integration):
        """Return a valid access token, refreshing if necessary"""
        token_age = timezone.now() - hubspot_integration.token_created
        if token_age.total_seconds() > hubspot_integration.expires_in - 300:  # Refresh 5 min before expiration
            return refresh_tokens(hubspot_integration.user)
        return hubspot_integration.access_token