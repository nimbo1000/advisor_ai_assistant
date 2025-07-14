from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Email(models.Model):
    sender = models.CharField(max_length=255)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=512)
    body = models.TextField()
    sent_at = models.DateTimeField()

class CalendarEvent(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)

class HubspotContact(models.Model):
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True)

class ContactNote(models.Model):
    contact = models.ForeignKey(HubspotContact, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class HubspotIntegration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_in = models.IntegerField()
    token_created = models.DateTimeField(auto_now_add=True)
    hubspot_user_id = models.CharField(max_length=64, blank=True, null=True)  # For mapping webhooks


class OngoingInstruction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instruction = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default='active')


class GmailPollingState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gmail_polling_state')
    last_history_id = models.CharField(max_length=128, blank=True, null=True)
    last_polled = models.DateTimeField(auto_now=True)
    # Google OAuth credentials for background polling
    token = models.CharField(max_length=512, blank=True, null=True)
    refresh_token = models.CharField(max_length=512, blank=True, null=True)
    token_uri = models.CharField(max_length=512, blank=True, null=True)
    client_id = models.CharField(max_length=512, blank=True, null=True)
    client_secret = models.CharField(max_length=512, blank=True, null=True)
    scopes = models.TextField(blank=True, null=True)  # Store as comma-separated string

    def get_google_credentials(self):
        if not all([self.token, self.refresh_token, self.token_uri, self.client_id, self.client_secret, self.scopes]):
            return None
        scopes_str = str(self.scopes) if self.scopes else ''
        return {
            'token': self.token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': [s.strip() for s in scopes_str.split(',') if s.strip()],
        }

