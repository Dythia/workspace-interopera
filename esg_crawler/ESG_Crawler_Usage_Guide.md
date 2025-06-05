# ESG Crawler Usage Guide

## 🚀 **Single Command to Analyze All Data**

### **Complete Analysis Command (Recommended)**
```bash
python esg_crawler.py --version 1.0 --batch-size 25
```

This command will:
- ✅ Process **all 1,220 companies** automatically
- ✅ Show **beautiful tqdm progress bars** with real-time updates
- ✅ **Skip companies** that already have Version 1.0 analysis
- ✅ **Append results** to existing data
- ✅ Handle **pagination automatically**

## 📊 **Batch Size Options**

### **Recommended (Balanced Speed & Reliability)**
```bash
# Process all companies with optimal batch size
python esg_crawler.py --version 1.0 --batch-size 25
```

### **Fast Processing (High Performance)**
```bash
# Larger batches for faster completion
python esg_crawler.py --version 1.0 --batch-size 50
```

### **Conservative (Safer for Unstable Networks)**
```bash
# Smaller batches for maximum reliability
python esg_crawler.py --version 1.0 --batch-size 10
```

## ⏱️ **Expected Completion Time**

Based on current stats (1,220 companies):
- **Batch size 10**: ~122 batches = ~3-4 hours
- **Batch size 25**: ~49 batches = ~2-3 hours
- **Batch size 50**: ~25 batches = ~1-2 hours  
- **Batch size 100**: ~13 batches = ~45-60 minutes

## 🎯 **Skip Logic (Default Behavior)**

### **Automatic Skipping**
The crawler **automatically skips companies** that already have the specified version analysis:

```sql
-- Only selects companies WITHOUT the specified version
WHERE (
    esg_info IS NULL 
    OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(esg_info) AS elem
        WHERE elem->>'crawler_version' = '1.0'
    )
)
```

### **Available Processing Modes**

#### **Default: Skip Existing (Recommended)**
```bash
python esg_crawler.py --version 1.0 --batch-size 25
# ✅ Skips companies with Version 1.0 analysis
```

#### **Force Re-analysis: Process All**
```bash
python esg_crawler.py --version 1.0 --batch-size 25 --force-reanalysis
# ⚠️ Re-analyzes ALL companies, even those with Version 1.0
```

#### **Replace Mode: Overwrite Existing**
```bash
python esg_crawler.py --version 1.0 --batch-size 25 --replace-existing
# 🔄 Overwrites ALL previous analysis data
```

## 🔄 **Data Appending vs Replacing**

### **Append Mode (Default)**
```bash
python esg_crawler.py --version 2.0 --batch-size 10
# Result: Adds Version 2.0 analysis to companies without it
```

### **Replace Mode**
```bash
python esg_crawler.py --version 2.0 --batch-size 10 --replace-existing
# Result: Deletes all previous analyses, keeps only new Version 2.0
```

## 📈 **Progress Visualization with tqdm**

The crawler now includes beautiful progress bars showing:
- **Real-time progress**: `33%`, `67%`, `100%`
- **Company names**: Current company being processed
- **Timing info**: `[00:08<00:00, 2.96s/companies]`
- **ESG status**: `✅ ESG Found` or `❌ No ESG`

Example output:
```
ESG v2.0 [3/1210] PT Sinar Tambang Arthalestari: 100%|████████| 3/3 [00:08<00:00, 2.96s/companies]
```

## 🎯 **Pagination and Offset**

### **Understanding Parameters**
- **`--batch-size`**: Number of companies to process in each batch
- **`--offset`**: Starting position (0-based index)

### **Manual Pagination Examples**
```bash
# Process first batch (companies 1-25)
python esg_crawler.py --version 1.0 --batch-size 25 --offset 0

# Process second batch (companies 26-50)
python esg_crawler.py --version 1.0 --batch-size 25 --offset 25

# Process third batch (companies 51-75)
python esg_crawler.py --version 1.0 --batch-size 25 --offset 50
```

### **Resume from Specific Point**
```bash
# If you processed 100 companies and want to continue
python esg_crawler.py --version 1.0 --batch-size 25 --offset 100
```

## 📊 **Statistics and Monitoring**

### **Check Progress**
```bash
# Show statistics for each version
python esg_crawler.py --version 1.0 --show-stats
python esg_crawler.py --version 2.0 --show-stats  
python esg_crawler.py --version 3.0 --show-stats
python esg_crawler.py --version 4.0 --show-stats
```

### **Example Statistics Output**
```
=== ESG Analysis Statistics for Version 1.0 ===
Total companies with websites: 1220
Companies needing analysis: 1220
Companies already analyzed: 0

Analysis Progress: 0.0% complete

Batches needed for remaining 1220 companies:
  Batch size 10: 122 batches
  Batch size 25: 49 batches
  Batch size 50: 25 batches
  Batch size 100: 13 batches

Version Analysis Summary:
  Version 2.0: 10 companies
  Version 3.0: 10 companies
  Version 4.0: 13 companies
```

## 🔧 **Advanced Options**

### **Custom Delays**
```bash
# Slower, more respectful crawling
python esg_crawler.py --version 1.0 --batch-size 10 --delay 2.0
```

### **Single Company Testing**
```bash
# Test specific company
python esg_crawler.py --version 1.0 --company-id 123 --website https://example.com
```

### **Version-Specific Features**

#### **Version 1.0: Basic Keyword Detection**
```bash
python esg_crawler.py --version 1.0 --batch-size 25
```

#### **Version 2.0: Enhanced Scoring Algorithm**
```bash
python esg_crawler.py --version 2.0 --batch-size 25
```

#### **Version 3.0: Document Discovery + Quantitative Analysis**
```bash
python esg_crawler.py --version 3.0 --batch-size 15
```

#### **Version 4.0: Advanced NLP Processing**
```bash
python esg_crawler.py --version 4.0 --batch-size 5
```

## 🎊 **Quick Start**

For immediate full analysis of all companies:

```bash
python esg_crawler.py --version 1.0 --batch-size 25
```

This single command will efficiently process your entire dataset with beautiful progress visualization! 🚀
