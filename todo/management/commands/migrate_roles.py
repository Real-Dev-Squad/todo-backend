from django.core.management.base import BaseCommand
from todo_project.db.migrations import run_all_migrations


class Command(BaseCommand):
    help = "Run database migrations including predefined roles"

    def handle(self, *args, **options):
        self.stdout.write("Starting database migrations...")

        success = run_all_migrations()

        if success:
            self.stdout.write("All database migrations completed successfully!")
        else:
            self.stdout.write("Some database migrations failed!") 