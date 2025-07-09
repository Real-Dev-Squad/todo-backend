#!/usr/bin/env python
"""
Migration script to help transition from environment-specific settings files
to the new consolidated environment variable approach.

This script will help you create a .env file based on your current environment.
"""

import os
import sys
from pathlib import Path


def get_environment_from_args():
    """Get the environment from command line arguments."""
    if len(sys.argv) > 1:
        env = sys.argv[1].lower()
        if env in ['development', 'staging', 'production']:
            return env
    return 'development'


def create_env_template(environment):
    """Create a .env file template based on the specified environment."""
    
    # Base template for all environments
    env_content = f"""# Django Settings
SECRET_KEY=django-insecure-w$a*-^hjqf&snr6qd&jkcq%0*5twb!_)qe0&z(2y-17umjr5tn
DEBUG=True
ENV={environment.upper()}

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
DB_NAME=todo_db

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Configuration
RDS_PUBLIC_KEY=
RDS_SESSION_COOKIE_NAME=rds-session-{environment}
RDS_SESSION_V2_COOKIE_NAME=rds-session-v2-{environment}
COOKIE_DOMAIN=
COOKIE_SECURE=False
COOKIE_SAMESITE=Lax

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/v1/auth/google/callback

# Google JWT Configuration
GOOGLE_JWT_PRIVATE_KEY=
GOOGLE_JWT_PUBLIC_KEY=
GOOGLE_JWT_ACCESS_LIFETIME=3600
GOOGLE_JWT_REFRESH_LIFETIME=604800

# Google Cookie Settings
GOOGLE_ACCESS_COOKIE_NAME=ext-access
GOOGLE_REFRESH_COOKIE_NAME=ext-refresh

# Service URLs
FRONTEND_URL=http://localhost:3000
RDS_BACKEND_BASE_URL=http://localhost:8087

# CORS Settings
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOW_CREDENTIALS=True

# Security Settings
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_DOMAIN=
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SECURE=False

# Testing
TESTING=False
"""

    # Environment-specific overrides
    if environment == 'staging':
        env_content = env_content.replace(
            'ALLOWED_HOSTS=localhost,127.0.0.1',
            'ALLOWED_HOSTS=staging-api.realdevsquad.com,services.realdevsquad.com'
        )
        env_content = env_content.replace(
            'COOKIE_DOMAIN=',
            'COOKIE_DOMAIN=.realdevsquad.com'
        )
        env_content = env_content.replace(
            'COOKIE_SECURE=False',
            'COOKIE_SECURE=True'
        )
        env_content = env_content.replace(
            'COOKIE_SAMESITE=Lax',
            'COOKIE_SAMESITE=None'
        )
        env_content = env_content.replace(
            'CORS_ALLOW_ALL_ORIGINS=True',
            'CORS_ALLOW_ALL_ORIGINS=False'
        )
        env_content += '\n# Staging-specific CORS origins\nCORS_ALLOWED_ORIGINS=https://staging-todo.realdevsquad.com\n'
        env_content = env_content.replace(
            'SESSION_COOKIE_SECURE=False',
            'SESSION_COOKIE_SECURE=True'
        )
        env_content = env_content.replace(
            'FRONTEND_URL=http://localhost:3000',
            'FRONTEND_URL=https://staging-todo.realdevsquad.com'
        )
        env_content = env_content.replace(
            'RDS_BACKEND_BASE_URL=http://localhost:8087',
            'RDS_BACKEND_BASE_URL=https://staging-api.realdevsquad.com'
        )
        
    elif environment == 'production':
        env_content = env_content.replace(
            'DEBUG=True',
            'DEBUG=False'
        )
        env_content = env_content.replace(
            'ALLOWED_HOSTS=localhost,127.0.0.1',
            'ALLOWED_HOSTS=api.realdevsquad.com,services.realdevsquad.com'
        )
        env_content = env_content.replace(
            'COOKIE_DOMAIN=',
            'COOKIE_DOMAIN=.realdevsquad.com'
        )
        env_content = env_content.replace(
            'COOKIE_SECURE=False',
            'COOKIE_SECURE=True'
        )
        env_content = env_content.replace(
            'COOKIE_SAMESITE=Lax',
            'COOKIE_SAMESITE=None'
        )
        env_content = env_content.replace(
            'CORS_ALLOW_ALL_ORIGINS=True',
            'CORS_ALLOW_ALL_ORIGINS=False'
        )
        env_content += '\n# Production-specific CORS origins\nCORS_ALLOWED_ORIGINS=https://todo.realdevsquad.com\n'
        env_content = env_content.replace(
            'SECURE_SSL_REDIRECT=False',
            'SECURE_SSL_REDIRECT=True'
        )
        env_content = env_content.replace(
            'SESSION_COOKIE_SECURE=False',
            'SESSION_COOKIE_SECURE=True'
        )
        env_content = env_content.replace(
            'FRONTEND_URL=http://localhost:3000',
            'FRONTEND_URL=https://todo.realdevsquad.com'
        )
        env_content = env_content.replace(
            'RDS_BACKEND_BASE_URL=http://localhost:8087',
            'RDS_BACKEND_BASE_URL=https://api.realdevsquad.com'
        )

    return env_content


def main():
    """Main migration function."""
    print("🚀 Django Settings Migration Tool")
    print("=" * 40)
    
    environment = get_environment_from_args()
    print(f"Creating .env template for {environment} environment...")
    
    # Create the .env file
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️  Warning: .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
    
    env_content = create_env_template(environment)
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env file created successfully!")
        print(f"📝 Environment: {environment.upper()}")
        print("\n📋 Next steps:")
        print("1. Review and customize the .env file for your specific needs")
        print("2. Add your actual secret keys and API credentials")
        print("3. Update database connection strings if needed")
        print("4. Test your application with: python manage.py runserver")
        print("\n📖 For complete documentation, see: ENVIRONMENT_VARIABLES.md")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 