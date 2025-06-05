#!/usr/bin/env python3
"""
IPO Scraper API Client
======================

A standalone client to execute IPO scraping tasks via the Sales-Manager API.
This script handles authentication and task creation for the IPO scraper workflow.

Usage:
    python ipo_scraper_client.py --username your@email.com --password yourpassword
    python ipo_scraper_client.py --config config.json
"""

import argparse
import json
import time
import sys
from typing import Dict
import requests
from datetime import datetime


class IPOScraperClient:
    """Client for executing IPO scraper tasks via API"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate and get access token"""
        print("🔐 Authenticating...")
        
        response = self.session.post(
            f"{self.base_url}/auth/token",
            data={
                "username": username,
                "password": password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
            print(f"✅ Authentication successful for {token_data['email']}")
            return token_data
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    def create_ipo_task(self, config: Dict) -> Dict:
        """Create IPO scraper task"""
        print("📝 Creating IPO scraper task...")
        
        # Try different agent IDs if the configured one fails
        agent_ids_to_try = [
            config.get("agent_id", 1),
            2, 3, 4, 5  # Try common agent IDs
        ]
        
        task_data_template = {
            "description": config.get("description", "IPO scraping and analysis"),
            "input_data": {
                "workflow": "ipo_demand_forecast_schedule_workflow",
                "task_input": {
                    "user_email": config.get("user_email"),
                    "target_sites": config.get("target_sites", ["38.co.kr", "ipostock.co.kr"]),
                    "company_limit": config.get("company_limit", 10)
                }
            },
            "status": "pending"
        }
        
        for agent_id in agent_ids_to_try:
            task_data = task_data_template.copy()
            task_data["agent_id"] = agent_id
            
            print(f"  Trying agent_id: {agent_id}")
            
            response = self.session.post(
                f"{self.base_url}/tasks",
                json=task_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                task = response.json()
                print(f"✅ Task created with ID: {task['id']} using agent_id: {agent_id}")
                return task
            elif response.status_code == 500 and "agent_id" in response.text:
                print(f"  ❌ Agent {agent_id} not found, trying next...")
                continue
            else:
                # Different error, don't continue trying
                break
        
        # If we get here, all agent IDs failed
        raise Exception(f"Task creation failed for all agent IDs. Last response: {response.status_code} - {response.text}")
    
    def get_task_status(self, task_id: int) -> Dict:
        """Get task status"""
        response = self.session.get(f"{self.base_url}/tasks/{task_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get task status: {response.status_code} - {response.text}")
    
    def get_task_result(self, task_id: int) -> Dict:
        """Get detailed task result"""
        response = self.session.get(f"{self.base_url}/tasks/{task_id}/result")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error fetching detailed task result: {response.status_code} {response.json()}")
            return None

    def monitor_task(self, task_id: int, check_interval: int = 10) -> Dict:
        """Monitor task progress until completion"""
        print("⏳ Monitoring task progress...")
        
        while True:
            try:
                task = self.get_task_status(task_id)
                status = task.get('status', 'unknown')
                
                print(f"📊 Task Status: {status} - {datetime.now().strftime('%H:%M:%S')}")
                
                if status in ['completed', 'failed', 'cancelled']:
                    # Try to get detailed results
                    print("🔍 Fetching detailed task results...")
                    result = self.get_task_result(task_id)
                    if result:
                        print(f"📋 Task Result: {result}")
                    return task
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n⚠️  Monitoring interrupted by user")
                return self.get_task_status(task_id)
            except Exception as e:
                print(f"❌ Error monitoring task: {e}")
                time.sleep(check_interval)
    
    def run_ipo_scraper(self, username: str, password: str, config: Dict) -> Dict:
        """Complete IPO scraper execution flow"""
        try:
            # Step 1: Authenticate
            auth_data = self.authenticate(username, password)
            config["user_email"] = config.get("user_email", auth_data["email"])
            
            # Step 2: Create task
            task = self.create_ipo_task(config)
            task_id = task["id"]
            
            # Step 3: Monitor progress
            final_task = self.monitor_task(task_id, config.get("check_interval", 10))
            
            # Step 4: Display results
            self.display_results(final_task)
            
            return final_task
            
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    
    def display_results(self, task: Dict):
        """Display task results"""
        status = task.get('status', 'unknown')
        print(f"\n🎉 Task completed with status: {status}")
        
        if status == 'completed':
            # Check for task results
            if 'result' in task and task['result']:
                print("\n📊 Task Results:")
                if isinstance(task['result'], dict):
                    print(json.dumps(task['result'], indent=2))
                else:
                    print(task['result'])
            
            # Check for result data in task result relationship
            if hasattr(task, 'task_result') and task['task_result']:
                result_data = task['task_result'].get('result_data')
                if result_data:
                    print("\n📈 Detailed Results:")
                    if isinstance(result_data, dict):
                        print(json.dumps(result_data, indent=2))
                    else:
                        print(result_data)
        
        elif status == 'failed':
            print("❌ Task failed. Check logs for details.")
            if 'error' in task:
                print(f"Error: {task['error']}")


def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="IPO Scraper API Client")
    parser.add_argument("--username", help="Username/email for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", 
                       help="Base URL for the API (default: http://localhost:8000/api/v1)")
    parser.add_argument("--target-sites", nargs="+", default=["38.co.kr", "ipostock.co.kr"],
                       help="Target sites to scrape")
    parser.add_argument("--company-limit", type=int, default=10,
                       help="Maximum number of companies to process")
    parser.add_argument("--check-interval", type=int, default=10,
                       help="Task monitoring check interval in seconds")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = load_config(args.config)
        username = config.get("username")
        password = config.get("password")
    else:
        config = {}
        username = args.username
        password = args.password
    
    # Validate required parameters
    if not username or not password:
        print("❌ Username and password are required")
        print("Use --username and --password, or provide --config with credentials")
        sys.exit(1)
    
    # Build configuration
    config.update({
        "target_sites": args.target_sites,
        "company_limit": args.company_limit,
        "check_interval": args.check_interval,
        "description": config.get("description", "IPO scraping and analysis"),
        "agent_id": config.get("agent_id", 1)
    })
    
    # Initialize client and run
    client = IPOScraperClient(args.base_url)
    client.run_ipo_scraper(username, password, config)


if __name__ == "__main__":
    main()