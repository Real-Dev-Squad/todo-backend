import debugpy
import socket
from django.core.management.commands.runserver import Command as RunServerCommand


class Command(RunServerCommand):
    help = "Run the Django development server with debugpy for VS Code debugging"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--debug-port", type=int, default=5678, help="Port for the debug server (default: 5678)")
        parser.add_argument(
            "--wait-for-client", action="store_true", help="Wait for debugger client to attach before starting server"
        )

    def is_port_in_use(self, port):
        """Check if a port is already in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return False
            except OSError:
                return True

    def handle(self, *args, **options):
        debug_port = options.get("debug_port", 5678)
        wait_for_client = options.get("wait_for_client", False)

        # Check if debugpy is already initialized or connected
        if debugpy.is_client_connected():
            self.stdout.write(self.style.WARNING(f"Debugger already connected on port {debug_port}"))
        else:
            # Check if debug port is in use
            if self.is_port_in_use(debug_port):
                self.stdout.write(self.style.ERROR(f"Port {debug_port} is already in use. Debug server not started."))
                self.stdout.write(self.style.WARNING("Django server will start without debug capability."))
            else:
                try:
                    # Only configure debugpy if not already configured
                    if not hasattr(debugpy, "_is_configured") or not debugpy._is_configured:
                        # Listen for debugger connections
                        debugpy.listen(("0.0.0.0", debug_port))
                        self.stdout.write(self.style.SUCCESS(f"Debug server listening on port {debug_port}"))

                        if wait_for_client:
                            self.stdout.write(self.style.WARNING("Waiting for debugger client to attach..."))
                            debugpy.wait_for_client()
                            self.stdout.write(self.style.SUCCESS("Debugger client attached!"))
                        else:
                            self.stdout.write(self.style.SUCCESS("Server starting - you can now attach the debugger"))
                    else:
                        self.stdout.write(self.style.WARNING("Debug server already configured"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to start debug server: {str(e)}"))
                    self.stdout.write(self.style.WARNING("Django server will start without debug capability."))

        # Call the parent runserver command
        super().handle(*args, **options)
