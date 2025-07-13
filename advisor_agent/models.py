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


class OngoingInstruction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ongoing_instructions')
    instruction = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}: {self.instruction[:50]}..."

