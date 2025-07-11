from django.core.management.base import BaseCommand
from todo_project.db.migrations import run_all_migrations


class Command(BaseCommand):
    help = "Run database migrations including fixed labels"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database migrations..."))

        success = run_all_migrations()

        if success:
            self.stdout.write(self.style.SUCCESS("All database migrations completed successfully!"))
        else:
            self.stdout.write(self.style.ERROR("Some database migrations failed!"))
