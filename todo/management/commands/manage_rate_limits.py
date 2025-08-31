from django.core.management.base import BaseCommand, CommandError
from todo.services.rate_limiter_service import rate_limiter_service
import json


class Command(BaseCommand):
    help = 'Manage rate limiting rules dynamically'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['show', 'update', 'create', 'delete'],
            help='Action to perform on rate limiting rules'
        )
        parser.add_argument(
            '--rule-name',
            default='default',
            help='Name of the rate limiting rule (default: default)'
        )
        parser.add_argument(
            '--window-size',
            type=int,
            help='Window size in minutes'
        )
        parser.add_argument(
            '--num-windows',
            type=int,
            help='Number of windows'
        )
        parser.add_argument(
            '--requests-per-second',
            type=int,
            help='Maximum requests per second'
        )
        parser.add_argument(
            '--sliding-scale-factor',
            type=float,
            help='Sliding scale factor (0.0 to 1.0)'
        )
        parser.add_argument(
            '--active',
            type=bool,
            help='Whether the rule is active (true/false)'
        )
        parser.add_argument(
            '--output-format',
            choices=['json', 'table'],
            default='table',
            help='Output format for show command'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        rule_name = options['rule_name']
        
        if action == 'show':
            self.show_rule(rule_name, options['output_format'])
        elif action == 'update':
            self.update_rule(rule_name, options)
        elif action == 'create':
            self.create_rule(rule_name, options)
        elif action == 'delete':
            self.delete_rule(rule_name)
    
    def show_rule(self, rule_name, output_format):
        """Show rate limiting rule information"""
        try:
            rule = rate_limiter_service._get_rule(rule_name)
            
            if output_format == 'json':
                self.stdout.write(json.dumps(rule, default=str, indent=2))
            else:
                self.stdout.write(f"\nRate Limiting Rule: {rule_name}")
                self.stdout.write("=" * 50)
                self.stdout.write(f"Window Size: {rule['window_size_minutes']} minutes")
                self.stdout.write(f"Number of Windows: {rule['num_windows']}")
                self.stdout.write(f"Requests per Second: {rule['requests_per_second']}")
                self.stdout.write(f"Sliding Scale Factor: {rule['sliding_scale_factor']}")
                self.stdout.write(f"Active: {rule['is_active']}")
                self.stdout.write(f"Created: {rule['created_at']}")
                self.stdout.write(f"Updated: {rule['updated_at']}")
                
                # Calculating effective limits
                total_window_size = rule['window_size_minutes'] * rule['num_windows']
                max_requests_per_window = rule['requests_per_second'] * rule['window_size_minutes'] * 60
                effective_max_requests = int(max_requests_per_window * rule['sliding_scale_factor'])
                
                self.stdout.write("\nEffective Limits:")
                self.stdout.write("-" * 20)
                self.stdout.write(f"Total Time Span: {total_window_size} minutes")
                self.stdout.write(f"Max Requests per Window: {max_requests_per_window}")
                self.stdout.write(f"Effective Max Requests: {effective_max_requests}")
                
        except Exception as e:
            raise CommandError(f"Failed to show rule {rule_name}: {e}")
    
    def update_rule(self, rule_name, options):
        """Update an existing rate limiting rule"""
        try:
            update_data = {}
            
            if options['window_size'] is not None:
                update_data['window_size_minutes'] = options['window_size']
            if options['num_windows'] is not None:
                update_data['num_windows'] = options['num_windows']
            if options['requests_per_second'] is not None:
                update_data['requests_per_second'] = options['requests_per_second']
            if options['sliding_scale_factor'] is not None:
                update_data['sliding_scale_factor'] = options['sliding_scale_factor']
            if options['active'] is not None:
                update_data['is_active'] = options['active']
            
            if not update_data:
                raise CommandError("No update parameters provided")
            
            success = rate_limiter_service.update_rule(rule_name, **update_data)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully updated rule '{rule_name}'")
                )
                # Show updated rule
                self.show_rule(rule_name, 'table')
            else:
                raise CommandError(f"Failed to update rule '{rule_name}'")
                
        except Exception as e:
            raise CommandError(f"Failed to update rule {rule_name}: {e}")
    
    def create_rule(self, rule_name, options):
        """Create a new rate limiting rule"""
        try:
            # Checking if rule already exists
            existing_rule = rate_limiter_service._get_rule(rule_name)
            if existing_rule and rule_name != 'default':
                raise CommandError(f"Rule '{rule_name}' already exists")
            
            # Setting  default values if not provided
            create_data = {
                'window_size_minutes': options['window_size'] or 5,
                'num_windows': options['num_windows'] or 3,
                'requests_per_second': options['requests_per_second'] or 120,
                'sliding_scale_factor': options['sliding_scale_factor'] or 0.8,
                'is_active': options['active'] if options['active'] is not None else True
            }
            
            success = rate_limiter_service.update_rule(rule_name, **create_data)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully created rule '{rule_name}'")
                )
                # Show created rule
                self.show_rule(rule_name, 'table')
            else:
                raise CommandError(f"Failed to create rule '{rule_name}'")
                
        except Exception as e:
            raise CommandError(f"Failed to create rule {rule_name}: {e}")
    
    def delete_rule(self, rule_name):
        """Delete a rate limiting rule (deactivate it)"""
        try:
            if rule_name == 'default':
                raise CommandError("Cannot delete the default rule")
            
            success = rate_limiter_service.update_rule(rule_name, is_active=False)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully deactivated rule '{rule_name}'")
                )
            else:
                raise CommandError(f"Failed to deactivate rule '{rule_name}'")
                
        except Exception as e:
            raise CommandError(f"Failed to delete rule {rule_name}: {e}")
