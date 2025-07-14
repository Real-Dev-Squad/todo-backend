#!/usr/bin/env python3
"""
Migration script to replace MongoDB imports with PostgreSQL imports
"""

import os
import re
from pathlib import Path

# Define the mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Repository imports
    r'from todo\.repositories\.user_repository import UserRepository': 'from todo.repositories.postgres_user_repository import UserRepository',
    r'from todo\.repositories\.task_repository import TaskRepository': 'from todo.repositories.postgres_task_repository import TaskRepository',
    r'from todo\.repositories\.role_repository import RoleRepository': 'from todo.repositories.postgres_role_repository import RoleRepository',
    r'from todo\.repositories\.label_repository import LabelRepository': 'from todo.repositories.postgres_label_repository import LabelRepository',
    r'from todo\.repositories\.team_repository import TeamRepository': 'from todo.repositories.postgres_team_repository import TeamRepository',
    r'from todo\.repositories\.team_repository import UserTeamDetailsRepository': 'from todo.repositories.postgres_team_repository import UserTeamDetailsRepository',
    r'from todo\.repositories\.assignee_task_details_repository import AssigneeTaskDetailsRepository': 'from todo.repositories.postgres_assignee_task_details_repository import AssigneeTaskDetailsRepository',
    r'from todo\.repositories\.watchlist_repository import WatchlistRepository': 'from todo.repositories.postgres_watchlist_repository import WatchlistRepository',
    
    # Model imports
    r'from todo\.models\.user import UserModel': 'from todo.models import User',
    r'from todo\.models\.task import TaskModel': 'from todo.models import Task',
    r'from todo\.models\.role import RoleModel': 'from todo.models import Role',
    r'from todo\.models\.label import LabelModel': 'from todo.models import Label',
    r'from todo\.models\.team import TeamModel': 'from todo.models import Team',
    r'from todo\.models\.team import UserTeamDetailsModel': 'from todo.models import UserTeamDetails',
    r'from todo\.models\.assignee_task_details import AssigneeTaskDetailsModel': 'from todo.models import AssigneeTaskDetails',
    r'from todo\.models\.watchlist import WatchlistModel': 'from todo.models import Watchlist',
    
    # Type annotations and variable references
    r'\bUserModel\b': 'User',
    r'\bTaskModel\b': 'Task',
    r'\bRoleModel\b': 'Role',
    r'\bLabelModel\b': 'Label',
    r'\bTeamModel\b': 'Team',
    r'\bUserTeamDetailsModel\b': 'UserTeamDetails',
    r'\bAssigneeTaskDetailsModel\b': 'AssigneeTaskDetails',
    r'\bWatchlistModel\b': 'Watchlist',
}

def update_file(file_path):
    """Update a single file with the import mappings"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all mappings
        for old_pattern, new_replacement in IMPORT_MAPPINGS.items():
            content = re.sub(old_pattern, new_replacement, content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main migration function"""
    base_dir = Path(__file__).parent
    
    # Files and directories to update
    target_patterns = [
        'todo/services/*.py',
        'todo/views/*.py',
        'todo/dto/*.py',
        'todo/serializers/*.py',
    ]
    
    updated_files = []
    
    for pattern in target_patterns:
        for file_path in base_dir.glob(pattern):
            if file_path.is_file() and file_path.suffix == '.py':
                if update_file(file_path):
                    updated_files.append(str(file_path))
    
    print(f"\n✅ Migration completed!")
    print(f"📝 Updated {len(updated_files)} files")
    
    if updated_files:
        print("\nUpdated files:")
        for file_path in updated_files:
            print(f"  - {file_path}")

if __name__ == "__main__":
    main()
