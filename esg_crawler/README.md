# ESG Report Crawler

A standalone ESG report crawler that analyzes company websites to detect ESG/sustainability reports and updates the production database.

## Features

- **Website Analysis**: Crawls company websites to detect ESG/sustainability content
- **Database Integration**: Queries `smm_company` table and updates ESG information
- **Batch Processing**: Process multiple companies efficiently
- **Single Company Mode**: Process individual companies by ID
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Respectful Crawling**: Built-in delays and timeout handling

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

## Usage

### Batch Processing (Default)
Process companies from the database in batches:
```bash
python esg_crawler.py --batch-size 10 --delay 2.0
```

### Single Company Processing
Process a specific company by ID and website:
```bash
python esg_crawler.py --company-id 123 --website https://example.com
```

### Command Line Options

- `--batch-size`: Number of companies to process in batch (default: 10)
- `--delay`: Delay between requests in seconds (default: 1.0)
- `--timeout`: Request timeout in seconds (default: 15)
- `--company-id`: Process single company by ID
- `--website`: Website URL for single company processing
- `--user-agent`: User agent string (default: ESGReportBot/1.0)

### Examples

```bash
# Process 20 companies with 3-second delay
python esg_crawler.py --batch-size 20 --delay 3.0

# Process single company
python esg_crawler.py --company-id 456 --website https://company.com

# Custom timeout and user agent
python esg_crawler.py --timeout 30 --user-agent "MyBot/2.0"
```

## Database Schema

The crawler updates the `smm_company` table with ESG information:

```sql
-- ESG info is stored in the esg_info JSONB column
{
  "has_esg_reports": true/false,
  "analysis_timestamp": "2025-01-01T12:00:00",
  "website_analysis": {
    "is_accessible": true,
    "sustainability_section_found": true,
    "sustainability_links_found": 3,
    "total_links_found": 25,
    "response_time": 1.2
  },
  "crawler_version": "1.0"
}
```

## ESG Detection Logic

The crawler detects ESG reports by analyzing:

1. **URL Patterns**: `/sustainability`, `/esg`, `/csr`, `/corporate-responsibility`, etc.
2. **Content Keywords**: "sustainability report", "esg report", "csr report", etc.
3. **Navigation Elements**: ESG-related menu items and links
4. **Page Titles**: ESG keywords in page titles and meta descriptions

## Logging

Logs are written to both console and `esg_crawler.log` file with:
- Processing progress
- ESG detection results
- Error messages and debugging info
- Database update confirmations

## Environment Variables

Required:
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password

Optional:
- `CRAWLER_DELAY`: Default delay between requests
- `CRAWLER_TIMEOUT`: Default request timeout
- `CRAWLER_USER_AGENT`: Default user agent string

## Error Handling

- Network timeouts and connection errors are handled gracefully
- Failed companies are logged but don't stop batch processing
- Database connection issues are properly reported
- Invalid URLs are normalized or marked as inaccessible

## Performance Considerations

- Uses async/await for concurrent processing
- Connection pooling for database efficiency
- Respectful crawling with configurable delays
- Memory-efficient processing of large company batches

# See what versions have been processed
python esg_crawler.py --version 1.0 --show-stats
python esg_crawler.py --version 2.0 --show-stats
python esg_crawler.py --version 3.0 --show-stats
python esg_crawler.py --version 4.0 --show-stats

python esg_crawler.py --version 4.0 --batch-size 50 
python esg_crawler.py --version 2.0 --batch-size 25 --process-all


SELECT 
    smm_company_id,
    company_name,
    website_url,
    esg_info
FROM smm_companies 
WHERE esg_info IS NOT NULL 
AND EXISTS (
    SELECT 1 
    FROM jsonb_array_elements(esg_info) AS elem
    WHERE elem->>'crawler_version' = '3.0'
);

SELECT 
    smm_company_id,
    company_name,
    website_url,
    elem->>'crawler_version' as version,
    elem->>'has_esg_reports' as has_esg_reports,
    elem->>'analysis_timestamp' as timestamp,
    elem->>'evidence' as evidence
FROM smm_companies,
jsonb_array_elements(esg_info) AS elem
WHERE elem->>'crawler_version' = '3.0'
ORDER BY smm_company_id;

SELECT COUNT(*) as companies_with_v3
FROM smm_companies 
WHERE esg_info IS NOT NULL 
AND EXISTS (
    SELECT 1 
    FROM jsonb_array_elements(esg_info) AS elem
    WHERE elem->>'crawler_version' = '3.0'
);


SELECT 
    smm_company_id,
    company_name as name,
    COALESCE((
        SELECT elem->>'has_esg_reports'
        FROM jsonb_array_elements(esg_info) AS elem
        WHERE elem->>'crawler_version' = '1.0'
        LIMIT 1
    ), 'N/A') as v1_result,
    
    COALESCE((
        SELECT elem->>'has_esg_reports'
        FROM jsonb_array_elements(esg_info) AS elem
        WHERE elem->>'crawler_version' = '2.0'
        LIMIT 1
    ), 'N/A') as v2_result,
    
    COALESCE((
        SELECT elem->>'has_esg_reports'
        FROM jsonb_array_elements(esg_info) AS elem
        WHERE elem->>'crawler_version' = '3.0'
        LIMIT 1
    ), 'N/A') as v3_result,
    esg_info
FROM smm_companies 
WHERE esg_info IS NOT NULL
ORDER BY smm_company_id;