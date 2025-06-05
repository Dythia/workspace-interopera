# ESG Crawler Version 3.0 - Document Discovery & Quantitative Analysis

## Overview

Version 3.0 of the ESG crawler introduces advanced document discovery capabilities and sophisticated quantitative data extraction. This version builds upon the enhanced scoring algorithm from Version 2.0 and adds powerful new features for comprehensive ESG content analysis.

## Key Features

### 🔍 Document Discovery
- **PDF Detection**: Automatically discovers and catalogs PDF documents on company websites
- **Office Document Detection**: Identifies DOC, DOCX, XLS, XLSX, PPT, and PPTX files
- **Sustainability Document Classification**: Intelligently identifies documents likely to contain ESG/sustainability content
- **Document Analysis Summary**: Provides comprehensive statistics on discovered documents

### 📊 Quantitative Data Extraction
- **Percentage Detection**: Extracts percentage values from content (e.g., "50% reduction")
- **Target Identification**: Finds sustainability targets and goals with specific values
- **Metrics Extraction**: Identifies quantitative metrics (tons, kWh, CO2, etc.)
- **Year Detection**: Captures target years and timeframes (2020-2050)
- **Numerical Goals**: Detects commitments like "net zero", "carbon neutral", "100% renewable"

### 🎯 Enhanced Scoring Algorithm
- **Multi-dimensional Analysis**: Combines content quality, document discovery, and quantitative data
- **Weighted Scoring**: Different weights for high-impact vs. medium-impact sustainability indicators
- **Confidence Calculation**: Advanced confidence scoring based on multiple evidence sources
- **Threshold-based Detection**: Sophisticated ESG presence determination

## Usage

### Command Line Interface

```bash
# Run Version 3.0 with document discovery and quantitative analysis
python esg_crawler.py --version 3.0

# Process specific company with Version 3.0
python esg_crawler.py --version 3.0 --company-id 123 --website https://example.com

# Batch processing with Version 3.0
python esg_crawler.py --version 3.0 --batch-size 5 --delay 2.0
```

### Version Comparison

| Feature | Version 1.0 | Version 2.0 | Version 3.0 |
|---------|-------------|-------------|-------------|
| Basic keyword detection | ✅ | ✅ | ✅ |
| Enhanced scoring algorithm | ❌ | ✅ | ✅ |
| Weighted impact analysis | ❌ | ✅ | ✅ |
| Document discovery | ❌ | ❌ | ✅ |
| Quantitative data extraction | ❌ | ❌ | ✅ |
| Advanced confidence scoring | ❌ | ✅ | ✅ |

## Output Structure

Version 3.0 produces comprehensive analysis results with the following structure:

```json
{
  "has_esg_reports": true,
  "analysis_timestamp": "2025-08-21T20:40:00",
  "website_analysis": {
    "is_accessible": true,
    "sustainability_section_found": true,
    "sustainability_links_found": 3
  },
  "crawling_evidence": {
    "detection_method": "document_discovery_with_quantitative_analysis",
    "sustainability_score": 7.5,
    "confidence_level": 0.85,
    "keywords_found": [...],
    "navigation_matches": [...],
    "title_matches": [...],
    "document_discovery": {
      "pdf_documents": [
        {
          "url": "/sustainability-report-2024.pdf",
          "link_text": "sustainability report 2024",
          "type": "pdf",
          "is_sustainability_related": true
        }
      ],
      "doc_documents": [...],
      "total_documents_found": 5,
      "sustainability_documents": [...],
      "document_analysis_summary": {
        "total_pdfs": 3,
        "total_office_docs": 2,
        "sustainability_related_docs": 4,
        "sustainability_ratio": 0.8
      }
    },
    "quantitative_patterns": {
      "percentages_found": ["50%", "25%", "100%"],
      "targets_found": ["2030", "2050"],
      "metrics_found": ["1000 tons", "500 kwh"],
      "years_found": ["2030", "2050"],
      "numerical_goals": ["net zero", "carbon neutral"]
    },
    "quantitative_data_found": true,
    "targets_or_goals_found": true
  }
}
```

## Technical Implementation

### Document Discovery Algorithm

The document discovery system:

1. **Link Extraction**: Scans all `<a>` tags with `href` attributes
2. **File Type Detection**: Identifies documents by file extensions
3. **Content Analysis**: Examines link text and URLs for sustainability keywords
4. **Classification**: Categorizes documents as sustainability-related or general
5. **Summary Generation**: Provides comprehensive statistics and ratios

### Quantitative Data Extraction

The quantitative analysis uses advanced regex patterns:

- **Percentage Pattern**: `(\d+(?:\.\d+)?)\s*%`
- **Target Pattern**: `(?:target|goal|aim|reduce|increase|achieve)\s+(?:by\s+)?(\d{4}|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:million|billion|thousand|tons?|kg|mt))`
- **Metric Pattern**: `(\d+(?:,\d{3})*(?:\.\d+)?)\s*(tons?|kg|mt|kwh|mwh|gwh|co2|carbon|emissions|energy|water|waste)`
- **Year Pattern**: `\b(20\d{2})\b` (filtered for 2020-2050)
- **Numerical Goal Pattern**: `(?:net.zero|carbon.neutral|zero.emissions|100%\s*renewable)`

### Enhanced Scoring System

Version 3.0 scoring combines:

- **Base Score**: Version 2.0 enhanced scoring algorithm (0-10 scale)
- **Document Score**: Up to 0.3 points for document discovery + 0.15 per sustainability document
- **Quantitative Score**: Up to 0.75 points for quantitative data patterns
- **Final Score**: Capped at 10.0 for consistency

### Confidence Calculation

Confidence factors include:
- Base confidence from Version 2.0
- Document confidence (0.1 per sustainability document, max 0.2)
- Quantitative confidence (0.05 per target found, max 0.1)
- Final confidence capped at 1.0

## Detection Thresholds

Version 3.0 uses enhanced thresholds:
- **ESG Presence**: Sustainability score ≥ 2.5 OR confidence ≥ 0.7 OR Version 2.0 detection
- **High Confidence**: Confidence ≥ 0.8 with quantitative data
- **Document Rich**: ≥ 3 sustainability documents discovered

## Performance Considerations

- **Processing Time**: ~20-30% longer than Version 2.0 due to document analysis
- **Memory Usage**: Moderate increase for storing document metadata
- **Network Requests**: Same as previous versions (no additional HTTP requests)
- **Database Storage**: Larger JSON payloads due to comprehensive evidence

## Migration from Previous Versions

### From Version 1.0
- All existing functionality preserved
- Enhanced evidence structure with new fields
- Backward compatible database storage

### From Version 2.0
- All Version 2.0 features included
- Additional document discovery and quantitative analysis
- Extended evidence structure with new sections

## Best Practices

1. **Batch Processing**: Use smaller batch sizes (5-10) for Version 3.0 due to increased processing
2. **Delay Configuration**: Consider 2-3 second delays for respectful crawling
3. **Result Analysis**: Focus on `document_discovery` and `quantitative_patterns` for Version 3.0 insights
4. **Confidence Interpretation**: Confidence ≥ 0.7 indicates high-quality ESG content detection

## Troubleshooting

### Common Issues

1. **High Processing Time**: Reduce batch size or increase delays
2. **Memory Usage**: Monitor for large document lists on content-heavy sites
3. **False Positives**: Review quantitative patterns for context relevance

### Debug Information

Version 3.0 provides extensive debug information:
- Document discovery statistics
- Quantitative pattern matches
- Enhanced confidence breakdown
- Processing timestamps

## Future Enhancements

Planned features for future versions:
- Multi-language keyword support
- Deep content crawling (multi-page analysis)
- ESG compliance scoring
- Industry-specific modifiers
- Advanced NLP processing
- Source credibility assessment

## Support

For issues or questions about Version 3.0:
1. Check the comprehensive evidence output for debugging
2. Review document discovery and quantitative patterns
3. Verify sustainability score and confidence calculations
4. Compare results with previous versions for validation

---

**Version 3.0** represents a significant advancement in ESG content detection, providing unprecedented insight into corporate sustainability reporting through intelligent document discovery and sophisticated quantitative analysis.
