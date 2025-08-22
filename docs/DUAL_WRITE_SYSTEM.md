# Dual-Write System: MongoDB to Postgres

## Overview

The dual-write system ensures that all data written to MongoDB is also persisted in a PostgreSQL database with a well-defined schema. This system is designed to enable future migration from MongoDB to Postgres with minimal operational risk and code changes.

## Architecture

### Components

1. **Postgres Models** (`todo/models/postgres/`)
   - Mirror MongoDB collections with normalized schema
   - Include sync metadata for tracking sync status
   - Use `mongo_id` field to maintain reference to MongoDB documents

2. **Dual-Write Service** (`todo/services/dual_write_service.py`)
   - Core service for writing to both databases
   - Handles data transformation between MongoDB and Postgres
   - Records sync failures for alerting

3. **Enhanced Dual-Write Service** (`todo/services/enhanced_dual_write_service.py`)
   - Extends base service with batch operations
   - Provides enhanced monitoring and metrics
   - Supports batch operation processing

4. **Abstract Repository Pattern** (`todo/repositories/abstract_repository.py`)
   - Defines interface for data access operations
   - Enables seamless switching between databases in the future
   - Provides consistent API across different storage backends

5. **Postgres Repositories** (`todo/repositories/postgres_repository.py`)
   - Concrete implementations of abstract repositories
   - Handle Postgres-specific operations
   - Maintain compatibility with existing MongoDB repositories

## Configuration

### Environment Variables

```bash
# Dual-Write Configuration
DUAL_WRITE_ENABLED=True                    # Enable/disable dual-write
DUAL_WRITE_RETRY_ATTEMPTS=3               # Number of retry attempts
DUAL_WRITE_RETRY_DELAY=5                  # Delay between retries (seconds)

# Postgres Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_NAME=todo_postgres
POSTGRES_USER=todo_user
POSTGRES_PASSWORD=todo_password
```

### Django Settings

The system automatically configures Django to use Postgres as the primary database while maintaining MongoDB connectivity through the existing `DatabaseManager`.

## Usage

### Basic Usage

```python
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService

# Initialize the service
dual_write_service = EnhancedDualWriteService()

# Create a document (writes to both MongoDB and Postgres)
success = dual_write_service.create_document(
    collection_name='users',
    data=user_data,
    mongo_id=str(user_id)
)

# Update a document
success = dual_write_service.update_document(
    collection_name='users',
    mongo_id=str(user_id),
    data=updated_data
)

# Delete a document
success = dual_write_service.delete_document(
    collection_name='users',
    mongo_id=str(user_id)
)
```

### Batch Operations

```python
# Perform multiple operations in batch
operations = [
    {
        'collection_name': 'users',
        'data': user_data,
        'mongo_id': str(user_id),
        'operation': 'create'
    },
    {
        'collection_name': 'tasks',
        'data': task_data,
        'mongo_id': str(task_id),
        'operation': 'update'
    }
]

success = dual_write_service.batch_operations(operations)
```

## Data Mapping

### MongoDB to Postgres Schema

| MongoDB Collection | Postgres Table | Key Fields |
|-------------------|----------------|------------|
| `users` | `postgres_users` | `google_id`, `email_id`, `name` |
| `tasks` | `postgres_tasks` | `title`, `status`, `priority`, `created_by` |
| `teams` | `postgres_teams` | `name`, `invite_code`, `created_by` |
| `labels` | `postgres_labels` | `name`, `color` |
| `roles` | `postgres_roles` | `name`, `permissions` |
| `task_assignments` | `postgres_task_assignments` | `task_mongo_id`, `user_mongo_id` |
| `watchlists` | `postgres_watchlists` | `name`, `user_mongo_id` |
| `user_team_details` | `postgres_user_team_details` | `user_id`, `team_id` |
| `user_roles` | `postgres_user_roles` | `user_mongo_id`, `role_mongo_id` |
| `audit_logs` | `postgres_audit_logs` | `action`, `collection_name`, `document_id` |

### Field Transformations

- **ObjectId Fields**: Converted to strings (24 characters)
- **Nested Objects**: Flattened or stored in separate tables
- **Arrays**: Stored in junction tables (e.g., `PostgresTaskLabel`)
- **Timestamps**: Preserved as-is
- **Enums**: Mapped to Postgres choices

## Sync Status Tracking

Each Postgres record includes sync metadata:

```python
class SyncMetadata:
    sync_status: str  # 'SYNCED', 'PENDING', 'FAILED'
    sync_error: str   # Error message if sync failed
    last_sync_at: datetime  # Last successful sync timestamp
```

## Error Handling and Alerting

### Sync Failures

The system automatically records sync failures:

```python
# Get sync failures
failures = dual_write_service.get_sync_failures()

# Get sync metrics
metrics = dual_write_service.get_sync_metrics()
```

### Alerting

- **Immediate Logging**: All failures are logged with ERROR level
- **Critical Alerts**: Logged with CRITICAL level for immediate attention
- **Failure Tracking**: Maintains list of recent failures for monitoring

### Retry Mechanism

- **Automatic Retries**: Failed operations are automatically retried
- **Configurable Attempts**: Set via `DUAL_WRITE_RETRY_ATTEMPTS`
- **Exponential Backoff**: Delay increases between retry attempts
- **Manual Retry**: Failed operations can be manually retried

## Monitoring and Health Checks

### Metrics

```python
# Get comprehensive sync metrics
metrics = dual_write_service.get_sync_metrics()

# Check sync status of specific document
status = dual_write_service.get_sync_status('users', str(user_id))
```

## Future Migration Path

### Phase 1: Dual-Write (Current)
- All writes go to both MongoDB and Postgres
- Reads continue from MongoDB
- Postgres schema is validated and optimized

### Phase 2: Read Migration
- Gradually shift read operations to Postgres
- Use feature flags to control read source
- Monitor performance and data consistency

### Phase 3: Full Migration
- All operations use Postgres
- MongoDB becomes read-only backup
- Eventually decommission MongoDB

### Code Changes Required

The abstract repository pattern minimizes code changes:

```python
# Current: MongoDB repository
from todo.repositories.user_repository import UserRepository
user_repo = UserRepository()

# Future: Postgres repository (minimal code change)
from todo.repositories.postgres_repository import PostgresUserRepository
user_repo = PostgresUserRepository()

# Same interface, different implementation
user = user_repo.get_by_email("user@example.com")
```

## Performance Considerations

### Synchronous Operations
- **Pros**: Immediate consistency, simple error handling
- **Cons**: Higher latency, potential for MongoDB write failures

### Batch Operations
- **Pros**: Reduced database round trips, better throughput
- **Cons**: Potential for partial failures

## Security

### Data Privacy
- All sensitive data is encrypted in transit
- Postgres connections use SSL
- Access controls are maintained across both databases

### Audit Trail
- All operations are logged in audit logs
- Sync failures are tracked for compliance
- Data integrity is maintained through transactions

## Testing

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Verify data transformation logic

### Integration Tests
- Test end-to-end sync operations
- Verify data consistency between databases
- Test failure scenarios and recovery

### Performance Tests
- Measure sync latency under load
- Test batch operation efficiency

## Troubleshooting

### Common Issues

1. **Postgres Connection Failures**
   - Check database credentials and network connectivity
   - Verify Postgres service is running
   - Check firewall settings

2. **Sync Failures**
   - Review sync error logs
   - Check data transformation logic
   - Verify Postgres schema matches expectations

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

# Get recent failures
failures = dual_write_service.get_sync_failures()
for failure in failures:
    print(f"Collection: {failure['collection']}, ID: {failure['mongo_id']}")
```

## Deployment

### Prerequisites
- PostgreSQL 15+ with appropriate extensions
- MongoDB 7+ (existing)
- Python 3.9+ with required packages

### Setup Steps
1. Create Postgres database and user
2. Run Django migrations
3. Configure environment variables
4. Verify sync operations

### Production Considerations
- Use connection pooling for Postgres
- Set up monitoring and alerting
- Implement backup and recovery procedures

## Support and Maintenance

### Regular Maintenance
- Monitor sync metrics and failures
- Review and optimize Postgres performance
- Update sync logic as schema evolves
- Clean up old sync failure records

### Updates and Upgrades
- Test sync operations after schema changes
- Verify data consistency after updates
- Monitor performance impact of changes
- Update documentation as needed
