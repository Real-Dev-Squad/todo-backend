from django.core.management.base import BaseCommand
from todo.services.postgres_sync_service import PostgresSyncService


class Command(BaseCommand):
    help = "Synchronize labels and roles PostgreSQL tables with MongoDB data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force sync even if tables already have data",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting PostgreSQL table synchronization for labels and roles..."))

        try:
            postgres_sync_service = PostgresSyncService()

            if options["force"]:
                self.stdout.write("Force sync enabled - will sync all tables regardless of existing data")

            success = postgres_sync_service.sync_all_tables()

            if success:
                self.stdout.write(self.style.SUCCESS("PostgreSQL table synchronization completed successfully!"))
            else:
                self.stdout.write(self.style.ERROR("Some PostgreSQL table synchronizations failed!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"PostgreSQL table synchronization failed: {str(e)}"))
