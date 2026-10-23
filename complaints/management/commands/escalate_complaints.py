from django.core.management.base import BaseCommand

from complaints.escalations import escalate_overdue_complaints


class Command(BaseCommand):
    help = "Escalate open complaints that have exceeded the configured response window."

    def handle(self, *args, **options):
        count = escalate_overdue_complaints()
        self.stdout.write(self.style.SUCCESS(f"Escalated {count} overdue complaint(s)."))
