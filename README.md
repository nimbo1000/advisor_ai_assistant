# Financial Advisor AI Agent

A Django-based AI assistant for financial advisors that integrates with Gmail, Google Calendar, and Hubspot CRM. The app provides a ChatGPT-like interface to answer questions, automate tasks, and proactively assist with client management using data from your email, calendar, and CRM.

## Features

- **Google OAuth Login**: Secure login with Google, requesting email and calendar permissions. Data automatically retrieved on authentication. Webhook set up for calendar event but not fully tested. Polling set up for emails with a django-crontab also not tested. Fetching can be triggered manually at these paths /gmail, /calendar.
- **Hubspot CRM Integration**: Connect and sync contacts and notes from Hubspot via OAuth. Syncing done automatically
- **Chat Interface**: Modern web chat UI for interacting with the AI agent.
- **Retrieval-Augmented Generation (RAG)**: Uses pgvector to index and search emails, contacts, notes, and events for context-aware answers.
- **Automated Task Handling**: Agent can schedule meetings, send emails, and create contacts/notes? using tool-calling. Hubspot object creation might not be working from chat interface due to async to sync issues. HTML form endpoints available for testing. 
- **Ongoing Instructions**: Users can set persistent instructions (e.g., "Add new email senders to Hubspot"), which the agent remembers and acts on when relevant events occur.
- **Proactive Agent**: Listens to webhooks/events from Gmail, Calendar, and Hubspot to trigger actions or suggestions automatically.
