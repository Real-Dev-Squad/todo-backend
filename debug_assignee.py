#!/usr/bin/env python3
"""
Debug script to help identify why assignee details might be showing as null.
Run this script to check the data structure and identify issues.
"""

import os
import sys
import django
from bson import ObjectId

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo_project.settings.development')
django.setup()

from todo.repositories.watchlist_repository import WatchlistRepository
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.repositories.user_repository import UserRepository
from todo.repositories.team_repository import TeamRepository
from todo.repositories.task_repository import TaskRepository


def debug_assignee_issue():
    """Debug function to identify assignee issues"""
    
    print("=== Debugging Assignee Issue ===\n")
    
    # 1. Check if there are any watchlist entries
    print("1. Checking watchlist entries...")
    watchlist_collection = WatchlistRepository.get_collection()
    watchlist_count = watchlist_collection.count_documents({})
    print(f"   Total watchlist entries: {watchlist_count}")
    
    if watchlist_count > 0:
        sample_watchlist = watchlist_collection.find_one()
        print(f"   Sample watchlist entry: {sample_watchlist}")
    
    # 2. Check if there are any task assignments
    print("\n2. Checking task assignments...")
    task_details_collection = TaskAssignmentRepository.get_collection()
    assignment_count = task_details_collection.count_documents({})
    print(f"   Total task assignments: {assignment_count}")
    
    if assignment_count > 0:
        sample_assignment = task_details_collection.find_one()
        print(f"   Sample task assignment: {sample_assignment}")
    
    # 3. Check if there are any tasks
    print("\n3. Checking tasks...")
    task_collection = TaskRepository.get_collection()
    task_count = task_collection.count_documents({})
    print(f"   Total tasks: {task_count}")
    
    if task_count > 0:
        sample_task = task_collection.find_one()
        print(f"   Sample task: {sample_task}")
    
    # 4. Check if there are any users
    print("\n4. Checking users...")
    user_collection = UserRepository._get_collection()
    user_count = user_collection.count_documents({})
    print(f"   Total users: {user_count}")
    
    if user_count > 0:
        sample_user = user_collection.find_one()
        print(f"   Sample user: {sample_user}")
    
    # 5. Check if there are any teams
    print("\n5. Checking teams...")
    team_collection = TeamRepository.get_collection()
    team_count = team_collection.count_documents({})
    print(f"   Total teams: {team_count}")
    
    if team_count > 0:
        sample_team = team_collection.find_one()
        print(f"   Sample team: {sample_team}")
    
    # 6. Test the aggregation pipeline
    print("\n6. Testing aggregation pipeline...")
    if watchlist_count > 0:
        try:
            # Get a sample user_id from watchlist
            sample_watchlist = watchlist_collection.find_one()
            if sample_watchlist:
                user_id = sample_watchlist.get('userId')
                print(f"   Testing with user_id: {user_id}")
                
                # Run the aggregation pipeline
                count, tasks = WatchlistRepository.get_watchlisted_tasks(1, 10, user_id)
                print(f"   Found {count} tasks for user {user_id}")
                
                if tasks:
                    print(f"   First task: {tasks[0].model_dump() if hasattr(tasks[0], 'model_dump') else tasks[0]}")
                else:
                    print("   No tasks found")
                    
        except Exception as e:
            print(f"   Error in aggregation: {e}")
    
    # 7. Test the fallback method
    print("\n7. Testing fallback method...")
    if task_count > 0:
        try:
            sample_task = task_collection.find_one()
            if sample_task:
                task_id = str(sample_task['_id'])
                print(f"   Testing fallback with task_id: {task_id}")
                
                assignee = WatchlistRepository._get_assignee_for_task(task_id)
                print(f"   Fallback assignee result: {assignee}")
                
        except Exception as e:
            print(f"   Error in fallback method: {e}")
    
    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    debug_assignee_issue() 