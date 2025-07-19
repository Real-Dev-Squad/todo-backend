#!/usr/bin/env python3
"""
Simple test script to verify executor update functionality
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/amitprakash/todo-backend-2')

# Set required environment variables
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('SECRET_KEY', 'debug-secret-key')
os.environ.setdefault('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
os.environ.setdefault('GOOGLE_OAUTH_CLIENT_ID', 'debug-client-id')
os.environ.setdefault('GOOGLE_OAUTH_CLIENT_SECRET', 'debug-client-secret')
os.environ.setdefault('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:8000/v1/auth/google/callback')
os.environ.setdefault('PRIVATE_KEY', 'debug-private-key')
os.environ.setdefault('PUBLIC_KEY', 'debug-public-key')
os.environ.setdefault('ACCESS_LIFETIME', '3600')
os.environ.setdefault('REFRESH_LIFETIME', '604800')
os.environ.setdefault('ACCESS_TOKEN_COOKIE_NAME', 'todo-access')
os.environ.setdefault('REFRESH_TOKEN_COOKIE_NAME', 'todo-refresh')
os.environ.setdefault('COOKIE_DOMAIN', 'localhost')
os.environ.setdefault('COOKIE_SECURE', 'False')
os.environ.setdefault('COOKIE_HTTPONLY', 'True')
os.environ.setdefault('COOKIE_SAMESITE', 'Lax')
os.environ.setdefault('TODO_UI_BASE_URL', 'http://localhost:3000')
os.environ.setdefault('TODO_UI_REDIRECT_PATH', 'dashboard')
os.environ.setdefault('TODO_BACKEND_BASE_URL', 'http://localhost:8000')
os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017/todo_db')
os.environ.setdefault('DB_NAME', 'todo_db')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings.development')
django.setup()

from bson import ObjectId
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.models.task_assignment import TaskAssignmentModel
from todo.models.common.pyobjectid import PyObjectId

def test_executor_update():
    """Test the executor update functionality"""
    print("=== Testing Executor Update Functionality ===")
    
    # Create a test task assignment with executor_id field
    task_id = str(ObjectId())
    assignee_id = str(ObjectId())
    user_id = str(ObjectId())
    
    print(f"Creating test assignment with task_id: {task_id}")
    
    # Create assignment with explicit executor_id=None
    assignment = TaskAssignmentModel(
        task_id=PyObjectId(task_id),
        assignee_id=PyObjectId(assignee_id),
        user_type="team",
        created_by=PyObjectId(user_id),
        updated_by=None,
        executor_id=None,  # Explicitly set to None
    )
    
    # Save to database
    created_assignment = TaskAssignmentRepository.create(assignment)
    print(f"✅ Assignment created with ID: {created_assignment.id}")
    print(f"   - task_id: {created_assignment.task_id}")
    print(f"   - assignee_id: {created_assignment.assignee_id}")
    print(f"   - user_type: {created_assignment.user_type}")
    print(f"   - executor_id: {created_assignment.executor_id}")
    
    # Test updating executor
    new_executor_id = str(ObjectId())
    print(f"\nTesting executor update to: {new_executor_id}")
    
    success = TaskAssignmentRepository.update_executor(task_id, new_executor_id, user_id)
    
    if success:
        print("✅ Executor update successful!")
        
        # Verify the update
        updated_assignment = TaskAssignmentRepository.get_by_task_id(task_id)
        if updated_assignment and updated_assignment.executor_id:
            print(f"✅ Verified: executor_id is now {updated_assignment.executor_id}")
        else:
            print("❌ Verification failed: executor_id not found in updated assignment")
    else:
        print("❌ Executor update failed!")
    
    # Clean up
    print(f"\nCleaning up test data...")
    TaskAssignmentRepository.delete_assignment(task_id, user_id)
    print("✅ Test completed")

if __name__ == "__main__":
    test_executor_update() 