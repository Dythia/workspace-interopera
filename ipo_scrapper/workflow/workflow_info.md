# IPO Scraper Workflow Information

## Workflow Overview

The IPO scraper uses a LangGraph-based workflow with the following components:

### Workflow Nodes
1. **scrape_lists** - Scrape IPO listing pages from target sites
2. **scrape_details** - Extract detailed IPO information
3. **process_data** - Normalize and compare scraped data
4. **save_data** - Store IPO data to database
5. **create_alerts** - Set up notification schedules
6. **generate_summary** - Create final execution report

### Target Sites
- **38.co.kr** - Korean IPO information site
- **ipostock.co.kr** - Korean IPO stock information

### Workflow ID
- **Workflow Name**: `ipo_demand_forecast_schedule_workflow`
- **Agent ID**: 1 (default)

### Data Flow
```
scrape_lists → scrape_details → process_data → save_data → create_alerts → generate_summary
```

### Expected Output
```json
{
  "status": "success",
  "result_data": "IPO scraping completed: X collected, Y saved, Z alerts created (success rate: N%)",
  "summary": {
    "total_scraped": X,
    "total_saved": Y,
    "total_alerts_created": Z,
    "success_rate": N
  }
}
```

## Integration Notes

This workflow is integrated into the Sales-Manager system and requires:
- Active Sales-Manager API server
- Database connectivity
- Proper authentication tokens
- Agent configuration in the system

The workflow files are located in the main Sales-Manager project at:
`/app/ai_agent/agents/ipo_scraper/`