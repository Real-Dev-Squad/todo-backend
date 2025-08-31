# TODO Backend - Updated

## Local development setup
1. Install pyenv
    - For Mac/Linux - https://github.com/pyenv/pyenv?tab=readme-ov-file#installation
    - For Windows - https://github.com/pyenv-win/pyenv-win/blob/master/docs/installation.md#chocolatey
2. Install the configured python version (3.12.7) using pyenv by running the command
    - For Mac/Linux
        ```
        pyenv install
        ```
    - For Windows
        ```
        pyenv install 3.11.5
        ```
3. Create virtual environment by running the command
    - For Mac/Linux
        ```
        pyenv virtualenv 3.11.5 venv
        ```
    - For Windows
        ```
        python -m pip install virtualenv
        python -m virtualenv venv
        ```
4. Activate the virtual environment by running the command
    - For Mac/Linux
        ```
        pyenv activate venv
        ```
    - For Windows
        ```
        .\venv\Scripts\activate
        ```
5. Install the project dependencies by running the command
    ```
    python -m pip install -r requirements.txt
    ```
6. Create a `.env` file for environment variables:
    - Copy the example environment file:
        ```
        cp .env.example .env
        ```
    - Edit the `.env` file and update the values according to your setup:
        - `SECRET_KEY`: Generate a unique secret key for Django using one of these methods:
            ```bash
            # Method 1: Using Django's built-in utility (Recommended)
            python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
            
            # Method 2: Using Python's secrets module
            python -c "import secrets; print(secrets.token_urlsafe(50))"
            
            # Method 3: Using openssl (if available)
            openssl rand -base64 50
            ```
        - `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
        - `DB_NAME`: Your database name
        - `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`: OAuth credentials for Google authentication
        - `PRIVATE_KEY` and `PUBLIC_KEY`: Generate RSA key pairs for JWT token signing using one of these methods:
            ```bash
            # Method 1: Using openssl (Recommended)
            # Generate private key (2048-bit RSA)
            openssl genrsa -out private_key.pem 2048
            
            # Generate public key from private key
            openssl rsa -in private_key.pem -pubout -out public_key.pem
            
            # View the keys and copy them to your .env file
            cat private_key.pem
            cat public_key.pem
            
            # Method 2: Using ssh-keygen
            ssh-keygen -t rsa -b 2048 -m PEM -f jwt_key -N ''
            openssl rsa -in jwt_key -pubout -out jwt_key.pub
            ```
            **Note**: Copy the entire content including `-----BEGIN...-----` and `-----END...-----` headers
        - Other settings can be left as default for local development
7. Install [docker](https://docs.docker.com/get-docker/) and [docker compose](https://docs.docker.com/compose/install/)
8. Start MongoDB using docker
    ```
    docker compose up -d db
    ```
9. Start the development server by running the command
    ```
    python manage.py runserver
    ```
10. Go to http://127.0.0.1:8000/v1/health API to make sure the server it up. You should see this response
    ```
    {
        "status": "UP",
        "components": {
            "db": {
                "status": "UP"
            }
        }
    }
    ```

## To simply try out the app
1. Install [docker](https://docs.docker.com/get-docker/) and [docker compose](https://docs.docker.com/compose/install/)
2. Start Django application and MongoDB using docker
    ```
    docker compose up -d
    ```
3. Go to http://127.0.0.1:8000/v1/health API to make sure the server it up. You should see this response
    ```
    {
    "status": "UP"
    }
    ```
4. On making changes to code and saving, live reload will work in this case as well

## Database Migrations

When making changes to Django models, you need to create and apply migrations:

1. **Create migrations** (run this after modifying models):
    ```
    python manage.py makemigrations
    ```

2. **Apply migrations** (run this to update the database schema):
    ```
    python manage.py migrate
    ```

3. **In Docker environment:**
    ```
    docker compose exec django-app python manage.py makemigrations
    docker compose exec django-app python manage.py migrate
    ```

**Note:** The docker-compose.yml automatically runs `migrate` on startup, but you must manually run `makemigrations` after model changes.

## Command reference
1. To run the tests, run the following command
    ```
    python manage.py test
    ```
2. To check test coverage, run the following command
    ```
    coverage run --source='.' manage.py test
    coverage report
    ```
3. To run the formatter
    ```
    ruff format
    ```
4. To run lint check
    ```
    ruff check
    ```
5. To fix lint issues
    ```
    ruff check --fix
    ```

## Debug Mode with VS Code

### Prerequisites
- VS Code with Python extension installed
- Docker and docker-compose

### Debug Setup

1. **Start the application with debug mode:**
   ```
   python manage.py runserver_debug 0.0.0.0:8000
   ```

2. **Available debug options:**
   ```bash
   # Basic debug mode (default debug port 5678)
   python manage.py runserver_debug 0.0.0.0:8000
   
   # Custom debug port
   python manage.py runserver_debug 0.0.0.0:8000 --debug-port 5679
   
   # Wait for debugger before starting (useful for debugging startup code)
   python manage.py runserver_debug 0.0.0.0:8000 --wait-for-client
   ```

3. **Attach VS Code debugger:**
   - Press `F5` or go to `Run > Start Debugging`
   - Select `Python: Remote Attach (Django in Docker)` from the dropdown
   - Set breakpoints in your Python code
   - Make requests to trigger the breakpoints

### Debug Features
- **Debug server port**: 5678 (configurable)
- **Path mapping**: Local code mapped to container paths
- **Django mode**: Special Django debugging features enabled
- **Hot reload**: Code changes reflected immediately
- **Variable inspection**: Full debugging capabilities in VS Code

### Troubleshooting
- If port 5678 is in use, specify a different port with `--debug-port`
- Ensure VS Code Python extension is installed
- Check that breakpoints are set in the correct files
- Verify the debug server shows "Debug server listening on port 5678"
