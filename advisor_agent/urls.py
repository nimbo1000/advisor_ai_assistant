from django.urls import path
from .views import *

urlpatterns = [
    path('', chat_view, name='chat'),
    path('logout/', logout_view, name='logout'),
    path('calendar/', read_calendar, name='read_calendar'),
    path('auth/google/', google_auth_init, name='google-auth'),
    path('auth/callback/', google_auth_callback, name='google-callback'),
    path('gmail/', read_gmail, name='read-gmail'),
    path('calendar/create/', create_calendar_event, name='create-event'),
    # Hubspot
    path('hubspot/auth/', hubspot_auth, name='hubspot_auth'),
    path('hubspot/callback/', hubspot_callback, name='hubspot_callback'),
    path('hubspot/contacts/', hubspot_contacts, name='hubspot_contacts'),
    path('hubspot/contacts/create/', create_contact, name='create_contact'),
    path('hubspot/contacts/<int:contact_id>/notes/create/', create_note, name='create_note'),
    path('webhooks/google-calendar/', google_calendar_webhook, name='google_calendar_webhook'),
    path('webhooks/hubspot/', hubspot_webhook, name='hubspot_webhook'),
] 