#!/usr/bin/env python3
"""
Test what data is available in the task endpoint
"""

import requests
import json

def get_token():
    """Get authentication token"""
    response = requests.post(
        "http://localhost:8000/api/v1/auth/token",
        data={
            "username": "dythia.prayudhatama@interopera.co",
            "password": "!Pt@20251!."
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Authentication failed: {response.status_code} - {response.text}")
        return None

def get_task_details(token, task_id):
    """Get detailed task information"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"http://localhost:8000/api/v1/tasks/{task_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        task = response.json()
        print(f"Task {task_id} details:")
        print(json.dumps(task, indent=2))
        return task
    else:
        print(f"Failed to get task {task_id}: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    auth_data = get_token()
    if auth_data:
        print(f"✅ Authenticated as {auth_data['email']}")
        
        # Test with the most recent task ID
        task_id = 1304  # From the last run
        task = get_task_details(auth_data['access_token'], task_id)