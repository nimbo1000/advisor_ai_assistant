from django.core.management.base import BaseCommand
from advisor_agent.utils import poll_gmail_for_all_users

class Command(BaseCommand):
    help = 'Poll Gmail for all users and update the vectorstore with new emails.'

    def handle(self, *args, **options):
        poll_gmail_for_all_users()
        self.stdout.write(self.style.SUCCESS('Successfully polled Gmail for all users.')) 