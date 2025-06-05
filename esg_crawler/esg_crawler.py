#!/usr/bin/env python3
"""
Standalone ESG Report Crawler

This script crawls company websites to detect ESG/sustainability reports
and updates the production database smm_companies table with the results.

Usage:
    python esg_crawler.py --help
    python esg_crawler.py --batch-size 10 --delay 2.0
    python esg_crawler.py --company-id 123 --website https://example.com
"""

import asyncio
import aiohttp
import json
import logging
import sys
import time
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
import re

from bs4 import BeautifulSoup
import asyncpg
from tqdm import tqdm
import os
from dotenv import load_dotenv

# NLP imports for Version 4.0
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from collections import Counter
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    print("Warning: NLP libraries not available. Version 4.0 will fall back to Version 3.0 functionality.")

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('esg_crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CrawlerConfig:
    """Configuration for the ESG report crawler service"""
    max_depth: int = 2
    max_pages_per_site: int = 20
    request_delay: float = 1.0
    timeout: int = 15
    user_agent: str = "ESGReportBot/1.0"

@dataclass
class WebsiteAnalysis:
    """Analysis result of website structure and ESG content accessibility"""
    base_url: str
    is_accessible: bool
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    page_size: Optional[int] = None
    has_navigation: bool = False
    language: str = 'unknown'
    sustainability_section_found: bool = False
    sustainability_links_found: int = 0
    total_links_found: int = 0
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

@dataclass
class ESGReportAnalysisResult:
    """Result of ESG report analysis for a company website"""
    company_website: str
    collection_timestamp: str
    website_analysis: Dict[str, Any]
    has_esg_reports: bool  # True if ESG/sustainability reports found, False otherwise
    crawling_evidence: Dict[str, Any] = None  # Proof of what content was found during crawling
    crawler_config: Dict[str, Any] = None  # Configuration used during crawling
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), indent=2, default=str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

class ESGReportCrawler:
    """Standalone ESG report crawler for database operations"""
    
    def __init__(self, config: CrawlerConfig = None, version: str = "1.0"):
        self.config = config or CrawlerConfig()
        self.db_pool = None
        self.version = version
        
        # ESG/Sustainability-related URL patterns for detection
        self.esg_url_patterns = [
            r'/sustainability',
            r'/esg',
            r'/csr',
            r'/corporate-responsibility',
            r'/environmental',
            r'/social-responsibility',
            r'/governance',
            r'/annual-report',
            r'/impact-report',
            r'/investor-relations',
            r'/responsibility',
            r'/climate',
            r'/carbon'
        ]
        
        # Keywords that indicate ESG/sustainability reports
        self.esg_keywords = [
            'sustainability report',
            'esg report',
            'csr report',
            'environmental report',
            'social responsibility report',
            'annual sustainability',
            'impact report',
            'corporate responsibility report',
            'governance report',
            'climate report',
            'carbon report',
            'environmental social governance'
        ]
    
    async def init_database(self):
        """Initialize database connection pool"""
        try:
            # Database configuration from environment variables
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'nexus'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', ''),
            }
            
            self.db_pool = await asyncpg.create_pool(
                **db_config,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close_database(self):
        """Close database connection pool"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database connection pool closed")
    
    async def get_companies_to_process(self, limit: Optional[int] = None, offset: int = 0, 
                                     force_reanalysis: bool = False) -> List[Dict[str, Any]]:
        """Get companies from smm_companies table that need ESG analysis with pagination and version awareness"""
        
        if force_reanalysis:
            # Re-analyze all companies with valid websites (for new versions)
            query = """
            SELECT smm_company_id, name, primary_domain as website, esg_info
            FROM smm_companies 
            WHERE primary_domain IS NOT NULL 
            AND primary_domain != ''
            ORDER BY smm_company_id
            """
        else:
            # Version-aware selection: companies without this specific version analysis
            query = f"""
            SELECT smm_company_id, name, primary_domain as website, esg_info
            FROM smm_companies 
            WHERE primary_domain IS NOT NULL 
            AND primary_domain != ''
            AND (
                esg_info IS NULL 
                OR NOT EXISTS (
                    SELECT 1 FROM jsonb_array_elements(
                        CASE 
                            WHEN jsonb_typeof(esg_info) = 'array' THEN esg_info
                            WHEN esg_info IS NOT NULL THEN jsonb_build_array(esg_info)
                            ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE elem->>'crawler_version' = '{self.version}'
                )
            )
            ORDER BY smm_company_id
            """
        
        # Add pagination
        if offset > 0:
            query += f" OFFSET {offset}"
        if limit:
            query += f" LIMIT {limit}"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def get_total_companies_count(self, force_reanalysis: bool = False) -> int:
        """Get total count of companies that need ESG analysis"""
        
        if force_reanalysis:
            query = """
            SELECT COUNT(*) as total
            FROM smm_companies 
            WHERE primary_domain IS NOT NULL 
            AND primary_domain != ''
            """
        else:
            query = f"""
            SELECT COUNT(*) as total
            FROM smm_companies 
            WHERE primary_domain IS NOT NULL 
            AND primary_domain != ''
            AND (
                esg_info IS NULL 
                OR NOT EXISTS (
                    SELECT 1 FROM jsonb_array_elements(
                        CASE 
                            WHEN jsonb_typeof(esg_info) = 'array' THEN esg_info
                            WHEN esg_info IS NOT NULL THEN jsonb_build_array(esg_info)
                            ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE elem->>'crawler_version' = '{self.version}'
                )
            )
            """
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(query)
            return result or 0
    
    async def update_company_esg_info(self, company_id: int, esg_result: ESGReportAnalysisResult, replace_existing: bool = False):
        """Update company ESG info in database by appending to existing results or replacing them"""
        try:
            # Create new analysis entry
            new_analysis = {
                'has_esg_reports': esg_result.has_esg_reports,
                'analysis_timestamp': esg_result.collection_timestamp,
                'website_analysis': esg_result.website_analysis,
                'crawling_evidence': esg_result.crawling_evidence,
                'crawler_config': esg_result.crawler_config,
                'crawler_version': self.version
            }
            
            if replace_existing:
                # Replace mode: overwrite all existing data with new analysis
                updated_analysis = [new_analysis]
                operation_type = "Replaced"
            else:
                # Append mode: add to existing data (default behavior)
                # First, get existing ESG analysis data
                select_query = """
                SELECT esg_info FROM smm_companies 
                WHERE smm_company_id = $1
                """
                
                async with self.db_pool.acquire() as conn:
                    existing_data = await conn.fetchval(select_query, company_id)
                    
                    # Prepare the updated analysis array
                    if existing_data is None:
                        # No existing data, create new array
                        updated_analysis = [new_analysis]
                    else:
                        # Parse existing data
                        if isinstance(existing_data, str):
                            existing_analysis = json.loads(existing_data)
                        else:
                            existing_analysis = existing_data
                        
                        # Ensure it's a list
                        if not isinstance(existing_analysis, list):
                            existing_analysis = [existing_analysis]
                        
                        # Append new analysis to existing array
                        existing_analysis.append(new_analysis)
                        updated_analysis = existing_analysis
                    
                operation_type = "Appended"
            
            # Update the database with the analysis array
            update_query = """
            UPDATE smm_companies 
            SET esg_info = $1, updated_at = NOW()
            WHERE smm_company_id = $2
            """
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(update_query, json.dumps(updated_analysis), company_id)
                logger.info(f"{operation_type} ESG analysis for company {company_id} (total analyses: {len(updated_analysis)})")
                
        except Exception as e:
            logger.error(f"Failed to update company {company_id}: {e}")
            raise
    
    async def analyze_company_website(self, company_website: str) -> ESGReportAnalysisResult:
        """
        Analyze company website for ESG/sustainability report presence
        
        Args:
            company_website: Company website URL to analyze
            
        Returns:
            ESGReportAnalysisResult: Analysis result with boolean ESG report detection
        """
        collection_timestamp = datetime.now().isoformat()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={'User-Agent': self.config.user_agent}
            ) as session:
                
                # Analyze website structure and get soup
                website_analysis, soup = await self._analyze_website_structure(session, company_website)
                
                # Detect ESG content and get evidence
                has_esg_reports, crawling_evidence = self._detect_esg_content(soup)
                
                # Add URL pattern detection to evidence
                crawling_evidence["url_patterns_found"] = self._detect_esg_url_patterns(company_website)
                
                # Log the result with evidence summary
                evidence_summary = {
                    "keywords_count": len(crawling_evidence["keywords_found"]),
                    "nav_matches_count": len(crawling_evidence["navigation_matches"]),
                    "title_matches_count": len(crawling_evidence["title_matches"]),
                    "url_patterns_count": len(crawling_evidence["url_patterns_found"])
                }
                logger.info(f"ESG analysis complete for {company_website}: ESG reports found = {has_esg_reports}, Evidence: {evidence_summary}")
                
                return ESGReportAnalysisResult(
                    company_website=company_website,
                    collection_timestamp=collection_timestamp,
                    website_analysis=website_analysis.to_dict(),
                    has_esg_reports=has_esg_reports,
                    crawling_evidence=crawling_evidence,
                    crawler_config=self._get_crawler_config_dict()
                )
                
        except Exception as e:
            logger.error(f"ESG analysis failed for {company_website}: {e}")
            
            # Return error result
            error_analysis = WebsiteAnalysis(
                base_url=company_website,
                is_accessible=False,
                error_message=str(e)
            )
            
            return ESGReportAnalysisResult(
                company_website=company_website,
                collection_timestamp=collection_timestamp,
                website_analysis=error_analysis.to_dict(),
                has_esg_reports=False
            )
    
    async def batch_analyze_companies(self, company_websites: List[str]) -> List[ESGReportAnalysisResult]:
        """
        Analyze multiple company websites in batch
        
        Args:
            company_websites: List of company website URLs to analyze
            
        Returns:
            List[ESGReportAnalysisResult]: Analysis results for all companies
        """
        tasks = [self.analyze_company_website(website) for website in company_websites]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to analyze {company_websites[i]}: {result}")
                # Create error result
                error_result = ESGReportAnalysisResult(
                    company_website=company_websites[i],
                    collection_timestamp=datetime.now().isoformat(),
                    website_analysis=WebsiteAnalysis(
                        base_url=company_websites[i],
                        is_accessible=False,
                        error_message=str(result)
                    ).to_dict(),
                    has_esg_reports=False
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _analyze_website_structure(self, session: aiohttp.ClientSession, base_url: str) -> tuple[WebsiteAnalysis, BeautifulSoup]:
        """Analyze website structure and look for ESG/sustainability indicators"""
        start_time = time.time()
        
        try:
            # Normalize URL
            normalized_url = self._normalize_url(base_url)
            
            # Add delay for respectful crawling
            await asyncio.sleep(self.config.request_delay)
            
            # Fetch the homepage
            async with session.get(normalized_url) as response:
                response_time = time.time() - start_time
                
                if response.status != 200:
                    return WebsiteAnalysis(
                        base_url=normalized_url,
                        is_accessible=False,
                        status_code=response.status,
                        response_time=response_time,
                        error_message=f"HTTP {response.status}"
                    ), BeautifulSoup("", 'html.parser')
                
                content = await response.text()
                content_type = response.headers.get('content-type', '')
                
                # Parse content with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract all links from homepage
                all_links = self._extract_links(soup, normalized_url)
                
                # Filter ESG/sustainability-related links
                esg_links = self._filter_esg_links(all_links)
                
                # Detect ESG content on homepage
                homepage_has_esg = self._detect_esg_content(soup)
                
                return WebsiteAnalysis(
                    base_url=normalized_url,
                    is_accessible=True,
                    status_code=response.status,
                    content_type=content_type,
                    page_size=len(content),
                    has_navigation=self._detect_navigation(soup),
                    language=self._detect_language(soup),
                    sustainability_section_found=homepage_has_esg or len(esg_links) > 0,
                    sustainability_links_found=len(esg_links),
                    total_links_found=len(all_links),
                    response_time=response_time
                ), soup
                
        except asyncio.TimeoutError:
            return WebsiteAnalysis(
                base_url=base_url,
                is_accessible=False,
                error_message="Request timeout",
                response_time=time.time() - start_time
            ), BeautifulSoup("", 'html.parser')
        except Exception as e:
            return WebsiteAnalysis(
                base_url=base_url,
                is_accessible=False,
                error_message=str(e),
                response_time=time.time() - start_time
            ), BeautifulSoup("", 'html.parser')
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to standard format"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip('/') or '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all valid links from the page"""
        links = []
        
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href'].strip()
            
            # Skip empty hrefs, javascript, mailto, etc.
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include HTTP/HTTPS links from same domain
            if (absolute_url.startswith(('http://', 'https://')) and 
                self._is_same_domain(absolute_url, base_url)):
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    def _is_same_domain(self, link: str, base_url: str) -> bool:
        """Check if link is from the same domain"""
        try:
            link_domain = urlparse(link).netloc.lower()
            base_domain = urlparse(base_url).netloc.lower()
            return link_domain == base_domain
        except Exception:
            return False
    
    def _filter_esg_links(self, links: List[str]) -> List[str]:
        """Filter links that likely contain ESG/sustainability content"""
        esg_links = []
        
        for link in links:
            link_lower = link.lower()
            
            # Check URL patterns
            for pattern in self.esg_url_patterns:
                if re.search(pattern, link_lower):
                    esg_links.append(link)
                    break
        
        return esg_links
    
    def _detect_esg_content(self, soup: BeautifulSoup) -> tuple[bool, Dict[str, Any]]:
        """Detect ESG content using version-specific logic"""
        if self.version == "4.0":
            return self._detect_esg_content_v4(soup)
        elif self.version == "3.0":
            return self._detect_esg_content_v3(soup)
        elif self.version == "2.0":
            return self._detect_esg_content_v2(soup)
        else:
            return self._detect_esg_content_v1(soup)
    
    def _detect_esg_content_v1(self, soup: BeautifulSoup) -> tuple[bool, Dict[str, Any]]:
        """Version 1: Basic keyword detection with evidence"""
        evidence = {
            "keywords_found": [],
            "navigation_matches": [],
            "title_matches": [],
            "url_patterns_found": [],
            "content_snippets": [],
            "detection_timestamp": datetime.now().isoformat(),
            "detection_method": "basic_keyword_matching"
        }
        
        has_esg = False
        
        # Get all text content from the page
        page_text = soup.get_text().lower()
        
        # Check for ESG keywords in page content
        for keyword in self.esg_keywords:
            if keyword in page_text:
                has_esg = True
                evidence["keywords_found"].append(keyword)
                # Extract snippet around the keyword for proof
                start_idx = page_text.find(keyword)
                snippet_start = max(0, start_idx - 50)
                snippet_end = min(len(page_text), start_idx + len(keyword) + 50)
                snippet = page_text[snippet_start:snippet_end].strip()
                evidence["content_snippets"].append({
                    "keyword": keyword,
                    "snippet": snippet,
                    "position": start_idx
                })
        
        # Check for ESG-related navigation items
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu', re.I))
        for nav in nav_elements:
            nav_text = nav.get_text().lower()
            esg_nav_keywords = ['sustainability', 'esg', 'csr', 'responsibility', 'environmental', 'governance']
            for keyword in esg_nav_keywords:
                if keyword in nav_text:
                    has_esg = True
                    evidence["navigation_matches"].append({
                        "keyword": keyword,
                        "nav_text": nav_text.strip()[:200],  # First 200 chars
                        "element_type": nav.name,
                        "element_class": nav.get('class', [])
                    })
        
        # Check page title and meta description
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            title_keywords = ['sustainability', 'esg', 'csr', 'responsibility']
            for keyword in title_keywords:
                if keyword in title_text:
                    has_esg = True
                    evidence["title_matches"].append({
                        "keyword": keyword,
                        "full_title": title.get_text().strip()
                    })
        
        return has_esg, evidence
    
    def _detect_esg_content_v2(self, soup: BeautifulSoup) -> tuple[bool, Dict[str, Any]]:
        """Version 2: Enhanced scoring algorithm based on Sunterra design"""
        evidence = {
            "keywords_found": [],
            "navigation_matches": [],
            "title_matches": [],
            "url_patterns_found": [],
            "content_snippets": [],
            "detection_timestamp": datetime.now().isoformat(),
            "detection_method": "enhanced_scoring_algorithm",
            "sustainability_score": 0.0,
            "confidence_level": 0.0,
            "content_quality_analysis": {},
            "quantitative_data_found": False,
            "targets_or_goals_found": False
        }
        
        # Enhanced keyword categories with different weights
        sustainability_keywords = {
            'high_impact': [
                'sustainability report', 'carbon footprint', 'net zero', 
                'science-based targets', 'ESG strategy', 'climate action'
            ],
            'medium_impact': [
                'green initiatives', 'renewable energy', 'energy efficiency',
                'waste reduction', 'circular economy'
            ],
            'low_impact': [
                'eco-friendly', 'sustainable practices', 'environmental awareness'
            ]
        }
        
        page_text = soup.get_text().lower()
        content_quality_score = 0.0
        
        # Analyze content quality with weighted scoring
        high_impact_matches = 0
        medium_impact_matches = 0
        low_impact_matches = 0
        
        # Check for high-impact keywords
        for keyword in sustainability_keywords['high_impact']:
            if keyword in page_text:
                high_impact_matches += 1
                evidence["keywords_found"].append({"keyword": keyword, "impact": "high"})
                # Extract snippet
                start_idx = page_text.find(keyword)
                snippet_start = max(0, start_idx - 50)
                snippet_end = min(len(page_text), start_idx + len(keyword) + 50)
                snippet = page_text[snippet_start:snippet_end].strip()
                evidence["content_snippets"].append({
                    "keyword": keyword,
                    "snippet": snippet,
                    "impact_level": "high",
                    "position": start_idx
                })
        
        # Check for medium-impact keywords
        for keyword in sustainability_keywords['medium_impact']:
            if keyword in page_text:
                medium_impact_matches += 1
                evidence["keywords_found"].append({"keyword": keyword, "impact": "medium"})
        
        # Check for low-impact keywords
        for keyword in sustainability_keywords['low_impact']:
            if keyword in page_text:
                low_impact_matches += 1
                evidence["keywords_found"].append({"keyword": keyword, "impact": "low"})
        
        # Calculate content quality score (0-1 scale)
        content_quality_score += min(0.4, high_impact_matches * 0.1)    # Max 0.4 for high-impact
        content_quality_score += min(0.3, medium_impact_matches * 0.05) # Max 0.3 for medium-impact  
        content_quality_score += min(0.1, low_impact_matches * 0.02)    # Max 0.1 for low-impact
        
        # Check for quantitative information
        quantitative_pattern = re.search(r'\d+%|\d+\s*(tons?|tonnes?|MW|GW|kWh|CO2|carbon)', page_text)
        if quantitative_pattern:
            content_quality_score += 0.15
            evidence["quantitative_data_found"] = True
            evidence["content_snippets"].append({
                "type": "quantitative_data",
                "snippet": quantitative_pattern.group(),
                "context": page_text[max(0, quantitative_pattern.start()-30):quantitative_pattern.end()+30]
            })
        
        # Check for specific targets or dates
        targets_pattern = re.search(r'by\s+20\d{2}|target|goal|commitment', page_text)
        if targets_pattern:
            content_quality_score += 0.05
            evidence["targets_or_goals_found"] = True
        
        # Enhanced navigation analysis
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu', re.I))
        nav_score = 0.0
        
        for nav in nav_elements:
            nav_text = nav.get_text().lower()
            esg_nav_keywords = ['sustainability', 'esg', 'csr', 'responsibility', 'environmental', 'governance']
            for keyword in esg_nav_keywords:
                if keyword in nav_text:
                    nav_score += 0.1
                    evidence["navigation_matches"].append({
                        "keyword": keyword,
                        "nav_text": nav_text.strip()[:200],
                        "element_type": nav.name,
                        "element_class": nav.get('class', []),
                        "confidence": 0.8
                    })
        
        # Enhanced title analysis
        title_score = 0.0
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            title_keywords = ['sustainability', 'esg', 'csr', 'responsibility']
            for keyword in title_keywords:
                if keyword in title_text:
                    title_score += 0.2
                    evidence["title_matches"].append({
                        "keyword": keyword,
                        "full_title": title.get_text().strip(),
                        "confidence": 0.9
                    })
        
        # Calculate overall sustainability score (0-10 scale)
        overall_score = (content_quality_score * 6.0) + (nav_score * 2.0) + (title_score * 2.0)
        overall_score = min(10.0, overall_score)
        
        # Calculate confidence level
        data_points = len(evidence["keywords_found"]) + len(evidence["navigation_matches"]) + len(evidence["title_matches"])
        confidence = min(1.0, 0.3 + (data_points * 0.1))
        
        # Store analysis results
        evidence["sustainability_score"] = round(overall_score, 2)
        evidence["confidence_level"] = round(confidence, 3)
        evidence["content_quality_analysis"] = {
            "high_impact_keywords": high_impact_matches,
            "medium_impact_keywords": medium_impact_matches,
            "low_impact_keywords": low_impact_matches,
            "content_quality_score": round(content_quality_score, 3),
            "navigation_score": round(nav_score, 3),
            "title_score": round(title_score, 3)
        }
        
        # Determine if ESG content is present (more sophisticated threshold)
        has_esg = overall_score >= 2.0 or confidence >= 0.6
        
        return has_esg, evidence
    
    def _detect_esg_content_v3(self, soup: BeautifulSoup) -> tuple[bool, Dict[str, Any]]:
        """Version 3: Enhanced with Document Discovery and Quantitative Data Extraction"""
        evidence = {
            "keywords_found": [],
            "navigation_matches": [],
            "title_matches": [],
            "url_patterns_found": [],
            "content_snippets": [],
            "detection_timestamp": datetime.now().isoformat(),
            "detection_method": "document_discovery_with_quantitative_analysis",
            "sustainability_score": 0.0,
            "confidence_level": 0.0,
            "content_quality_analysis": {},
            "quantitative_data_found": False,
            "targets_or_goals_found": False,
            "document_discovery": {
                "pdf_documents": [],
                "doc_documents": [],
                "total_documents_found": 0,
                "sustainability_documents": [],
                "document_analysis_summary": {}
            },
            "quantitative_patterns": {
                "percentages_found": [],
                "targets_found": [],
                "metrics_found": [],
                "years_found": [],
                "numerical_goals": []
            }
        }
        
        # Start with Version 2 scoring as base
        has_esg_v2, evidence_v2 = self._detect_esg_content_v2(soup)
        
        # Merge Version 2 evidence
        for key in evidence_v2:
            if key in evidence and key != "detection_method":
                evidence[key] = evidence_v2[key]
        
        # Document Discovery - Find PDF and DOC links
        documents_found = self._discover_documents(soup)
        evidence["document_discovery"] = documents_found
        
        # Enhanced Quantitative Data Extraction
        quantitative_data = self._extract_quantitative_data(soup)
        evidence["quantitative_patterns"] = quantitative_data
        
        # Calculate enhanced sustainability score with document discovery
        sustainability_score = evidence.get("sustainability_score", 0.0)
        
        # Document discovery scoring
        doc_score = 0.0
        if documents_found["total_documents_found"] > 0:
            doc_score += min(documents_found["total_documents_found"] * 0.1, 0.3)  # Max 0.3 for documents
            
        if documents_found["sustainability_documents"]:
            doc_score += len(documents_found["sustainability_documents"]) * 0.15  # Bonus for sustainability docs
            
        # Quantitative data scoring
        quant_score = 0.0
        if quantitative_data["percentages_found"]:
            quant_score += min(len(quantitative_data["percentages_found"]) * 0.05, 0.2)
        if quantitative_data["targets_found"]:
            quant_score += min(len(quantitative_data["targets_found"]) * 0.1, 0.3)
        if quantitative_data["numerical_goals"]:
            quant_score += min(len(quantitative_data["numerical_goals"]) * 0.08, 0.25)
            
        # Update sustainability score
        enhanced_score = sustainability_score + doc_score + quant_score
        evidence["sustainability_score"] = min(enhanced_score, 10.0)  # Keep same scale as v2
        
        # Update quantitative data flags
        evidence["quantitative_data_found"] = bool(
            quantitative_data["percentages_found"] or 
            quantitative_data["metrics_found"] or 
            quantitative_data["numerical_goals"]
        )
        evidence["targets_or_goals_found"] = bool(
            quantitative_data["targets_found"] or 
            quantitative_data["numerical_goals"]
        )
        
        # Enhanced confidence calculation
        base_confidence = evidence.get("confidence_level", 0.0)
        doc_confidence = min(len(documents_found["sustainability_documents"]) * 0.1, 0.2)
        quant_confidence = min(len(quantitative_data["targets_found"]) * 0.05, 0.1)
        evidence["confidence_level"] = min(base_confidence + doc_confidence + quant_confidence, 1.0)
        
        # Determine ESG presence with enhanced threshold
        has_esg = evidence["sustainability_score"] >= 2.5 or evidence["confidence_level"] >= 0.7 or has_esg_v2
        
        return has_esg, evidence
    
    def _discover_documents(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Discover PDF and DOC documents on the page"""
        document_discovery = {
            "pdf_documents": [],
            "doc_documents": [],
            "total_documents_found": 0,
            "sustainability_documents": [],
            "document_analysis_summary": {}
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        # Document file extensions to look for
        pdf_extensions = ['.pdf']
        doc_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        
        # Sustainability-related keywords for document analysis
        sustainability_doc_keywords = [
            'sustainability', 'esg', 'csr', 'responsibility', 'environmental',
            'carbon', 'climate', 'green', 'renewable', 'annual report',
            'impact report', 'governance', 'ethics', 'compliance'
        ]
        
        for link in links:
            href = link.get('href', '').lower()
            link_text = link.get_text().strip().lower()
            
            # Check for PDF documents
            if any(ext in href for ext in pdf_extensions):
                doc_info = {
                    "url": href,
                    "link_text": link_text,
                    "type": "pdf",
                    "is_sustainability_related": any(keyword in href or keyword in link_text 
                                                   for keyword in sustainability_doc_keywords)
                }
                document_discovery["pdf_documents"].append(doc_info)
                
                if doc_info["is_sustainability_related"]:
                    document_discovery["sustainability_documents"].append(doc_info)
            
            # Check for DOC/Office documents
            elif any(ext in href for ext in doc_extensions):
                doc_info = {
                    "url": href,
                    "link_text": link_text,
                    "type": "office_document",
                    "is_sustainability_related": any(keyword in href or keyword in link_text 
                                                   for keyword in sustainability_doc_keywords)
                }
                document_discovery["doc_documents"].append(doc_info)
                
                if doc_info["is_sustainability_related"]:
                    document_discovery["sustainability_documents"].append(doc_info)
        
        # Calculate totals
        document_discovery["total_documents_found"] = (
            len(document_discovery["pdf_documents"]) + 
            len(document_discovery["doc_documents"])
        )
        
        # Analysis summary
        document_discovery["document_analysis_summary"] = {
            "total_pdfs": len(document_discovery["pdf_documents"]),
            "total_office_docs": len(document_discovery["doc_documents"]),
            "sustainability_related_docs": len(document_discovery["sustainability_documents"]),
            "sustainability_ratio": (
                len(document_discovery["sustainability_documents"]) / 
                max(document_discovery["total_documents_found"], 1)
            )
        }
        
        return document_discovery
    
    def _extract_quantitative_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract quantitative data patterns from page content"""
        quantitative_patterns = {
            "percentages_found": [],
            "targets_found": [],
            "metrics_found": [],
            "years_found": [],
            "numerical_goals": []
        }
        
        page_text = soup.get_text()
        
        # Regex patterns for quantitative data
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        target_pattern = r'(?:target|goal|aim|reduce|increase|achieve)\s+(?:by\s+)?(\d{4}|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:million|billion|thousand|tons?|kg|mt))'
        metric_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(tons?|kg|mt|kwh|mwh|gwh|co2|carbon|emissions|energy|water|waste)'
        year_pattern = r'\b(20\d{2})\b'
        numerical_goal_pattern = r'(?:net.zero|carbon.neutral|zero.emissions|100%\s*renewable)'
        
        # Find percentages
        percentages = re.findall(percentage_pattern, page_text, re.IGNORECASE)
        for percentage in percentages:
            quantitative_patterns["percentages_found"].append(f"{percentage}%")
        
        # Find targets and goals
        targets = re.findall(target_pattern, page_text, re.IGNORECASE)
        for target in targets:
            quantitative_patterns["targets_found"].append(target)
        
        # Find metrics
        metrics = re.findall(metric_pattern, page_text, re.IGNORECASE)
        for value, unit in metrics:
            quantitative_patterns["metrics_found"].append(f"{value} {unit}")
        
        # Find years (likely target years)
        years = re.findall(year_pattern, page_text)
        # Filter for reasonable future years (2020-2050)
        relevant_years = [year for year in years if 2020 <= int(year) <= 2050]
        quantitative_patterns["years_found"] = list(set(relevant_years))
        
        # Find numerical goals (net zero, carbon neutral, etc.)
        numerical_goals = re.findall(numerical_goal_pattern, page_text, re.IGNORECASE)
        quantitative_patterns["numerical_goals"] = list(set(numerical_goals))
        
        return quantitative_patterns
    
    def _detect_esg_content_v4(self, soup: BeautifulSoup) -> tuple[bool, Dict[str, Any]]:
        """Version 4: Advanced NLP Processing with Sentiment Analysis and Named Entity Recognition"""
        # Download required NLTK data if not available
        self._ensure_nltk_data()
        
        evidence = {
            "keywords_found": [],
            "navigation_matches": [],
            "title_matches": [],
            "url_patterns_found": [],
            "content_snippets": [],
            "detection_timestamp": datetime.now().isoformat(),
            "detection_method": "advanced_nlp_processing",
            "sustainability_score": 0.0,
            "confidence_level": 0.0,
            "content_quality_analysis": {},
            "quantitative_data_found": False,
            "targets_or_goals_found": False,
            "document_discovery": {},
            "quantitative_patterns": {},
            "nlp_analysis": {
                "sentiment_analysis": {},
                "named_entities": [],
                "semantic_similarity": {},
                "content_summary": {},
                "esg_topics_identified": [],
                "commitment_strength": 0.0,
                "forward_looking_statements": [],
                "credibility_indicators": {}
            }
        }
        
        # Check if NLP libraries are available
        if not NLP_AVAILABLE:
            logger.warning("NLP libraries not available. Falling back to Version 3.0")
            return self._detect_esg_content_v3(soup)
        
        # Start with Version 3 as base
        has_esg_v3, evidence_v3 = self._detect_esg_content_v3(soup)
        
        # Merge Version 3 evidence
        for key in evidence_v3:
            if key in evidence and key != "detection_method":
                evidence[key] = evidence_v3[key]
        
        # Advanced NLP Processing
        page_text = soup.get_text()
        nlp_results = self._perform_nlp_analysis(page_text)
        evidence["nlp_analysis"] = nlp_results
        
        # Calculate enhanced sustainability score with NLP insights
        base_score = evidence.get("sustainability_score", 0.0)
        nlp_score = self._calculate_nlp_score(nlp_results)
        
        # Enhanced scoring with NLP factors
        enhanced_score = base_score + nlp_score
        evidence["sustainability_score"] = min(enhanced_score, 10.0)
        
        # Enhanced confidence with NLP factors
        base_confidence = evidence.get("confidence_level", 0.0)
        nlp_confidence = self._calculate_nlp_confidence(nlp_results)
        evidence["confidence_level"] = min(base_confidence + nlp_confidence, 1.0)
        
        # Determine ESG presence with NLP enhancement
        has_esg = (
            evidence["sustainability_score"] >= 3.0 or 
            evidence["confidence_level"] >= 0.75 or 
            nlp_results["commitment_strength"] >= 0.7 or
            has_esg_v3
        )
        
        return has_esg, evidence
    
    def _perform_nlp_analysis(self, text: str) -> Dict[str, Any]:
        """Perform comprehensive NLP analysis on the text content"""
        if not NLP_AVAILABLE:
            return {}
        
        try:
            # Initialize NLP tools
            sia = SentimentIntensityAnalyzer()
            lemmatizer = WordNetLemmatizer()
            
            # Download required NLTK data if not present
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            try:
                nltk.data.find('corpora/wordnet')
            except LookupError:
                nltk.download('wordnet', quiet=True)
            
            try:
                nltk.data.find('vader_lexicon')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
            
            # Sentiment Analysis
            sentiment_scores = sia.polarity_scores(text)
            
            # Tokenization and preprocessing
            sentences = sent_tokenize(text)
            words = word_tokenize(text.lower())
            stop_words = set(stopwords.words('english'))
            filtered_words = [lemmatizer.lemmatize(word) for word in words if word.isalpha() and word not in stop_words]
            
            # ESG-specific sentiment analysis
            esg_sentences = [sent for sent in sentences if self._contains_esg_keywords(sent)]
            esg_sentiment = np.mean([sia.polarity_scores(sent)['compound'] for sent in esg_sentences]) if esg_sentences else 0.0
            
            # Named Entity Recognition (simplified)
            esg_entities = self._extract_esg_entities(text)
            
            # Semantic similarity analysis
            semantic_analysis = self._analyze_semantic_similarity(filtered_words)
            
            # Content summarization
            content_summary = self._summarize_esg_content(esg_sentences)
            
            # ESG topic identification
            esg_topics = self._identify_esg_topics(text)
            
            # Commitment strength analysis
            commitment_strength = self._analyze_commitment_strength(text)
            
            # Forward-looking statements
            forward_statements = self._extract_forward_looking_statements(sentences)
            
            # Credibility indicators
            credibility = self._analyze_credibility_indicators(text)
            
            return {
                "sentiment_analysis": {
                    "overall_sentiment": sentiment_scores,
                    "esg_specific_sentiment": float(esg_sentiment),
                    "positive_indicators": sentiment_scores['pos'],
                    "negative_indicators": sentiment_scores['neg'],
                    "neutral_indicators": sentiment_scores['neu']
                },
                "named_entities": esg_entities,
                "semantic_similarity": semantic_analysis,
                "content_summary": content_summary,
                "esg_topics_identified": esg_topics,
                "commitment_strength": float(commitment_strength),
                "forward_looking_statements": forward_statements,
                "credibility_indicators": credibility
            }
            
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return {}
    
    def _contains_esg_keywords(self, text: str) -> bool:
        """Check if text contains ESG-related keywords"""
        esg_keywords = [
            'sustainability', 'environmental', 'social', 'governance', 'esg',
            'carbon', 'climate', 'renewable', 'green', 'responsible', 'ethical'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in esg_keywords)
    
    def _extract_esg_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract ESG-related named entities"""
        entities = []
        
        # Environmental entities
        env_patterns = [
            r'\b(\d+(?:\.\d+)?)\s*(?:tons?|tonnes?)\s*(?:of\s*)?(?:co2|carbon|emissions?)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:mwh|kwh|gwh)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:reduction|renewable|clean)\b'
        ]
        
        for pattern in env_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "type": "environmental_metric",
                    "value": match.group(1),
                    "context": match.group(0),
                    "position": match.span()
                })
        
        # Social entities
        social_keywords = ['diversity', 'inclusion', 'safety', 'community', 'employee', 'human rights']
        for keyword in social_keywords:
            pattern = rf'\b{keyword}\b'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "type": "social_topic",
                    "value": keyword,
                    "context": match.group(0),
                    "position": match.span()
                })
        
        return entities[:20]  # Limit to top 20 entities
    
    def _analyze_semantic_similarity(self, words: List[str]) -> Dict[str, Any]:
        """Analyze semantic similarity with ESG concepts"""
        esg_concept_words = {
            'environmental': ['green', 'clean', 'renewable', 'sustainable', 'carbon', 'climate', 'energy'],
            'social': ['community', 'diversity', 'inclusion', 'safety', 'employee', 'stakeholder'],
            'governance': ['ethics', 'compliance', 'transparency', 'accountability', 'board', 'audit']
        }
        
        similarity_scores = {}
        word_counter = Counter(words)
        
        for concept, concept_words in esg_concept_words.items():
            overlap = sum(word_counter[word] for word in concept_words if word in word_counter)
            similarity_scores[concept] = overlap / max(len(concept_words), 1)
        
        return {
            "concept_similarities": similarity_scores,
            "dominant_concept": max(similarity_scores, key=similarity_scores.get) if similarity_scores else None,
            "overall_esg_alignment": sum(similarity_scores.values()) / len(similarity_scores) if similarity_scores else 0.0
        }
    
    def _summarize_esg_content(self, esg_sentences: List[str]) -> Dict[str, Any]:
        """Summarize ESG-related content"""
        if not esg_sentences:
            return {"summary": "", "key_points": [], "sentence_count": 0}
        
        # Simple extractive summarization
        key_sentences = esg_sentences[:3]  # Top 3 sentences
        summary = " ".join(key_sentences)
        
        # Extract key points
        key_points = []
        for sentence in esg_sentences:
            if any(word in sentence.lower() for word in ['target', 'goal', 'commit', 'reduce', 'increase']):
                key_points.append(sentence.strip())
        
        return {
            "summary": summary[:500],  # Limit summary length
            "key_points": key_points[:5],  # Top 5 key points
            "sentence_count": len(esg_sentences)
        }
    
    def _identify_esg_topics(self, text: str) -> List[Dict[str, Any]]:
        """Identify specific ESG topics mentioned in the text"""
        topics = {
            'Climate Change': ['climate', 'global warming', 'greenhouse gas', 'carbon footprint'],
            'Renewable Energy': ['renewable', 'solar', 'wind', 'clean energy', 'green energy'],
            'Waste Management': ['waste', 'recycling', 'circular economy', 'zero waste'],
            'Water Conservation': ['water', 'conservation', 'sustainable water'],
            'Diversity & Inclusion': ['diversity', 'inclusion', 'equal opportunity', 'gender equality'],
            'Employee Safety': ['safety', 'workplace safety', 'occupational health'],
            'Corporate Governance': ['governance', 'board', 'ethics', 'compliance', 'transparency'],
            'Supply Chain': ['supply chain', 'supplier', 'responsible sourcing']
        }
        
        identified_topics = []
        text_lower = text.lower()
        
        for topic, keywords in topics.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                identified_topics.append({
                    "topic": topic,
                    "keyword_matches": matches,
                    "relevance_score": matches / len(keywords)
                })
        
        # Sort by relevance
        identified_topics.sort(key=lambda x: x['relevance_score'], reverse=True)
        return identified_topics[:10]  # Top 10 topics
    
    def _analyze_commitment_strength(self, text: str) -> float:
        """Analyze the strength of ESG commitments in the text"""
        strong_commitment_words = ['commit', 'pledge', 'promise', 'guarantee', 'ensure', 'will achieve']
        moderate_commitment_words = ['aim', 'target', 'goal', 'strive', 'work towards', 'plan to']
        weak_commitment_words = ['consider', 'explore', 'may', 'might', 'could', 'potentially']
        
        text_lower = text.lower()
        
        strong_count = sum(1 for word in strong_commitment_words if word in text_lower)
        moderate_count = sum(1 for word in moderate_commitment_words if word in text_lower)
        weak_count = sum(1 for word in weak_commitment_words if word in text_lower)
        
        total_commitments = strong_count + moderate_count + weak_count
        if total_commitments == 0:
            return 0.0
        
        # Weighted scoring
        commitment_score = (strong_count * 1.0 + moderate_count * 0.6 + weak_count * 0.2) / total_commitments
        return min(commitment_score, 1.0)
    
    def _extract_forward_looking_statements(self, sentences: List[str]) -> List[str]:
        """Extract forward-looking statements related to ESG"""
        forward_indicators = ['by 2030', 'by 2050', 'will', 'plan to', 'target', 'goal', 'future', 'next year']
        forward_statements = []
        
        for sentence in sentences:
            if (any(indicator in sentence.lower() for indicator in forward_indicators) and 
                self._contains_esg_keywords(sentence)):
                forward_statements.append(sentence.strip())
        
        return forward_statements[:5]  # Top 5 forward-looking statements
    
    def _analyze_credibility_indicators(self, text: str) -> Dict[str, Any]:
        """Analyze credibility indicators in ESG content"""
        credibility_indicators = {
            'third_party_verification': ['verified', 'audited', 'certified', 'accredited', 'validated'],
            'specific_metrics': ['tons', 'kwh', 'percent', '%', 'million', 'billion'],
            'timeframes': ['2030', '2050', 'annual', 'quarterly', 'monthly'],
            'standards_frameworks': ['gri', 'sasb', 'tcfd', 'ungc', 'iso 14001', 'science based targets']
        }
        
        text_lower = text.lower()
        credibility_scores = {}
        
        for category, indicators in credibility_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            credibility_scores[category] = matches / len(indicators)
        
        overall_credibility = sum(credibility_scores.values()) / len(credibility_scores)
        
        return {
            "category_scores": credibility_scores,
            "overall_credibility": overall_credibility,
            "has_verification": credibility_scores.get('third_party_verification', 0) > 0,
            "has_specific_metrics": credibility_scores.get('specific_metrics', 0) > 0
        }
    
    def _calculate_nlp_score(self, nlp_results: Dict[str, Any]) -> float:
        """Calculate additional score based on NLP analysis"""
        if not nlp_results:
            return 0.0
        
        score = 0.0
        
        # Sentiment contribution
        esg_sentiment = nlp_results.get("sentiment_analysis", {}).get("esg_specific_sentiment", 0)
        if esg_sentiment > 0.1:
            score += min(esg_sentiment * 0.5, 0.5)
        
        # Topic diversity contribution
        topics_count = len(nlp_results.get("esg_topics_identified", []))
        score += min(topics_count * 0.1, 0.8)
        
        # Commitment strength contribution
        commitment_strength = nlp_results.get("commitment_strength", 0)
        score += commitment_strength * 0.6
        
        # Credibility contribution
        credibility = nlp_results.get("credibility_indicators", {}).get("overall_credibility", 0)
        score += credibility * 0.4
        
        return min(score, 2.0)  # Cap additional NLP score at 2.0
    
    def _calculate_nlp_confidence(self, nlp_results: Dict[str, Any]) -> float:
        """Calculate additional confidence based on NLP analysis"""
        if not nlp_results:
            return 0.0
        
        confidence = 0.0
        
        # Forward-looking statements boost confidence
        forward_statements = len(nlp_results.get("forward_looking_statements", []))
        confidence += min(forward_statements * 0.05, 0.15)
        
        # Named entities boost confidence
        entities = len(nlp_results.get("named_entities", []))
        confidence += min(entities * 0.01, 0.1)
        
        # Credibility indicators boost confidence
        credibility = nlp_results.get("credibility_indicators", {})
        if credibility.get("has_verification", False):
            confidence += 0.1
        if credibility.get("has_specific_metrics", False):
            confidence += 0.05
        
        return min(confidence, 0.3)  # Cap additional NLP confidence at 0.3
    
    def _detect_navigation(self, soup: BeautifulSoup) -> bool:
        """Detect if page has navigation structure"""
        nav_indicators = [
            soup.find('nav'),
            soup.find(class_=re.compile(r'nav', re.I)),
            soup.find(id=re.compile(r'nav', re.I)),
            soup.find('ul', class_=re.compile(r'menu', re.I))
        ]
        
        return any(indicator is not None for indicator in nav_indicators)
    
    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect page language"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag['lang'][:2].lower()
        
        # Check meta tags
        meta_lang = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if meta_lang and meta_lang.get('content'):
            return meta_lang['content'][:2].lower()
        
        return 'en'  # Default to English
    
    def _determine_esg_report_presence(self, website_analysis: WebsiteAnalysis) -> bool:
        """
        Determine if the website has ESG reports based on analysis
        
        Args:
            website_analysis: Analysis results from website crawling
            
        Returns:
            bool: True if ESG reports are likely present, False otherwise
        """
        if not website_analysis.is_accessible:
            return False
        
        # Check if sustainability section was found on homepage
        if website_analysis.sustainability_section_found:
            return True
        
        # Check if ESG-specific links were found
        if website_analysis.sustainability_links_found > 0:
            return True
        
        return False
    
    def _detect_esg_url_patterns(self, base_url: str) -> List[str]:
        """Detect ESG-related URL patterns from the base website"""
        esg_patterns = [
            '/sustainability', '/esg', '/csr', '/corporate-responsibility',
            '/environmental', '/social-responsibility', '/governance',
            '/annual-report', '/impact-report', '/climate', '/carbon'
        ]
        
        found_patterns = []
        for pattern in esg_patterns:
            if pattern in base_url.lower():
                found_patterns.append(pattern)
        
        return found_patterns
    
    def _get_crawler_config_dict(self) -> Dict[str, Any]:
        """Get crawler configuration as dictionary for storage"""
        return {
            "max_depth": self.config.max_depth,
            "config_timestamp": datetime.now().isoformat()
        }
    
    def _ensure_nltk_data(self):
        """Download required NLTK data if not available"""
        try:
            import nltk
            required_data = ['vader_lexicon', 'punkt', 'stopwords', 'wordnet']
            
            for data_name in required_data:
                try:
                    nltk.data.find(f'tokenizers/{data_name}' if data_name == 'punkt' else 
                                 f'corpora/{data_name}' if data_name in ['stopwords', 'wordnet'] else 
                                 f'sentiment/{data_name}')
                except LookupError:
                    logger.info(f"Downloading NLTK data: {data_name}")
                    nltk.download(data_name, quiet=True)
                    
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}. NLP features may not work properly.")
    
    async def process_companies_batch(self, batch_size: int = 10, offset: int = 0, 
                                    force_reanalysis: bool = False, replace_existing: bool = False):
        """Process companies in batches with pagination and version awareness"""
        try:
            await self.init_database()
            
            # Get total count for progress tracking
            total_companies = await self.get_total_companies_count(force_reanalysis)
            logger.info(f"Total companies needing analysis for version {self.version}: {total_companies}")
            
            companies = await self.get_companies_to_process(
                limit=batch_size, 
                offset=offset, 
                force_reanalysis=force_reanalysis
            )
            
            if not companies:
                logger.info(f"No companies need ESG analysis for version {self.version} at offset {offset}")
                return
            
            logger.info(f"Processing batch: {len(companies)} companies (offset: {offset}, total: {total_companies})")
            
            # Create progress bar for this batch
            progress_bar = tqdm(
                companies, 
                desc=f"ESG v{self.version} Analysis",
                unit="companies",
                position=0,
                leave=True,
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
            
            for i, company in enumerate(progress_bar):
                try:
                    current_position = offset + i + 1
                    
                    # Update progress bar description with current company
                    progress_bar.set_description(f"ESG v{self.version} [{current_position}/{total_companies}] {company['name'][:30]}")
                    
                    logger.info(f"[{current_position}/{total_companies}] Processing company {company['smm_company_id']}: {company['name']} - {company['website']}")
                    
                    # Check if this version already exists (for force_reanalysis mode)
                    if force_reanalysis and self._has_version_analysis(company.get('esg_info'), self.version):
                        logger.info(f"Company {company['smm_company_id']} already has version {self.version} analysis, re-analyzing...")
                    
                    result = await self.analyze_company_website(company['website'])
                    await self.update_company_esg_info(company['smm_company_id'], result, replace_existing=replace_existing)
                    
                    # Update progress bar postfix with result
                    esg_status = "✅ ESG Found" if result.has_esg_reports else "❌ No ESG"
                    progress_bar.set_postfix_str(esg_status)
                    
                    logger.info(f"Company {company['smm_company_id']} - ESG reports found: {result.has_esg_reports}")
                    
                    # Add delay between companies
                    await asyncio.sleep(self.config.request_delay)
                    
                except Exception as e:
                    progress_bar.set_postfix_str("❌ Error")
                    logger.error(f"Failed to process company {company['smm_company_id']}: {e}")
                    continue
            
            # Close progress bar
            progress_bar.close()
            
            # Log batch completion
            processed_so_far = min(offset + batch_size, total_companies)
            logger.info(f"Batch completed. Processed {processed_so_far}/{total_companies} companies for version {self.version}")
            
        finally:
            await self.close_database()
    
    async def process_all_companies(self, batch_size: int = 10, 
                                  force_reanalysis: bool = False, replace_existing: bool = False):
        """Process ALL companies continuously until complete"""
        try:
            await self.init_database()
            
            # Get initial total count
            total_companies = await self.get_total_companies_count(force_reanalysis)
            logger.info(f"Starting continuous processing of {total_companies} companies for version {self.version}")
            
            if total_companies == 0:
                logger.info(f"No companies need analysis for version {self.version}")
                return
            
            # Create overall progress bar
            overall_progress = tqdm(
                total=total_companies,
                desc=f"ESG v{self.version} Complete Analysis",
                unit="companies",
                position=1,
                leave=True,
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )
            
            processed_count = 0
            current_offset = 0
            
            while processed_count < total_companies:
                # Get companies for this batch
                companies = await self.get_companies_to_process(
                    limit=batch_size, 
                    offset=current_offset, 
                    force_reanalysis=force_reanalysis
                )
                
                if not companies:
                    logger.info(f"No more companies to process at offset {current_offset}")
                    break
                
                logger.info(f"Processing batch: {len(companies)} companies (offset: {current_offset}, remaining: {total_companies - processed_count})")
                
                # Process this batch
                batch_progress = tqdm(
                    companies, 
                    desc=f"Batch {current_offset//batch_size + 1}",
                    unit="companies",
                    position=0,
                    leave=False,
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                )
                
                for i, company in enumerate(batch_progress):
                    try:
                        current_position = processed_count + i + 1
                        
                        # Update progress bars
                        batch_progress.set_description(f"Batch {current_offset//batch_size + 1} - {company['name'][:25]}")
                        overall_progress.set_description(f"ESG v{self.version} [{current_position}/{total_companies}] {company['name'][:30]}")
                        
                        logger.info(f"[{current_position}/{total_companies}] Processing company {company['smm_company_id']}: {company['name']} - {company['website']}")
                        
                        # Check if this version already exists (for force_reanalysis mode)
                        if force_reanalysis and self._has_version_analysis(company.get('esg_info'), self.version):
                            logger.info(f"Company {company['smm_company_id']} already has version {self.version} analysis, re-analyzing...")
                        
                        result = await self.analyze_company_website(company['website'])
                        await self.update_company_esg_info(company['smm_company_id'], result, replace_existing=replace_existing)
                        
                        # Update progress bars with result
                        esg_status = "✅ ESG Found" if result.has_esg_reports else "❌ No ESG"
                        batch_progress.set_postfix_str(esg_status)
                        overall_progress.set_postfix_str(esg_status)
                        overall_progress.update(1)
                        
                        logger.info(f"Company {company['smm_company_id']} - ESG reports found: {result.has_esg_reports}")
                        
                        # Add delay between companies
                        await asyncio.sleep(self.config.request_delay)
                        
                    except Exception as e:
                        batch_progress.set_postfix_str("❌ Error")
                        overall_progress.set_postfix_str("❌ Error")
                        overall_progress.update(1)
                        logger.error(f"Failed to process company {company['smm_company_id']}: {e}")
                        continue
                
                # Close batch progress bar
                batch_progress.close()
                
                # Update counters
                processed_count += len(companies)
                current_offset += batch_size
                
                # Log batch completion
                logger.info(f"Batch completed. Processed {processed_count}/{total_companies} companies for version {self.version}")
                
                # Check if we need to continue
                remaining_companies = await self.get_total_companies_count(force_reanalysis)
                if remaining_companies == 0:
                    logger.info(f"All companies have been analyzed for version {self.version}")
                    break
            
            # Close overall progress bar
            overall_progress.close()
            
            logger.info(f"🎉 Complete! Processed {processed_count} companies for version {self.version}")
            
        finally:
            await self.close_database()
    
    def _has_version_analysis(self, esg_info: Any, version: str) -> bool:
        """Check if a company already has analysis for the specified version"""
        if not esg_info:
            return False
        
        try:
            if isinstance(esg_info, str):
                esg_data = json.loads(esg_info)
            else:
                esg_data = esg_info
            
            if isinstance(esg_data, list):
                return any(analysis.get('crawler_version') == version for analysis in esg_data)
            elif isinstance(esg_data, dict):
                return esg_data.get('crawler_version') == version
        except (json.JSONDecodeError, TypeError):
            pass
        
        return False
    
    async def show_analysis_statistics(self, force_reanalysis: bool = False):
        """Show statistics about companies needing ESG analysis"""
        try:
            await self.init_database()
            
            # Get total companies with websites
            total_with_websites = await self.get_total_companies_count(force_reanalysis=True)
            
            # Get companies needing analysis for this version
            need_analysis = await self.get_total_companies_count(force_reanalysis=force_reanalysis)
            
            # Get version-specific statistics
            version_stats = await self.get_version_analysis_statistics()
            
            print(f"\n=== ESG Analysis Statistics for Version {self.version} ===")
            print(f"Total companies with websites: {total_with_websites}")
            print(f"Companies needing analysis: {need_analysis}")
            print(f"Companies already analyzed: {total_with_websites - need_analysis}")
            
            if need_analysis > 0:
                print(f"\nAnalysis Progress: {((total_with_websites - need_analysis) / total_with_websites * 100):.1f}% complete")
                
                # Calculate batches needed
                batch_examples = [10, 25, 50, 100]
                print(f"\nBatches needed for remaining {need_analysis} companies:")
                for batch_size in batch_examples:
                    batches = (need_analysis + batch_size - 1) // batch_size  # Ceiling division
                    print(f"  Batch size {batch_size}: {batches} batches")
            
            print(f"\nVersion Analysis Summary:")
            for version, count in version_stats.items():
                print(f"  Version {version}: {count} companies")
            
            if force_reanalysis:
                print(f"\n⚠️  Force reanalysis mode: Will re-analyze ALL {total_with_websites} companies")
            else:
                print(f"\n✅ Normal mode: Will only analyze companies without Version {self.version}")
            
            print(f"\nExample commands:")
            print(f"# Process first batch of 10 companies")
            print(f"python esg_crawler.py --version {self.version} --batch-size 10 --offset 0")
            print(f"# Process second batch")
            print(f"python esg_crawler.py --version {self.version} --batch-size 10 --offset 10")
            print(f"# Force re-analysis of all companies")
            print(f"python esg_crawler.py --version {self.version} --force-reanalysis --batch-size 5")
            
        finally:
            await self.close_database()
    
    async def get_version_analysis_statistics(self) -> Dict[str, int]:
        """Get statistics of how many companies have been analyzed by each version"""
        query = """
        SELECT 
            elem->>'crawler_version' as version,
            COUNT(DISTINCT smm_company_id) as company_count
        FROM smm_companies,
        LATERAL jsonb_array_elements(
            CASE 
                WHEN jsonb_typeof(esg_info) = 'array' THEN esg_info
                WHEN esg_info IS NOT NULL THEN jsonb_build_array(esg_info)
                ELSE '[]'::jsonb
            END
        ) AS elem
        WHERE primary_domain IS NOT NULL 
        AND primary_domain != ''
        AND elem->>'crawler_version' IS NOT NULL
        GROUP BY elem->>'crawler_version'
        ORDER BY elem->>'crawler_version'
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return {row['version']: row['company_count'] for row in rows}
    
    async def process_single_company(self, company_id: int, website: str):
        """Process a single company by ID and website"""
        try:
            await self.init_database()
            
            logger.info(f"Processing single company {company_id}: {website}")
            
            result = await self.analyze_company_website(website)
            await self.update_company_esg_info(company_id, result)
            
            logger.info(f"Company {company_id} - ESG reports found: {result.has_esg_reports}")
            print(f"Analysis result: {result.to_json()}")
            
        finally:
            await self.close_database()

def main():
    """Main entry point for the standalone ESG crawler"""
    parser = argparse.ArgumentParser(description='ESG Report Crawler for Company Websites')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of companies to process in batch')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    parser.add_argument('--timeout', type=int, default=15, help='Request timeout in seconds')
    parser.add_argument('--company-id', type=int, help='Process single company by ID')
    parser.add_argument('--website', type=str, help='Website URL for single company processing')
    parser.add_argument('--user-agent', type=str, default='ESGReportBot/1.0', help='User agent string')
    parser.add_argument('--version', type=str, default='1.0', choices=['1.0', '2.0', '3.0', '4.0'], help='Crawler version (1.0=basic, 2.0=enhanced scoring, 3.0=document discovery + quantitative analysis, 4.0=advanced NLP processing)')
    parser.add_argument('--offset', type=int, default=0, help='Starting offset for batch processing (for pagination)')
    parser.add_argument('--force-reanalysis', action='store_true', help='Force re-analysis of companies that already have this version analysis')
    parser.add_argument('--replace-existing', action='store_true', help='Replace existing ESG analysis instead of appending (overwrites all previous analysis)')
    parser.add_argument('--process-all', action='store_true', help='Process ALL companies continuously until complete (overrides offset)')
    parser.add_argument('--show-stats', action='store_true', help='Show statistics about companies needing analysis')
    
    args = parser.parse_args()
    
    # Validate single company arguments
    if args.company_id and not args.website:
        parser.error('--website is required when using --company-id')
    if args.website and not args.company_id:
        parser.error('--company-id is required when using --website')
    
    # Create crawler configuration
    config = CrawlerConfig(
        request_delay=args.delay,
        timeout=args.timeout,
        user_agent=args.user_agent
    )
    
    crawler = ESGReportCrawler(config, version=args.version)
    
    try:
        if args.show_stats:
            # Show statistics only
            asyncio.run(crawler.show_analysis_statistics(args.force_reanalysis))
        elif args.company_id and args.website:
            # Process single company
            asyncio.run(crawler.process_single_company(args.company_id, args.website))
        else:
            if args.process_all:
                # Process ALL companies continuously
                asyncio.run(crawler.process_all_companies(
                    batch_size=args.batch_size,
                    force_reanalysis=args.force_reanalysis,
                    replace_existing=args.replace_existing
                ))
            else:
                # Process single batch with pagination
                asyncio.run(crawler.process_companies_batch(
                    batch_size=args.batch_size,
                    offset=args.offset,
                    force_reanalysis=args.force_reanalysis,
                    replace_existing=args.replace_existing
                ))
            
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
