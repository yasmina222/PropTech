"""
School Research Assistant - Ofsted Analysis Chain
==================================================
Adapted from: ofsted_analyzer_v2.py
"""

import re
import logging
import requests
import json
import io
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import PyPDF2
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config_v2 import LLM_PROVIDER, get_model, get_api_keys, LLM_TEMPERATURE
from models_v2 import ConversationStarter, OfstedData

logger = logging.getLogger(__name__)



class SubjectImprovement(BaseModel):
    """Improvement needed in a specific subject"""
    issues: List[str] = Field(default_factory=list, description="List of specific issues")
    year_groups_affected: List[str] = Field(default_factory=list, description="Year groups affected")
    urgency: str = Field(default="MEDIUM", description="HIGH, MEDIUM, or LOW")


class MainImprovement(BaseModel):
    """A main improvement area from the Ofsted report"""
    area: str = Field(description="Area name e.g. Mathematics, SEND")
    description: str = Field(description="Brief description of what needs improving")
    specifics: str = Field(default="", description="Specific details mentioned in report")


class OfstedAnalysisResult(BaseModel):
    """Complete Ofsted analysis result"""
    rating: str = Field(default="Unknown")
    inspection_date: Optional[str] = Field(default=None)
    main_improvements: List[MainImprovement] = Field(default_factory=list)
    subject_improvements: Dict[str, SubjectImprovement] = Field(default_factory=dict)
    other_key_improvements: Dict[str, List[str]] = Field(default_factory=dict)
    priority_order: List[str] = Field(default_factory=list)
    report_url: Optional[str] = Field(default=None)
    pdf_extracted: bool = Field(default=False)


class OfstedChain:
    """
    LangChain-based Ofsted analyzer.
    
    Preserves all the good stuff from ofsted_analyzer_v2.py:
    - Regex patterns for finding improvements
    - PyPDF2 for PDF extraction
    - Source URL attribution
    
    Uses LangChain for the LLM analysis step.
    """
    
    def __init__(self):
        """Initialize the Ofsted chain"""
        self.llm = self._get_llm()
        
        # PRESERVED: All broad improvement patterns from original
        self.broad_improvement_patterns = [
            # Subject-specific patterns
            r'(?:improve|develop|strengthen|raise standards in|enhance) (?:the )?(?:teaching of |provision for |outcomes in |progress in |achievement in )?(?:mathematics|maths|numeracy)',
            r'(?:improve|develop|strengthen|raise standards in|enhance) (?:the )?(?:teaching of |provision for |outcomes in |progress in |achievement in )?(?:english|literacy|reading|writing|phonics)',
            r'(?:improve|develop|strengthen|raise standards in|enhance) (?:the )?(?:teaching of |provision for |outcomes in |progress in |achievement in )?(?:science)',
            
            # Key stage and assessment patterns
            r'(?:improve|raise|increase) (?:outcomes|results|achievement|progress|attainment) (?:in|at|for) (?:key stage \d|KS\d|year \d|early years|EYFS)',
            r'(?:improve|raise) (?:SATs|GCSE|A-level|examination) results',
            r'(?:ensure|improve) (?:more|all) pupils (?:achieve|reach|attain) (?:expected|higher) standards',
            
            # SEND patterns
            r'(?:improve|develop|strengthen|enhance) (?:provision for |support for |outcomes for )?(?:SEND pupils|pupils with SEND|special educational needs)',
            r'(?:ensure|improve) (?:SEND|SEN) (?:pupils|children|students) (?:make better progress|achieve better|are better supported)',
            
            # Behaviour and attendance
            r'(?:improve|address|tackle) (?:behaviour|attendance|punctuality|persistent absence)',
            r'(?:reduce|address) (?:exclusions|fixed-term exclusions|persistent absence)',
            
            # Leadership patterns
            r'(?:strengthen|improve|develop) (?:leadership|middle leadership|subject leadership|senior leadership)',
            r'(?:develop|improve) (?:the effectiveness of |capacity in )?(?:leaders|leadership team|middle leaders)',
            
            # Teaching quality
            r'(?:improve|ensure) (?:the quality of |consistency of |effectiveness of )?teaching',
            r'(?:ensure|improve) (?:all )?teachers (?:provide|deliver|use) (?:high-quality|effective|consistent)',
            
            # Curriculum
            r'(?:improve|develop|strengthen) (?:the )?curriculum (?:in|for|planning|implementation)',
            r'(?:ensure|improve) (?:curriculum|subjects) (?:are|is) (?:well-sequenced|properly planned|effectively delivered)',
            
            # Assessment
            r'(?:improve|develop|strengthen) (?:assessment|tracking|monitoring) (?:systems|of pupil progress|procedures)',
            
            # Safeguarding
            r'(?:strengthen|improve|address) (?:safeguarding|child protection|safer recruitment)'
        ]
        
        # PRESERVED: Key subjects dictionary from original
        self.key_subjects = {
            'mathematics': ['mathematics', 'maths', 'numeracy', 'calculation', 'arithmetic'],
            'english': ['english', 'literacy', 'reading', 'writing', 'phonics', 'spelling', 'grammar'],
            'science': ['science', 'scientific', 'investigation', 'experiments'],
            'computing': ['computing', 'ICT', 'computer science', 'digital'],
            'languages': ['languages', 'MFL', 'french', 'spanish', 'foreign language'],
            'humanities': ['history', 'geography', 'RE', 'religious education'],
            'arts': ['art', 'music', 'drama', 'creative'],
            'pe': ['PE', 'physical education', 'sport', 'sports']
        }
        
        logger.info(f"✅ OfstedChain initialized with {LLM_PROVIDER}")
    
    def _get_llm(self):
        """Get the appropriate LLM based on config"""
        api_keys = get_api_keys()
        
        if LLM_PROVIDER == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=get_model("primary"),
                api_key=api_keys["anthropic"],
                temperature=LLM_TEMPERATURE,
                max_tokens=2000
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=get_model("primary"),
                api_key=api_keys["openai"],
                temperature=LLM_TEMPERATURE,
                max_tokens=2000
            )
    
    def analyze(self, school_name: str, urn: str = None) -> Dict[str, Any]:
        """
        Complete Ofsted analysis for a school.
        
        Steps:
        1. Find Ofsted report URL via web search
        2. Download and extract PDF text
        3. Use regex to find improvements
        4. Send to LLM for structured analysis
        5. Generate conversation starters with source URLs
        
        Returns dict with analysis results and conversation starters.
        """
        logger.info(f"🔍 Starting Ofsted analysis for {school_name}")
        
        result = {
            "rating": None,
            "inspection_date": None,
            "report_url": None,
            "improvements": [],
            "conversation_starters": [],
            "pdf_extracted": False,
            "error": None
        }
        
        try:
            # Step 1: Find report URL
            report_url = self._find_ofsted_report_url(school_name, urn)
            
            if not report_url:
                logger.warning(f"Could not find Ofsted report URL for {school_name}")
                result["error"] = "Could not find Ofsted report"
                return result
            
            result["report_url"] = report_url
            logger.info(f"📄 Found report: {report_url}")
            
            # Step 2: Download and extract PDF
            pdf_text = self._download_and_extract_pdf(report_url)
            
            if not pdf_text:
                logger.warning(f"Could not extract PDF text for {school_name}")
                result["error"] = "Could not extract PDF content"
                return result
            
            result["pdf_extracted"] = True
            logger.info(f"📝 Extracted {len(pdf_text)} characters from PDF")
            
            # Step 3: Extract basic info (rating, date)
            result["rating"] = self._extract_rating(pdf_text)
            result["inspection_date"] = self._extract_inspection_date(pdf_text)
            
            # Step 4: Extract improvements using regex
            broad_improvements = self._extract_broad_improvements(pdf_text)
            subject_issues = self._extract_subject_issues(pdf_text)
            
            logger.info(f"🔎 Found {len(broad_improvements)} improvements, {len(subject_issues)} subject issues")
            
            # Step 5: Use LLM to structure and analyze
            analysis = self._analyze_with_llm(
                school_name=school_name,
                pdf_text=pdf_text,
                broad_improvements=broad_improvements,
                subject_issues=subject_issues,
                rating=result["rating"],
                inspection_date=result["inspection_date"]
            )
            
            result["improvements"] = analysis.get("main_improvements", [])
            result["subject_improvements"] = analysis.get("subject_improvements", {})
            result["priority_order"] = analysis.get("priority_order", [])
            
            # Step 6: Generate conversation starters WITH SOURCE URLs
            result["conversation_starters"] = self._generate_conversation_starters(
                analysis=analysis,
                report_url=report_url,
                school_name=school_name
            )
            
            logger.info(f"✅ Ofsted analysis complete for {school_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error in Ofsted analysis: {e}")
            result["error"] = str(e)
            return result
    
    def _find_ofsted_report_url(self, school_name: str, urn: str = None) -> Optional[str]:
        """
        Find the Ofsted PDF report URL using Serper API.
        
        This is how the original ofsted_analyzer_v2.py did it - 
        using Serper to search Google for the PDF.
        """
        api_keys = get_api_keys()
        serper_key = api_keys.get("serper")
        
        if not serper_key:
            logger.warning("No Serper API key - trying direct URL construction")
            return self._try_direct_ofsted_url(school_name, urn)
        
        # Search queries to try (same as original)
        search_queries = [
            f'"{school_name}" site:files.ofsted.gov.uk filetype:pdf',
            f'{school_name} Ofsted report PDF',
            f'"{school_name}" Ofsted inspection report'
        ]
        
        for query in search_queries:
            try:
                # Call Serper API
                url = "https://google.serper.dev/search"
                headers = {
                    "X-API-KEY": serper_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "q": query,
                    "num": 5
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    organic_results = data.get("organic", [])
                    
                    for result in organic_results:
                        link = result.get("link", "")
                        
                        # Check if it's an Ofsted PDF
                        if self._is_ofsted_pdf_url(link):
                            logger.info(f"✅ Found Ofsted PDF via Serper: {link}")
                            return link
                        
                        # Check if it's an Ofsted page that might have PDF link
                        if "reports.ofsted.gov.uk" in link or "ofsted.gov.uk" in link:
                            pdf_url = self._extract_pdf_from_page(link)
                            if pdf_url:
                                logger.info(f"✅ Found Ofsted PDF from page: {pdf_url}")
                                return pdf_url
                else:
                    logger.warning(f"Serper API error: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Search error for '{query}': {e}")
                continue
        
        # Fallback: try direct URL construction
        return self._try_direct_ofsted_url(school_name, urn)
    
    def _try_direct_ofsted_url(self, school_name: str, urn: str = None) -> Optional[str]:
        """
        Try to find Ofsted report without Serper by scraping reports.ofsted.gov.uk
        """
        try:
            # Search on Ofsted's own search page
            search_url = f"https://reports.ofsted.gov.uk/search?q={requests.utils.quote(school_name)}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for links to provider pages or PDFs
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Direct PDF link
                    if 'files.ofsted.gov.uk' in href and '.pdf' in href:
                        return href
                    
                    # Provider page link - follow it to find PDF
                    if '/provider/' in href:
                        full_url = f"https://reports.ofsted.gov.uk{href}" if href.startswith('/') else href
                        pdf_url = self._extract_pdf_from_page(full_url)
                        if pdf_url:
                            return pdf_url
            
        except Exception as e:
            logger.warning(f"Direct search error: {e}")
        
        return None
    
    def _extract_pdf_from_page(self, page_url: str) -> Optional[str]:
        """Extract PDF link from an Ofsted provider page"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(page_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'files.ofsted.gov.uk' in href and '.pdf' in href.lower():
                        return href
                    if href.endswith('.pdf') and 'ofsted' in href.lower():
                        if not href.startswith('http'):
                            from urllib.parse import urljoin
                            href = urljoin(page_url, href)
                        return href
                        
        except Exception as e:
            logger.warning(f"Error extracting PDF from {page_url}: {e}")
        
        return None
    
    def _is_ofsted_pdf_url(self, url: str) -> bool:
        """Check if URL is likely an Ofsted PDF"""
        url_lower = url.lower()
        return (
            ('ofsted' in url_lower or 'files.ofsted.gov.uk' in url_lower) and
            (url_lower.endswith('.pdf') or 'file/' in url_lower)
        )
    
    def _download_and_extract_pdf(self, url: str) -> Optional[str]:
        """
        Download PDF and extract text using PyPDF2.
        
        PRESERVED from original - no API cost for extraction.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # If URL is a page (not PDF), try to find PDF link on it
            if not url.endswith('.pdf'):
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.endswith('.pdf') and 'ofsted' in href.lower():
                            if not href.startswith('http'):
                                from urllib.parse import urljoin
                                href = urljoin(url, href)
                            url = href
                            break
            
            # Download PDF
            logger.info(f"⬇️ Downloading PDF from {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract text using PyPDF2
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            full_text = '\n'.join(text_content)
            
            # Clean up whitespace
            full_text = re.sub(r'\s+', ' ', full_text)
            
            logger.info(f"📄 Extracted {len(full_text)} chars from {len(pdf_reader.pages)} pages")
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return None
    
    def _extract_rating(self, pdf_text: str) -> Optional[str]:
        """Extract Ofsted rating from PDF text"""
        ratings = ['Outstanding', 'Good', 'Requires Improvement', 'Requires improvement', 'Inadequate']
        
        # Look for "Overall effectiveness: X" pattern
        patterns = [
            r'Overall effectiveness[:\s]+(\w+)',
            r'This school is (\w+)',
            r'judged to be (\w+)',
            r'The school (?:continues to be |is )(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text, re.IGNORECASE)
            if match:
                found = match.group(1)
                for rating in ratings:
                    if found.lower() == rating.lower().split()[0]:
                        return rating
        
        # Direct search for rating words
        for rating in ratings:
            if rating.lower() in pdf_text.lower()[:2000]:
                return rating
        
        return None
    
    def _extract_inspection_date(self, pdf_text: str) -> Optional[str]:
        """Extract inspection date from PDF text"""
        # Look for date patterns
        patterns = [
            r'Inspection dates?[:\s]+(\d{1,2}(?:\s+and\s+\d{1,2})?\s+\w+\s+\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text[:1000], re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_broad_improvements(self, pdf_text: str) -> List[Dict[str, str]]:
        """
        Extract broad improvements using regex patterns.
        
        PRESERVED from original ofsted_analyzer_v2.py
        """
        improvements = []
        seen = set()
        
        for pattern in self.broad_improvement_patterns:
            matches = re.finditer(pattern, pdf_text, re.IGNORECASE)
            for match in matches:
                full_match = match.group(0)
                
                # Get context around the match
                start = max(0, match.start() - 50)
                end = min(len(pdf_text), match.end() + 100)
                context = pdf_text[start:end].strip()
                
                # Categorize the improvement
                category = self._categorize_improvement(full_match)
                
                # Avoid duplicates
                key = f"{category}:{full_match[:30]}"
                if key not in seen:
                    seen.add(key)
                    improvements.append({
                        'category': category,
                        'improvement': self._clean_text(context),
                        'original_match': full_match
                    })
        
        return improvements
    
    def _extract_subject_issues(self, pdf_text: str) -> Dict[str, List[str]]:
        """
        Extract issues by subject area.
        
        PRESERVED from original ofsted_analyzer_v2.py
        """
        subject_issues = {}
        
        for subject, keywords in self.key_subjects.items():
            issues = []
            
            for keyword in keywords:
                patterns = [
                    f'{keyword}.*?(?:weak|poor|inadequate|below|behind|not good enough)',
                    f'(?:weak|poor|inadequate|below|behind).*?{keyword}',
                    f'{keyword}.*?(?:need|needs|require|requires).*?(?:improvement|developing|attention)',
                    f'(?:improve|develop|strengthen).*?{keyword}',
                    f'{keyword}.*?(?:is|are) not.*?(?:good|effective|strong) enough'
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, pdf_text, re.IGNORECASE)
                    for match in matches:
                        context = self._get_sentence_context(pdf_text, match.start())
                        if context and len(context) > 20:
                            issues.append(context)
            
            if issues:
                # Deduplicate and limit
                unique_issues = list(set(issues))[:3]
                subject_issues[subject] = unique_issues
        
        return subject_issues
    
    def _categorize_improvement(self, text: str) -> str:
        """
        Categorize improvement into broad areas.
        
        PRESERVED from original ofsted_analyzer_v2.py
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['mathematics', 'maths', 'numeracy']):
            return 'Mathematics'
        elif any(word in text_lower for word in ['english', 'literacy', 'reading', 'writing', 'phonics']):
            return 'English/Literacy'
        elif 'science' in text_lower:
            return 'Science'
        elif any(word in text_lower for word in ['send', 'special educational']):
            return 'SEND Provision'
        elif any(word in text_lower for word in ['behaviour', 'attendance', 'exclusion']):
            return 'Behaviour/Attendance'
        elif any(word in text_lower for word in ['leadership', 'leaders', 'management']):
            return 'Leadership'
        elif any(word in text_lower for word in ['teaching', 'teachers', 'pedagogy']):
            return 'Teaching Quality'
        elif any(word in text_lower for word in ['curriculum', 'planning', 'sequencing']):
            return 'Curriculum'
        elif any(word in text_lower for word in ['assessment', 'tracking', 'progress']):
            return 'Assessment'
        elif any(word in text_lower for word in ['safeguarding', 'safety', 'protection']):
            return 'Safeguarding'
        elif any(word in text_lower for word in ['early years', 'eyfs', 'reception']):
            return 'Early Years'
        else:
            return 'General Improvement'
    
    def _get_sentence_context(self, text: str, position: int) -> str:
        """Get the complete sentence containing the position"""
        start = text.rfind('.', 0, position)
        start = 0 if start == -1 else start + 1
        
        end = text.find('.', position)
        end = len(text) if end == -1 else end + 1
        
        return text[start:end].strip()
    
    def _clean_text(self, text: str) -> str:
        """Clean and simplify text"""
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'[\n\r]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        if len(text) > 150:
            text = text[:147] + '...'
        
        return text
    
    def _get_improvement_excerpt(self, pdf_text: str) -> str:
        """Get relevant excerpt focusing on improvements"""
        sections = [
            'what does the school need to do to improve',
            'areas for improvement',
            'next steps',
            'priorities for improvement',
            'recommendations'
        ]
        
        for section in sections:
            idx = pdf_text.lower().find(section)
            if idx != -1:
                return pdf_text[idx:idx+3000]
        
        # Fallback to middle section
        mid = len(pdf_text) // 2
        return pdf_text[mid-1500:mid+1500]
    
    def _analyze_with_llm(self, school_name: str, pdf_text: str,
                          broad_improvements: List[Dict], subject_issues: Dict,
                          rating: str, inspection_date: str) -> Dict[str, Any]:
        """
        Use LangChain LLM to structure the improvements.
        
        This replaces the direct OpenAI call with LangChain.
        """
        # Prepare improvements text
        improvements_text = "\n".join([
            f"- {imp['category']}: {imp['improvement']}" 
            for imp in broad_improvements[:10]
        ])
        
        # Prepare subject issues text
        subject_text = "\n".join([
            f"{subject.upper()}: {'; '.join(issues[:2])}"
            for subject, issues in subject_issues.items()
        ])
        
        # Get key excerpt
        excerpt = self._get_improvement_excerpt(pdf_text)[:2500]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing Ofsted school inspection reports.
Extract BROAD, ACTIONABLE improvements that would require staffing solutions.

Focus on:
- Subject areas needing improvement (maths, English, science)
- Key stage or year group issues
- SEND provision problems
- Behaviour or attendance issues
- Leadership weaknesses
- Teaching quality issues

DO NOT include facility-specific issues unless they directly impact teaching.

Return valid JSON only, no markdown."""),
            ("human", """Analyze this Ofsted report for {school_name}.

Current rating: {rating}
Inspection date: {inspection_date}

IMPROVEMENTS FOUND BY PATTERN MATCHING:
{improvements_text}

SUBJECT ISSUES:
{subject_text}

REPORT EXCERPT:
{excerpt}

Return as JSON:
{{
    "main_improvements": [
        {{"area": "Subject/Area name", "description": "What needs improving", "specifics": "Specific details"}}
    ],
    "subject_improvements": {{
        "mathematics": {{"issues": ["issue1"], "year_groups_affected": ["Year 6"], "urgency": "HIGH"}},
        "english": {{"issues": ["issue1"], "year_groups_affected": ["KS2"], "urgency": "MEDIUM"}}
    }},
    "other_key_improvements": {{
        "send": ["SEND issues"],
        "behaviour": ["Behaviour issues"],
        "leadership": ["Leadership issues"],
        "teaching_quality": ["Teaching issues"]
    }},
    "priority_order": ["1. Top priority", "2. Second priority"]
}}""")
        ])
        
        try:
            chain = prompt | self.llm | JsonOutputParser()
            
            result = chain.invoke({
                "school_name": school_name,
                "rating": rating or "Unknown",
                "inspection_date": inspection_date or "Unknown",
                "improvements_text": improvements_text or "No specific improvements found",
                "subject_text": subject_text or "No subject issues found",
                "excerpt": excerpt
            })
            
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return {
                "main_improvements": [],
                "subject_improvements": {},
                "other_key_improvements": {},
                "priority_order": []
            }
    
    def _generate_conversation_starters(self, analysis: Dict, report_url: str, 
                                        school_name: str) -> List[ConversationStarter]:
        """
        Generate conversation starters WITH SOURCE URLs.
        
        PRESERVED from original - you love the source attribution!
        """
        starters = []
        
        # Main improvement conversation starter
        main_improvements = analysis.get('main_improvements', [])
        if main_improvements:
            top = main_improvements[0]
            area = top.get('area', 'Key areas')
            
            starters.append(ConversationStarter(
                topic=f"{area} Support",
                detail=(
                    f"I noticed from your recent Ofsted report that {area.lower()} was identified "
                    f"as a development area. We work with several schools facing similar challenges "
                    f"and have seen great results. For example, one partner school improved outcomes "
                    f"by 22% in just two terms with the right specialist support. Would it be helpful "
                    f"to discuss how we might support your improvement journey?"
                ),
                source=report_url,
                relevance_score=1.0
            ))
        
        # Subject-specific starters
        subject_improvements = analysis.get('subject_improvements', {})
        
        # Mathematics
        maths = subject_improvements.get('mathematics', {})
        if maths.get('urgency') == 'HIGH':
            year_groups = maths.get('year_groups_affected', ['KS2'])
            starters.append(ConversationStarter(
                topic="Mathematics Improvement",
                detail=(
                    f"Your Ofsted report highlights mathematics as a priority, particularly for "
                    f"{', '.join(year_groups)}. We've placed maths specialists who've made significant "
                    f"impacts - one helped increase pupils meeting expected standards from 61% to 78%. "
                    f"What are your main priorities for maths improvement this term?"
                ),
                source=report_url,
                relevance_score=0.95
            ))
        
        # English/Literacy
        english = subject_improvements.get('english', {})
        if english.get('urgency') in ['HIGH', 'MEDIUM']:
            starters.append(ConversationStarter(
                topic="English & Literacy Support",
                detail=(
                    f"I see from your Ofsted that English/literacy development is a focus area. "
                    f"Reading and writing outcomes are so crucial for overall progress. We have "
                    f"experienced English specialists who've helped schools significantly improve "
                    f"their phonics and reading comprehension results. Would you like to hear about "
                    f"some approaches that have worked well?"
                ),
                source=report_url,
                relevance_score=0.92
            ))
        
        # SEND
        send_issues = analysis.get('other_key_improvements', {}).get('send', [])
        if send_issues:
            starters.append(ConversationStarter(
                topic="SEND Provision Support",
                detail=(
                    f"I understand from your Ofsted report that enhancing SEND provision is a priority. "
                    f"This is such a crucial area. We work with experienced SEND practitioners who can "
                    f"help develop whole-school SEND systems. Many have experience preparing schools "
                    f"for Ofsted. What aspects of SEND provision are you looking to strengthen?"
                ),
                source=report_url,
                relevance_score=0.93
            ))
        
        # Leadership
        leadership_issues = analysis.get('other_key_improvements', {}).get('leadership', [])
        if leadership_issues:
            starters.append(ConversationStarter(
                topic="Leadership Development",
                detail=(
                    f"Your Ofsted mentions leadership development as an area for focus. Strong middle "
                    f"leadership is often key to driving improvement across a school. We can connect "
                    f"you with experienced leaders who can provide interim support or mentoring. "
                    f"What leadership capacity challenges are you currently facing?"
                ),
                source=report_url,
                relevance_score=0.88
            ))
        
        # Priority-based action plan starter
        priorities = analysis.get('priority_order', [])
        if len(priorities) >= 2:
            starters.append(ConversationStarter(
                topic="Ofsted Action Plan Support",
                detail=(
                    f"Looking at your Ofsted priorities, you have several areas to address. "
                    f"We understand how challenging it is to tackle multiple improvements while "
                    f"maintaining day-to-day excellence. We could discuss a coordinated approach, "
                    f"starting with your top priority. What timeline are you working to for "
                    f"showing progress to Ofsted?"
                ),
                source=report_url,
                relevance_score=0.90
            ))
        
        return starters



def get_ofsted_chain() -> OfstedChain:
    """Get an instance of the Ofsted chain"""
    return OfstedChain()
