# TODO Backend

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
6. Create a `.env` file in the root directory with your environment variables. See `ENVIRONMENT_VARIABLES.md` for a complete list of available variables and their descriptions.
7. Install [docker](https://docs.docker.com/get-docker/) and [docker compose](https://docs.docker.com/compose/install/)
8. Start MongoDB using docker
    ```
    docker-compose up -d db
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
    docker-compose up -d
    ```
3. Go to http://127.0.0.1:8000/v1/health API to make sure the server it up. You should see this response
    ```
    {
    "status": "UP"
    }
    ```
4. On making changes to code and saving, live reload will work in this case as well

## Environment Configuration

The application uses environment variables for all configuration. All environment-specific settings have been consolidated into a single approach using environment variables.

### Quick Setup

1. Create a `.env` file in the project root using the migration script:
   ```bash
   python migrate_settings.py development  # or staging, production
   ```
   Or manually create a `.env` file and add your environment variables (see `ENVIRONMENT_VARIABLES.md` for complete documentation)
2. The application will automatically load these variables

### Example .env file for development:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ENV=DEVELOPMENT

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
DB_NAME=todo_db

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS Settings
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOW_CREDENTIALS=True
```

For production deployments, refer to the environment-specific configurations in `ENVIRONMENT_VARIABLES.md`.

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