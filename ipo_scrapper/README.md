# IPO Scraper Client

A standalone Python client for executing IPO scraping tasks via the Sales-Manager API. This tool automates the process of scraping IPO data from Korean financial websites and managing the results through the Sales-Manager task system.

## Features

- 🔐 **JWT Authentication** - Secure API authentication with token management
- 📊 **Task Management** - Create and monitor IPO scraping tasks
- ⏳ **Progress Monitoring** - Real-time task status tracking
- 🎯 **Configurable Targets** - Support for multiple IPO data sources
- 📝 **Comprehensive Logging** - Detailed execution logs and results
- ⚙️ **Flexible Configuration** - Command-line and JSON configuration options

## Prerequisites

- Python 3.8 or higher
- Access to a running Sales-Manager API server
- Valid user credentials for the Sales-Manager system

## Installation

1. **Clone or download this directory**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Option 1: Command Line Arguments

```bash
python ipo_scraper_client.py \
  --username your@email.com \
  --password yourpassword \
  --target-sites 38.co.kr ipostock.co.kr \
  --company-limit 20
```

### Option 2: JSON Configuration File

1. **Copy the example configuration:**
   ```bash
   cp config.example.json config.json
   ```

2. **Edit `config.json` with your credentials:**
   ```json
   {
     "username": "your_email@domain.com",
     "password": "your_password",
     "description": "IPO scraping and analysis",
     "agent_id": 1,
     "target_sites": ["38.co.kr", "ipostock.co.kr"],
     "company_limit": 20,
     "check_interval": 10,
     "user_email": "your_email@domain.com"
   }
   ```

3. **Run with configuration file:**
   ```bash
   python ipo_scraper_client.py --config config.json
   ```

## Usage Examples

### Basic Usage
```bash
python ipo_scraper_client.py --username user@example.com --password mypassword
```

### Advanced Usage with Custom Parameters
```bash
python ipo_scraper_client.py \
  --username user@example.com \
  --password mypassword \
  --base-url http://your-server:8000/api/v1 \
  --target-sites 38.co.kr ipostock.co.kr \
  --company-limit 50 \
  --check-interval 5
```

### Using Configuration File
```bash
python ipo_scraper_client.py --config config.json
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--username` | Username/email for authentication | Required |
| `--password` | Password for authentication | Required |
| `--config` | Path to JSON configuration file | None |
| `--base-url` | Base URL for the API | `http://localhost:8000/api/v1` |
| `--target-sites` | Target sites to scrape | `38.co.kr ipostock.co.kr` |
| `--company-limit` | Maximum companies to process | `10` |
| `--check-interval` | Task monitoring interval (seconds) | `10` |

## Configuration Parameters

### Required Parameters
- `username` - Your Sales-Manager account email
- `password` - Your Sales-Manager account password

### Optional Parameters
- `description` - Task description (default: "IPO scraping and analysis")
- `agent_id` - Agent ID to use (default: 1)
- `target_sites` - List of sites to scrape (default: ["38.co.kr", "ipostock.co.kr"])
- `company_limit` - Maximum number of companies to process (default: 10)
- `check_interval` - How often to check task status in seconds (default: 10)
- `user_email` - Email for notifications (defaults to username)

## Workflow Process

The IPO scraper executes the following workflow:

1. **Authentication** 🔐
   - Authenticate with Sales-Manager API
   - Obtain JWT access token

2. **Task Creation** 📝
   - Create IPO scraping task
   - Configure workflow parameters

3. **Workflow Execution** ⚙️
   - `scrape_lists` - Scrape IPO listing pages
   - `scrape_details` - Extract detailed information
   - `process_data` - Normalize and compare data
   - `save_data` - Store to database
   - `create_alerts` - Set up notifications
   - `generate_summary` - Create final report

4. **Monitoring** 📊
   - Track task progress
   - Display status updates
   - Show final results

## Expected Output

### Successful Execution
```
🔐 Authenticating...
✅ Authentication successful for user@example.com
📝 Creating IPO scraper task...
✅ Task created with ID: 123
⏳ Monitoring task progress...
📊 Task Status: running - 14:05:30
📊 Task Status: running - 14:05:40
📊 Task Status: completed - 14:05:50

🎉 Task completed with status: completed

📊 Task Results:
{
  "status": "success",
  "result_data": "IPO scraping completed: 15 collected, 12 saved, 5 alerts created (success rate: 80%)",
  "summary": {
    "total_scraped": 15,
    "total_saved": 12,
    "total_alerts_created": 5,
    "success_rate": 80.0
  }
}
```

## Target Sites

The scraper supports the following Korean IPO information sites:

- **38.co.kr** - Comprehensive IPO data and analysis
- **ipostock.co.kr** - IPO stock information and schedules

## Error Handling

The client includes comprehensive error handling for:

- **Authentication failures** - Invalid credentials or expired tokens
- **Network issues** - Connection timeouts and API unavailability
- **Task failures** - Workflow execution errors
- **Configuration errors** - Invalid parameters or missing files

## Security Notes

- **Never commit credentials** to version control
- **Use environment variables** for sensitive data in production
- **Rotate passwords regularly** for security
- **Use HTTPS** in production environments

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   ❌ Authentication failed: 401 - Incorrect username or password
   ```
   - Verify your username and password
   - Check if your account is active

2. **Connection Refused**
   ```
   ❌ Error: ConnectionError
   ```
   - Ensure the Sales-Manager API server is running
   - Check the `--base-url` parameter

3. **Task Creation Failed**
   ```
   ❌ Task creation failed: 403 - Not enough permissions
   ```
   - Verify your account has task creation permissions
   - Check if the agent_id exists

### Debug Mode

For detailed debugging, you can modify the script to enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Integration

This client integrates with the Sales-Manager API endpoints:

- `POST /api/v1/auth/token` - Authentication
- `POST /api/v1/tasks` - Task creation
- `GET /api/v1/tasks/{id}` - Task status monitoring

## Workflow Integration

The IPO scraper workflow (`ipo_demand_forecast_schedule_workflow`) is integrated into the Sales-Manager system. The actual workflow implementation is located in the main Sales-Manager project at:

```
/app/ai_agent/agents/ipo_scraper/
├── builder.py          # Workflow builder
├── nodes.py           # Workflow nodes
├── state.py           # State management
└── tools/             # Scraping tools
```

## License

This project is part of the Sales-Manager system by InterOpera.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the Sales-Manager API documentation
3. Contact the development team

---

**Note**: This client requires an active Sales-Manager API server and proper database connectivity to function correctly.