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
6. Create a `.env` file in the root directory, and copy the content from the `.env.example` file to it
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

## API Documentation

### Tasks

#### Add Label to Task
```
POST /v1/tasks/{task_id}/labels

Add a label to an existing task.

Request Body:
{
    "label_id": "string"  // ID of the label to add
}

Responses:
200 OK - Label added successfully
400 Bad Request - Invalid input (e.g., invalid label ID format)
404 Not Found - Task or label not found
500 Internal Server Error - Unexpected server error

Example:
POST /v1/tasks/123/labels
{
    "label_id": "456"
}
```