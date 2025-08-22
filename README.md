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
6. Create a `.env` file for environment variables:
    - Copy the example environment file:
        ```
        cp .env.example .env
        ```
    - Edit the `.env` file and update the values according to your setup:
        - `SECRET_KEY`: Generate a unique secret key for Django
        - `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
        - `DB_NAME`: Your database name
        - `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`: OAuth credentials for Google authentication
        - `PRIVATE_KEY` and `PUBLIC_KEY`: Generate RSA key pairs for JWT token signing
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


# Dual-Write System: MongoDB to PostgreSQL

## 🎯 Overview

This feature implements a comprehensive dual-write system that ensures all data written to MongoDB is automatically synchronized to PostgreSQL. The system is designed to enable future migration from MongoDB to PostgreSQL with minimal operational risk and code changes.

## ✨ Key Features

- **Dual-Write Operations**: Every MongoDB write is automatically mirrored to PostgreSQL
- **Synchronous Operations**: Immediate consistency with both databases
- **Comprehensive Error Handling**: Automatic retry mechanisms and failure tracking
- **Future-Ready Architecture**: Abstract repository pattern for seamless database switching
- **Real-time Monitoring**: Health checks and sync metrics
- **Production Ready**: Includes Docker setup, migrations, and comprehensive documentation

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application  │───▶│  Dual-Write      │───▶│   PostgreSQL    │
│   (MongoDB)    │    │  Service         │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 15+
- MongoDB 7+ (existing)

### 2. Setup Development Environment

```bash
# Start required services
docker-compose -f docker-compose.dev.yml up -d

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp env.example .env
# Edit .env with your configuration

# Run Django migrations
python manage.py migrate
```

### 3. Basic Usage

```python
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService

# Initialize the service
dual_write_service = EnhancedDualWriteService()

# Create a document (automatically syncs to both databases)
success = dual_write_service.create_document(
    collection_name='users',
    data={'name': 'John Doe', 'email': 'john@example.com'},
    mongo_id='507f1f77bcf86cd799439011'
)
```

## 📊 Data Mapping

The system automatically maps MongoDB collections to PostgreSQL tables:

| MongoDB Collection | PostgreSQL Table | Description |
|-------------------|------------------|-------------|
| `users` | `postgres_users` | User accounts and profiles |
| `tasks` | `postgres_tasks` | Task management |
| `teams` | `postgres_teams` | Team organization |
| `labels` | `postgres_labels` | Task labels and categories |
| `roles` | `postgres_roles` | User roles and permissions |
| `task_assignments` | `postgres_task_assignments` | Task assignments |
| `watchlists` | `postgres_watchlists` | User watchlists |
| `audit_logs` | `postgres_audit_logs` | System audit trail |

## ⚙️ Configuration

### Environment Variables

```bash
# Enable/disable dual-write
DUAL_WRITE_ENABLED=True

# Retry configuration
DUAL_WRITE_RETRY_ATTEMPTS=3
DUAL_WRITE_RETRY_DELAY=5

# Database connections
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_NAME=todo_postgres
POSTGRES_USER=todo_user
POSTGRES_PASSWORD=todo_password
```

### Django Settings

The system automatically configures Django to use PostgreSQL while maintaining MongoDB connectivity.

## 📈 Monitoring and Health Checks

### Sync Metrics

```python
# Get comprehensive sync metrics
metrics = dual_write_service.get_sync_metrics()
print(f"Total failures: {metrics['total_failures']}")
```

### Health Monitoring

```python
# Check sync status of specific document
status = dual_write_service.get_sync_status('users', str(user_id))
print(f"Sync status: {status}")
```

## 🧪 Testing

### Unit Tests

```bash
# Run unit tests
python manage.py test todo.tests.unit

# Run specific test file
python manage.py test todo.tests.unit.services.test_dual_write_service
```

### Integration Tests

```bash
# Run integration tests
python manage.py test todo.tests.integration
```

### Manual Testing

```python
# Test sync operations
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService

service = EnhancedDualWriteService()

# Test create
success = service.create_document('users', user_data, str(user_id))
assert success == True

# Test update
success = service.update_document('users', str(user_id), updated_data)
assert success == True

# Test delete
success = service.delete_document('users', str(user_id))
assert success == True
```

## 🚨 Error Handling

### Automatic Retries

Failed sync operations are automatically retried with configurable attempts and delays.

### Failure Tracking

```python
# Get recent sync failures
failures = dual_write_service.get_sync_failures()
for failure in failures:
    print(f"Collection: {failure['collection']}")
    print(f"Document ID: {failure['mongo_id']}")
    print(f"Error: {failure['error']}")
```

### Manual Retry

```python
# Retry a specific failed sync
success = dual_write_service.retry_failed_sync('users', str(user_id))
```

## 🔮 Future Migration Path

### Phase 1: Dual-Write (Current)
- ✅ All writes go to both databases
- ✅ Reads continue from MongoDB
- ✅ Postgres schema validated

### Phase 2: Read Migration
- 🔄 Gradually shift reads to PostgreSQL
- 🔄 Use feature flags for control
- 🔄 Monitor performance

### Phase 3: Full Migration
- 🎯 All operations use PostgreSQL
- 🎯 MongoDB becomes backup
- 🎯 Eventually decommission MongoDB

### Code Changes Required

The abstract repository pattern minimizes code changes:

```python
# Current: MongoDB
from todo.repositories.user_repository import UserRepository
user_repo = UserRepository()

# Future: PostgreSQL (minimal change)
from todo.repositories.postgres_repository import PostgresUserRepository
user_repo = PostgresUserRepository()

# Same interface!
user = user_repo.get_by_email("user@example.com")
```

## 🐳 Docker Development

### Start Services

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check service status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs postgres
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it todo_postgres_dev psql -U todo_user -d todo_postgres

# Connect to MongoDB
docker exec -it todo_mongodb_dev mongosh -u admin -p password
```

## 📚 Documentation

- **README**: [README_DUAL_WRITE.md](README_DUAL_WRITE.md)
- **System Docs**: [docs/DUAL_WRITE_SYSTEM.md](docs/DUAL_WRITE_SYSTEM.md)
- **Environment Config**: [env.example](env.example)
- **Docker Setup**: [docker-compose.dev.yml](docker-compose.dev.yml)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   - Check if PostgreSQL is running
   - Verify credentials in `.env`
   - Check network connectivity

2. **Sync Failures**
   - Review sync error logs
   - Check data transformation logic
   - Verify PostgreSQL schema

3. **Performance Issues**
   - Monitor sync latency
   - Optimize batch operation sizes
   - Monitor database performance

### Debug Commands

```python
# Enable debug logging
import logging
logging.getLogger('todo.services.dual_write_service').setLevel(logging.DEBUG)

# Check sync status
status = dual_write_service.get_sync_status('users', str(user_id))
print(f"Sync status: {status}")
```

