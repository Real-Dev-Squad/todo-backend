#!/usr/bin/env python3
"""
Test script to create sample data and test the assignee functionality.
This will help verify that the assignee details are working correctly.
"""

import os
import sys
import django
from bson import ObjectId
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings.development')
django.setup()

from todo.models.user import UserModel
from todo.models.team import TeamModel
from todo.models.task import TaskModel
from todo.models.task_assignment import TaskAssignmentModel
from todo.models.watchlist import WatchlistModel
from todo.repositories.user_repository import UserRepository
from todo.repositories.team_repository import TeamRepository
from todo.repositories.task_repository import TaskRepository
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.repositories.watchlist_repository import WatchlistRepository


def create_sample_data():
    """Create sample data for testing assignee functionality"""
    
    print("=== Creating Sample Data ===\n")
    
    # 1. Create a sample user
    print("1. Creating sample user...")
    user_data = {
        "google_id": "test_google_id_123",
        "email": "testuser@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg"
    }
    user = UserRepository.create_or_update(user_data)
    print(f"   Created user: {user.name} ({user.email_id})")
    
    # 2. Create a sample team
    print("\n2. Creating sample team...")
    team = TeamModel(
        name="Test Team",
        description="A test team for assignee testing",
        invite_code="TEST123",
        created_by=user.id,
        updated_by=user.id
    )
    team = TeamRepository.create(team)
    print(f"   Created team: {team.name}")
    
    # 3. Create a sample task
    print("\n3. Creating sample task...")
    task = TaskModel(
        title="Test Task with Assignee",
        description="This is a test task to verify assignee functionality",
        priority="HIGH",
        status="TODO",
        created_by=user.id
    )
    task = TaskRepository.create(task)
    print(f"   Created task: {task.title}")
    
    # 4. Create a task assignment (assign task to user)
    print("\n4. Creating task assignment (user assignee)...")
    assignment = TaskAssignmentModel(
        task_id=task.id,
        assignee_id=user.id,
        user_type="user",
        created_by=user.id
    )
    assignment = TaskAssignmentRepository.create(assignment)
    print(f"   Assigned task to user: {user.name}")
    
    # 5. Create another task assigned to team
    print("\n5. Creating task assigned to team...")
    team_task = TaskModel(
        title="Team Task",
        description="This task is assigned to a team",
        priority="MEDIUM",
        status="IN_PROGRESS",
        created_by=user.id
    )
    team_task = TaskRepository.create(team_task)
    print(f"   Created team task: {team_task.title}")
    
    team_assignment = TaskAssignmentModel(
        task_id=team_task.id,
        assignee_id=team.id,
        user_type="team",
        created_by=user.id
    )
    team_assignment = TaskAssignmentRepository.create(team_assignment)
    print(f"   Assigned task to team: {team.name}")
    
    # 6. Create an unassigned task
    print("\n6. Creating unassigned task...")
    unassigned_task = TaskModel(
        title="Unassigned Task",
        description="This task has no assignee",
        priority="LOW",
        status="TODO",
        created_by=user.id
    )
    unassigned_task = TaskRepository.create(unassigned_task)
    print(f"   Created unassigned task: {unassigned_task.title}")
    
    # 7. Add tasks to watchlist
    print("\n7. Adding tasks to watchlist...")
    
    # Add user-assigned task to watchlist
    user_watchlist = WatchlistModel(
        taskId=str(task.id),
        userId=str(user.id),
        createdBy=str(user.id)
    )
    user_watchlist = WatchlistRepository.create(user_watchlist)
    print(f"   Added user task to watchlist")
    
    # Add team-assigned task to watchlist
    team_watchlist = WatchlistModel(
        taskId=str(team_task.id),
        userId=str(user.id),
        createdBy=str(user.id)
    )
    team_watchlist = WatchlistRepository.create(team_watchlist)
    print(f"   Added team task to watchlist")
    
    # Add unassigned task to watchlist
    unassigned_watchlist = WatchlistModel(
        taskId=str(unassigned_task.id),
        userId=str(user.id),
        createdBy=str(user.id)
    )
    unassigned_watchlist = WatchlistRepository.create(unassigned_watchlist)
    print(f"   Added unassigned task to watchlist")
    
    return user.id, task.id, team_task.id, unassigned_task.id


def test_assignee_functionality(user_id, task_id, team_task_id, unassigned_task_id):
    """Test the assignee functionality with the created data"""
    
    print("\n=== Testing Assignee Functionality ===\n")
    
    # Test the watchlist endpoint
    print("1. Testing watchlist with assignee details...")
    try:
        count, tasks = WatchlistRepository.get_watchlisted_tasks(1, 10, str(user_id))
        print(f"   Found {count} watchlisted tasks")
        
        for i, task in enumerate(tasks, 1):
            print(f"\n   Task {i}:")
            print(f"     Title: {task.title}")
            print(f"     Task ID: {task.taskId}")
            print(f"     Assignee: {task.assignee}")
            
            if task.assignee:
                print(f"     Assignee Type: {task.assignee.type}")
                print(f"     Assignee Name: {task.assignee.name}")
                print(f"     Assignee Email: {task.assignee.email}")
            else:
                print(f"     Assignee: None (unassigned task)")
                
    except Exception as e:
        print(f"   Error testing watchlist: {e}")
    
    # Test the fallback method
    print("\n2. Testing fallback method...")
    try:
        user_assignee = WatchlistRepository._get_assignee_for_task(str(task_id))
        print(f"   User task assignee: {user_assignee}")
        
        team_assignee = WatchlistRepository._get_assignee_for_task(str(team_task_id))
        print(f"   Team task assignee: {team_assignee}")
        
        unassigned_assignee = WatchlistRepository._get_assignee_for_task(str(unassigned_task_id))
        print(f"   Unassigned task assignee: {unassigned_assignee}")
        
    except Exception as e:
        print(f"   Error testing fallback: {e}")


def cleanup_sample_data():
    """Clean up the sample data"""
    print("\n=== Cleaning Up Sample Data ===\n")
    
    try:
        # Clean up watchlist
        watchlist_collection = WatchlistRepository.get_collection()
        watchlist_collection.delete_many({"userId": {"$regex": "test"}})
        print("   Cleaned up watchlist entries")
        
        # Clean up task assignments
        task_details_collection = TaskAssignmentRepository.get_collection()
        task_details_collection.delete_many({"created_by": {"$regex": "test"}})
        print("   Cleaned up task assignments")
        
        # Clean up tasks
        task_collection = TaskRepository.get_collection()
        task_collection.delete_many({"title": {"$regex": "Test"}})
        print("   Cleaned up tasks")
        
        # Clean up teams
        team_collection = TeamRepository.get_collection()
        team_collection.delete_many({"name": "Test Team"})
        print("   Cleaned up teams")
        
        # Clean up users
        user_collection = UserRepository._get_collection()
        user_collection.delete_many({"email_id": "testuser@example.com"})
        print("   Cleaned up users")
        
    except Exception as e:
        print(f"   Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        # Create sample data
        user_id, task_id, team_task_id, unassigned_task_id = create_sample_data()
        
        # Test the functionality
        test_assignee_functionality(user_id, task_id, team_task_id, unassigned_task_id)
        
        # Ask if user wants to clean up
        response = input("\nDo you want to clean up the sample data? (y/n): ")
        if response.lower() == 'y':
            cleanup_sample_data()
            print("   Cleanup completed!")
        else:
            print("   Sample data left in database for further testing")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 