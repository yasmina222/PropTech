"""
School Research Assistant - Intelligence Service

WHAT THIS FILE DOES:
- Orchestrates the entire flow: load data → generate insights → cache
- This is the "brain" that coordinates everything
- Calls the LangChain conversation chain
- Handles caching to avoid redundant LLM calls
"""

import logging
import json
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Set up logging FIRST - before any imports that might use it
logger = logging.getLogger(__name__)

# Add the project root to Python path (fixes Streamlit Cloud imports)
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models_v2 import School, ConversationStarter, ConversationStarterResponse
from data_loader import DataLoader, get_data_loader
from chains.conversation_chain import ConversationChain
from config_v2 import ENABLE_CACHE, CACHE_TTL_HOURS, CACHE_DIR, FEATURES

# Import Ofsted chain (optional - may fail if dependencies missing)
try:
    from chains.ofsted_chain import OfstedChain, get_ofsted_chain
    OFSTED_AVAILABLE = True
except ImportError as e:
    OFSTED_AVAILABLE = False
    logger.warning(f"Ofsted chain not available: {e}")


class SimpleCache:
    """
    Simple file-based cache for conversation starters.
    
    WHY WE CACHE:
    - LLM calls cost money (and take time)
    - If we already generated starters for a school, reuse them
    - Cache expires after CACHE_TTL_HOURS (default 24)
    
    FUTURE: Replace with LangChain's built-in caching for production
    """
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.enabled = ENABLE_CACHE
        
    def _get_cache_key(self, school_urn: str) -> str:
        """Generate cache key from school URN"""
        return hashlib.md5(f"starters_{school_urn}".encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
    
    def get(self, school_urn: str) -> Optional[List[dict]]:
        """Get cached conversation starters if valid"""
        if not self.enabled:
            return None
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(data['cached_at'])
            if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.info(f" Cache expired for {school_urn}")
                return None
            
            logger.info(f"📦 Cache HIT for {school_urn}")
            return data['starters']
            
        except Exception as e:
            logger.warning(f"⚠️ Cache read error: {e}")
            return None
    
    def set(self, school_urn: str, starters: List[ConversationStarter]) -> bool:
        """Save conversation starters to cache"""
        if not self.enabled:
            return False
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                'school_urn': school_urn,
                'cached_at': datetime.now().isoformat(),
                'starters': [s.model_dump() for s in starters]
            }
            
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f" Cached {len(starters)} starters for {school_urn}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Cache write error: {e}")
            return False
    
    def clear(self, school_urn: str = None) -> int:
        """Clear cache for one school or all schools"""
        count = 0
        
        if school_urn:
            key = self._get_cache_key(school_urn)
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                count = 1
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        
        logger.info(f" Cleared {count} cache entries")
        return count


class SchoolIntelligenceService:
    """
    Main service that orchestrates everything.
    
    This is what the Streamlit app talks to.
    """
    
    def __init__(self):
        """Initialize all components"""
        self.data_loader = get_data_loader()
        self.conversation_chain = None  # Lazy load to avoid API calls at startup
        self.ofsted_chain = None  # Lazy load Ofsted analyzer
        self.cache = SimpleCache()
        
        logger.info("✅ SchoolIntelligenceService initialized")
    
    def _get_chain(self) -> ConversationChain:
        """Lazy-load the conversation chain (avoids API calls at startup)"""
        if self.conversation_chain is None:
            self.conversation_chain = ConversationChain()
        return self.conversation_chain
    
    def _get_ofsted_chain(self) -> Optional['OfstedChain']:
        """Lazy-load the Ofsted chain"""
        if not OFSTED_AVAILABLE:
            return None
        if self.ofsted_chain is None:
            self.ofsted_chain = get_ofsted_chain()
        return self.ofsted_chain
    
    
    # DATA ACCESS METHODS
    
    
    def get_all_schools(self) -> List[School]:
        """Get all schools from the data source"""
        return self.data_loader.get_all_schools()
    
    def get_school_names(self) -> List[str]:
        """Get school names for dropdown"""
        return self.data_loader.get_school_names()
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        """Get a school by name (without generating starters)"""
        return self.data_loader.get_school_by_name(name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data statistics"""
        return self.data_loader.get_statistics()
    
    
    # INTELLIGENCE METHODS (with LLM calls)
    
    
    def get_school_intelligence(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Get a school WITH conversation starters generated.
        
        This is the main method for the UI:
        1. Gets school data from cache/CSV
        2. Generates conversation starters using LLM
        3. Caches the results
        
        Args:
            school_name: Name of the school
            force_refresh: If True, regenerate starters even if cached
            num_starters: How many starters to generate
            
        Returns:
            School object with conversation_starters populated
        """
        # Get the school
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            logger.warning(f"⚠️ School not found: {school_name}")
            return None
        
        # Check if conversation starters are enabled
        if not FEATURES.get("conversation_starters", True):
            logger.info("ℹ️ Conversation starters disabled in config")
            return school
        
        # Check cache first
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        # Generate new starters using LLM
        try:
            chain = self._get_chain()
            response = chain.generate(school, num_starters)
            
            # Add starters to school
            school.conversation_starters = response.conversation_starters
            
            # Cache the results
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Error generating intelligence: {e}")
            # Return school without starters on error
            return school
    
    async def get_school_intelligence_async(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Async version of get_school_intelligence.
        
        Use this when processing multiple schools in parallel.
        """
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            return None
        
        if not FEATURES.get("conversation_starters", True):
            return school
        
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        try:
            chain = self._get_chain()
            response = await chain.agenerate(school, num_starters)
            
            school.conversation_starters = response.conversation_starters
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Async error: {e}")
            return school
    
    def get_school_intelligence_with_ofsted(
        self,
        school_name: str,
        force_refresh: bool = False,
        num_starters: int = 5,
        include_ofsted: bool = True
    ) -> Optional[School]:
        """
        Get school intelligence WITH Ofsted analysis.
        
        This method:
        1. Gets school data from CSV
        2. Analyzes Ofsted report (downloads PDF, extracts improvements)
        3. Generates conversation starters using BOTH financial + Ofsted data
        
        Args:
            school_name: Name of the school
            force_refresh: If True, bypass cache
            num_starters: Number of conversation starters
            include_ofsted: If True, fetch and analyze Ofsted report
            
        Returns:
            School object with conversation_starters including Ofsted insights
        """
        # Get the school
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            logger.warning(f"⚠️ School not found: {school_name}")
            return None
        
        # Check cache first
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                logger.info(f"📦 Using cached starters for {school_name}")
                return school
        
        all_starters = []
        ofsted_data = None
        
        # Step 1: Ofsted analysis (if enabled and available)
        if include_ofsted and OFSTED_AVAILABLE and FEATURES.get("ofsted_analysis", True):
            try:
                logger.info(f"🔍 Fetching Ofsted data for {school_name}...")
                ofsted_chain = self._get_ofsted_chain()
                
                if ofsted_chain:
                    ofsted_result = ofsted_chain.analyze(school_name, school.urn)
                    
                    if ofsted_result and not ofsted_result.get("error"):
                        # Update school with Ofsted data
                        from models_v2 import OfstedData
                        school.ofsted = OfstedData(
                            rating=ofsted_result.get("rating"),
                            inspection_date=ofsted_result.get("inspection_date"),
                            report_url=ofsted_result.get("report_url"),
                            areas_for_improvement=[
                                imp.get("description", "") 
                                for imp in ofsted_result.get("improvements", [])[:5]
                            ]
                        )
                        
                        # Add Ofsted conversation starters (WITH SOURCE URLs!)
                        ofsted_starters = ofsted_result.get("conversation_starters", [])
                        all_starters.extend(ofsted_starters)
                        
                        logger.info(f"✅ Got {len(ofsted_starters)} Ofsted-based starters")
                    else:
                        logger.warning(f"⚠️ Ofsted analysis returned error: {ofsted_result.get('error')}")
                        
            except Exception as e:
                logger.error(f"❌ Ofsted analysis failed: {e}")
                # Continue without Ofsted data
        
        # Step 2: Generate financial-based conversation starters
        if FEATURES.get("conversation_starters", True):
            try:
                chain = self._get_chain()
                
                # Reduce number if we already have Ofsted starters
                remaining = max(1, num_starters - len(all_starters))
                
                response = chain.generate(school, remaining)
                all_starters.extend(response.conversation_starters)
                
            except Exception as e:
                logger.error(f"❌ Error generating starters: {e}")
        
        # Combine and deduplicate starters
        # Prioritize Ofsted starters (they have source URLs!)
        seen_topics = set()
        unique_starters = []
        
        for starter in all_starters:
            if starter.topic not in seen_topics:
                seen_topics.add(starter.topic)
                unique_starters.append(starter)
        
        # Limit to requested number
        school.conversation_starters = unique_starters[:num_starters]
        
        # Cache the results
        self.cache.set(school.urn, school.conversation_starters)
        
        logger.info(f"✅ Generated {len(school.conversation_starters)} total starters for {school_name}")
        return school

    def get_school_intelligence_with_send(
        self, 
        school_name: str, 
        force_refresh: bool = False, 
        num_starters: int = 3
    ) -> Optional[School]:
        """
        Generate SEND-focused conversation starters for a school.
        Uses the SEND data to create targeted conversation openers for the SEND team.
        """
        school = self.get_school_by_name(school_name)
        if not school:
            return None
        
        if not school.send or not school.send.has_send_data():
            return school
        
        send = school.send
        
        send_percentage = send.get_send_percentage()
        send_percentage_str = f"{send_percentage:.1f}%" if send_percentage else 'N/A'
        
        send_context = f"""
SEND DATA FOR {school.school_name}:
- Total SEND Pupils: {send.get_total_send()}
- EHC Plans: {send.ehc_plan or 0} (legally binding - school MUST provide support)
- SEN Support: {send.sen_support or 0}
- SEND as % of school: {send_percentage_str}
- Has SEN Unit: {'Yes - DEDICATED SEND INFRASTRUCTURE' if send.has_sen_unit else 'No'}
- Has Resourced Provision: {'Yes - SPECIALIST PROVISION' if send.has_resourced_provision else 'No'}

EHC PLAN BREAKDOWN BY NEED:
- Autism (ASD): {send.ehc_asd or 0}
- SEMH (Social/Emotional/Mental Health): {send.ehc_semh or 0}
- Speech & Language (SLCN): {send.ehc_slcn or 0}
- Severe Learning Difficulty: {send.ehc_sld or 0}
- Moderate Learning Difficulty: {send.ehc_mld or 0}
- Physical Disability: {send.ehc_pd or 0}

SEND PRIORITY SCORE: {send.get_send_priority_score()}
SEND PRIORITY LEVEL: {send.get_send_priority_level()}
"""
        
        if school.headteacher:
            send_context += f"\nHEADTEACHER: {school.headteacher.full_name}"
        
        prompt = f"""You are a sales coach for Protocol Education's SEND team. They place:
- Specialist Teaching Assistants (autism-trained, SEMH-trained, SLCN support)
- 1:1 support staff for pupils with EHC plans
- SENCos and SEND coordinators
- Cover for SEN units and resourced provisions

Generate {num_starters} SEND-focused conversation starters for this school.

{send_context}

KEY POINTS:
- EHC plans are LEGALLY BINDING - schools MUST provide the support specified
- Schools with SEN Units have dedicated SEND infrastructure = ongoing demand
- ASD and SEMH are hardest to recruit for
- Reference SPECIFIC numbers from the data

Return JSON with this structure:
{{
    "conversation_starters": [
        {{
            "topic": "Brief topic (3-5 words)",
            "detail": "The full conversation starter (2-4 sentences)",
            "source": "SEND Data",
            "relevance_score": 0.9
        }}
    ],
    "sales_priority": "HIGH, MEDIUM, or LOW"
}}
"""
        
        try:
            response = self._call_llm(prompt)
            
            result = json.loads(response)
            
            for starter_data in result.get("conversation_starters", []):
                starter = ConversationStarter(
                    topic=starter_data.get("topic", "SEND Opportunity"),
                    detail=starter_data.get("detail", ""),
                    source="SEND Data",
                    relevance_score=starter_data.get("relevance_score", 0.9)
                )
                school.conversation_starters.append(starter)
            
            return school
            
        except Exception as e:
            logger.error(f"Error generating SEND starters: {e}")
            return school

    def get_high_priority_schools(self, limit: int = 10) -> List[School]:
        """
        Get top priority schools for calling.
        
        Returns schools sorted by sales priority.
        """
        schools = self.data_loader.get_all_schools()
        
        # Sort by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
        sorted_schools = sorted(
            schools, 
            key=lambda s: priority_order.get(s.get_sales_priority(), 3)
        )
        
        return sorted_schools[:limit]
    
    def get_schools_with_agency_spend(self) -> List[School]:
        """Get schools that spend on agency staff"""
        return self.data_loader.get_schools_with_agency_spend()
    
    
    # CACHE MANAGEMENT
    
    
    def clear_cache(self, school_name: str = None) -> int:
        """Clear cache for one school or all schools"""
        if school_name:
            school = self.data_loader.get_school_by_name(school_name)
            if school:
                return self.cache.clear(school.urn)
            return 0
        return self.cache.clear()
    
    def refresh_data(self) -> List[School]:
        """Force reload data from source"""
        return self.data_loader.refresh()


# SINGLETON INSTANCE


_service_instance: Optional[SchoolIntelligenceService] = None

def get_intelligence_service() -> SchoolIntelligenceService:
    """
    Get the global service instance.
    
    Usage:
        from school_intelligence_service import get_intelligence_service
        service = get_intelligence_service()
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SchoolIntelligenceService()
    return _service_instance


# TESTING

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the service
    service = SchoolIntelligenceService()
    
    # Get all school names
    names = service.get_school_names()
    print(f"\n📚 Available schools ({len(names)}):")
    for name in names[:5]:
        print(f"   • {name}")
    
    # Get statistics
    stats = service.get_statistics()
    print(f"\n Statistics:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Get high priority schools
    high_priority = service.get_high_priority_schools(limit=3)
    print(f"\n High priority schools:")
    for school in high_priority:
        print(f"   • {school.school_name} ({school.get_sales_priority()})")
    
    # Test intelligence generation (this makes an LLM call!)
    print("\n Testing conversation starter generation...")
    print("   (This will make an API call to Claude/GPT)")
    
    # Uncomment to test:
    # school = service.get_school_intelligence("Thomas Coram Centre")
    # if school:
    #     print(f"\n💬 Starters for {school.school_name}:")
    #     for s in school.conversation_starters:
    #         print(f"\n   Topic: {s.topic}")
    #         print(f"   {s.detail}")
