"""
School Research Assistant - Streamlit App (v3)
Redesigned UI with Table View and Deep Dive Pages
UPDATED: Added Sales Intelligence Summary with contextual alerts
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sys
import io
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from school_intelligence_service import get_intelligence_service
from data_loader import get_data_loader
from models_v2 import School, ConversationStarter
from config_v2 import LLM_PROVIDER, FEATURES, get_display_label

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_SHORTLIST = 15

# =============================================================================
# PAGE CONFIG & CUSTOM CSS
# =============================================================================

st.set_page_config(
    page_title="School Research Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the new design
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global font and background */
    .stApp {
        background-color: #1a1d24;
        font-family: 'Inter', sans-serif;
    }
    
    /* Main title styling - used across all pages */
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 300;
        color: #ffffff;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }
    
    .main-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Section headers - consistent with main title */
    .section-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.5rem;
        font-weight: 400;
        color: #ffffff;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.3px;
    }
    
    .section-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: #6b7280;
        margin-bottom: 1rem;
    }
    
    /* Deep dive header - matches main title style */
    .deep-dive-header {
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 300;
        color: #ffffff;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    
    /* All h1, h2, h3 elements should use Inter */
    .stApp h1, .stApp h2, .stApp h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 300 !important;
        letter-spacing: -0.3px;
    }
    
    /* Search box styling */
    .stTextInput > div > div > input {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        padding: 0.75rem 1rem;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #6b7280;
    }
    
    /* Table header */
    .table-header {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 0.8fr 1fr;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .table-header-cell {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Table row */
    .table-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 0.8fr 1fr;
        padding: 1rem;
        align-items: center;
        border-bottom: 1px solid #2d3748;
        transition: background-color 0.2s;
    }
    
    .table-row:hover {
        background-color: #2d3748;
    }
    
    /* School name cell */
    .school-name {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 500;
        color: #ffffff;
        margin-bottom: 0.25rem;
        letter-spacing: -0.2px;
    }
    
    .school-urn {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #6b7280;
    }
    
    /* Budget cell */
    .budget-amount {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 500;
        color: #ffffff;
    }
    
    /* Local Authority cell */
    .la-name {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: #d1d5db;
    }
    
    /* Priority badges */
    .priority-badge-high {
        background-color: #dc2626;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .priority-badge-medium {
        background-color: #f59e0b;
        color: black;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .priority-badge-low {
        background-color: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* NEW badge */
    .new-badge {
        background-color: #10b981;
        color: white;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        margin-left: 0.5rem;
        display: inline-block;
    }
    
    /* Deep dive link */
    .deep-dive-link {
        color: #60a5fa;
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        text-decoration: none;
        cursor: pointer;
    }
    
    .deep-dive-link:hover {
        color: #93c5fd;
        text-decoration: underline;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1a1d24;
        border-right: 1px solid #2d3748;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #d1d5db;
    }
    
    .sidebar-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 400;
        color: #ffffff;
        margin-bottom: 1rem;
        letter-spacing: -0.2px;
    }
    
    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background-color: transparent;
    }
    
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    
    .metric-value {
        font-family: 'Inter', sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: #ffffff;
    }
    
    /* Shortlist section */
    .shortlist-section {
        background-color: #2d3748;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .shortlist-header {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        color: #ffffff;
        margin-bottom: 0.75rem;
        letter-spacing: 0.02em;
    }
    
    .shortlist-empty {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        color: #6b7280;
    }
    
    /* Deep dive page styling */
    .deep-dive-header {
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    
    .back-link {
        color: #60a5fa;
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        cursor: pointer;
        margin-bottom: 1rem;
        display: inline-block;
    }
    
    /* Info cards */
    .info-card {
        background-color: #2d3748;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .info-card-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        font-weight: 400;
        color: #ffffff;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #4a5568;
        letter-spacing: -0.2px;
    }
    
    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid #374151;
    }
    
    .info-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: #9ca3af;
    }
    
    .info-value {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: #ffffff;
        font-weight: 500;
    }
    
    /* Conversation starter cards */
    .starter-card {
        background-color: #374151;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .starter-card-ofsted {
        background-color: #374151;
        border-left: 4px solid #f97316;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .starter-card-send {
        background-color: #374151;
        border-left: 4px solid #06b6d4;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .starter-topic {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 500;
        color: #ffffff;
        margin-bottom: 0.5rem;
        letter-spacing: -0.2px;
    }
    
    .starter-detail {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: #d1d5db;
        line-height: 1.6;
    }
    
    .starter-source {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.5rem;
    }
    
    /* SEN badges */
    .sen-badge {
        background-color: #7c3aed;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
        display: inline-block;
    }
    
    /* =========================================================================
       NEW: Sales Intelligence Summary Styles
       ========================================================================= */
    
    .intel-summary-container {
        background: linear-gradient(135deg, #1e2530 0%, #2d3748 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #3d4a5c;
    }
    
    .intel-summary-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 1rem;
    }
    
    .intel-card {
        background-color: #1a1d24;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #4a5568;
    }
    
    .intel-card-hot {
        border-left-color: #ef4444;
        background-color: rgba(239, 68, 68, 0.1);
    }
    
    .intel-card-warm {
        border-left-color: #f59e0b;
        background-color: rgba(245, 158, 11, 0.1);
    }
    
    .intel-card-medium {
        border-left-color: #3b82f6;
        background-color: rgba(59, 130, 246, 0.1);
    }
    
    .intel-card-cool {
        border-left-color: #10b981;
        background-color: rgba(16, 185, 129, 0.1);
    }
    
    .intel-card-investigate {
        border-left-color: #8b5cf6;
        background-color: rgba(139, 92, 246, 0.1);
    }
    
    .intel-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .intel-card-icon {
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }
    
    .intel-card-headline {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .intel-card-amount {
        font-family: 'Inter', sans-serif;
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.25rem;
    }
    
    .intel-card-subtext {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }
    
    .intel-card-action {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: #d1d5db;
        line-height: 1.5;
        padding: 0.75rem;
        background-color: rgba(0, 0, 0, 0.2);
        border-radius: 6px;
        margin-top: 0.5rem;
    }
    
    .why-call-box {
        background: linear-gradient(135deg, #1e3a5f 0%, #1e2530 100%);
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
        border: 1px solid #3b82f6;
    }
    
    .why-call-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        color: #60a5fa;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    
    .why-call-text {
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        color: #e5e7eb;
        line-height: 1.6;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Button styling */
    .stButton > button {
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        padding: 0.5rem 1rem;
    }
    
    .stButton > button:hover {
        background-color: #2563eb;
    }
    
    /* Checkbox styling */
    .stCheckbox {
        font-family: 'Inter', sans-serif;
    }
    
    /* Selectbox styling */
    .stSelectbox {
        font-family: 'Inter', sans-serif;
    }
    
    div[data-baseweb="select"] {
        font-family: 'Inter', sans-serif;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "shortlist" not in st.session_state:
        st.session_state.shortlist = {}
    if "view" not in st.session_state:
        st.session_state.view = "list"
    if "selected_urn" not in st.session_state:
        st.session_state.selected_urn = None


# =============================================================================
# SHORTLIST FUNCTIONS
# =============================================================================

def add_to_shortlist(school: School):
    if len(st.session_state.shortlist) >= MAX_SHORTLIST:
        return False
    st.session_state.shortlist[school.urn] = {
        "school": school,
        "added_at": datetime.now()
    }
    return True


def remove_from_shortlist(urn: str):
    if urn in st.session_state.shortlist:
        del st.session_state.shortlist[urn]


def is_in_shortlist(urn: str) -> bool:
    return urn in st.session_state.shortlist


def get_shortlist_schools() -> list:
    return [item["school"] for item in st.session_state.shortlist.values()]


def export_shortlist_to_excel() -> bytes:
    """Export shortlist to Excel file"""
    schools = get_shortlist_schools()
    
    summary_data = []
    starters_data = []
    
    for school in schools:
        fin_priority = school.get_sales_priority()
        send_priority = school.get_send_priority()
        staffing_spend = ""
        agency_spend = ""
        if school.financial:
            if school.financial.total_teaching_support_costs:
                staffing_spend = f"£{school.financial.total_teaching_support_costs:,.0f}"
            if school.financial.agency_supply_costs:
                agency_spend = f"£{school.financial.agency_supply_costs:,.0f}"
        
        ehc_plans = 0
        sen_support = 0
        has_sen_unit = "No"
        has_rp = "No"
        if school.send:
            ehc_plans = school.send.ehc_plan or 0
            sen_support = school.send.sen_support or 0
            has_sen_unit = "Yes" if school.send.has_sen_unit else "No"
            has_rp = "Yes" if school.send.has_resourced_provision else "No"
        
        summary_data.append({
            "School Name": school.school_name,
            "URN": school.urn,
            "Local Authority": school.la_name or "",
            "Headteacher": school.headteacher.full_name if school.headteacher else "",
            "Phone": school.phone or "",
            "Website": school.website or "",
            "Financial Priority": fin_priority,
            "Staffing Spend": staffing_spend,
            "Agency Spend": agency_spend,
            "SEND Priority": send_priority,
            "EHC Plans": ehc_plans,
            "SEN Support": sen_support,
            "Has SEN Unit": has_sen_unit,
            "Has Resourced Provision": has_rp,
            "Why Call": school.get_why_call_summary(),
            "Gov.uk Link": f"https://schools-financial-benchmarking.service.gov.uk/school?urn={school.urn}"
        })
        
        for starter in school.conversation_starters:
            source = starter.source or "Financial/School Data"
            starters_data.append({
                "School Name": school.school_name,
                "URN": school.urn,
                "Topic": starter.topic,
                "Conversation Script": starter.detail,
                "Source": source
            })
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='School Summary', index=False)
        
        if starters_data:
            df_starters = pd.DataFrame(starters_data)
            df_starters.to_excel(writer, sheet_name='Conversation Starters', index=False)
    
    output.seek(0)
    return output.getvalue()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_fbit_url(urn: str) -> str:
    return f"https://schools-financial-benchmarking.service.gov.uk/school?urn={urn}"


def get_budget_display(school: School) -> str:
    """Get formatted budget display"""
    if school.financial and school.financial.total_teaching_support_costs:
        return f"£{school.financial.total_teaching_support_costs:,.0f}"
    return "N/A"


def get_agency_display(school: School) -> str:
    """Get formatted agency spend display"""
    if school.financial and school.financial.agency_supply_costs:
        return f"£{school.financial.agency_supply_costs:,.0f}"
    return "£0"


def get_priority_badge(priority: str) -> str:
    """Get HTML for priority badge"""
    if priority == "HIGH":
        return '<span class="priority-badge-high">HIGH</span>'
    elif priority == "MEDIUM":
        return '<span class="priority-badge-medium">MEDIUM</span>'
    else:
        return '<span class="priority-badge-low">LOW</span>'


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar(stats: dict, data_loader):
    """Render the sidebar with dashboard metrics and filters"""
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Dashboard</div>', unsafe_allow_html=True)
        
        # Metrics grid
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Schools</div>
                <div class="metric-value">{stats['total_schools']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">High Priority</div>
                <div class="metric-value">{stats['high_priority']:,}</div>
            </div>
            """, unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">With Contacts</div>
                <div class="metric-value">{stats.get('with_contacts', 0):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Local Authorities</div>
                <div class="metric-value">{stats.get('boroughs', 33)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filters
        st.markdown("**Filter by Local Authority**")
        st.caption("Select Local Authority")
        local_authorities = data_loader.get_boroughs()
        selected_la = st.selectbox(
            "Local Authority",
            options=["All Local Authorities"] + local_authorities,
            index=0,
            label_visibility="collapsed"
        )
        
        # New customers filter (placeholder)
        new_only = st.checkbox("New Customers only", value=False)
        
        st.markdown("---")
        
        # Shortlist section
        st.markdown(f"""
        <div class="shortlist-section">
            <div class="shortlist-header">MY SHORTLIST ({len(st.session_state.shortlist)}/{MAX_SHORTLIST})</div>
        """, unsafe_allow_html=True)
        
        if st.session_state.shortlist:
            for urn, item in list(st.session_state.shortlist.items()):
                school = item["school"]
                col_name, col_remove = st.columns([4, 1])
                with col_name:
                    if st.button(f"📍 {school.school_name[:25]}...", key=f"load_{urn}"):
                        st.session_state.view = "deep_dive"
                        st.session_state.selected_urn = urn
                        st.rerun()
                with col_remove:
                    if st.button("✕", key=f"remove_{urn}"):
                        remove_from_shortlist(urn)
                        st.rerun()
            
            st.markdown("---")
            excel_data = export_shortlist_to_excel()
            st.download_button(
                label="📥 Download Shortlist",
                data=excel_data,
                file_name=f"school_shortlist_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.spreadsheetml.sheet"
            )
        else:
            st.markdown("""
            <div class="shortlist-empty">
                No schools added yet.<br>
                Research schools and add them to your shortlist.
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        return selected_la, new_only


# =============================================================================
# LIST VIEW (MAIN PAGE)
# =============================================================================

def render_list_view(schools: list, search_query: str = ""):
    """Render the main list view with school table"""
    
    # Title
    st.markdown("""
    <div class="main-title">Automate your Prospecting and Research so you can Focus on Selling</div>
    <div class="main-subtitle">London Schools Dataset | Financial, Contact & SEND Intelligence</div>
    """, unsafe_allow_html=True)
    
    # Search section
    st.markdown('<div class="section-title">Search Schools</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Select a school or type to filter the list</div>', unsafe_allow_html=True)
    
    # Create two search options: dropdown select (primary) + text filter
    search_col1, search_col2 = st.columns([2, 2])
    
    with search_col1:
        # Primary: Searchable dropdown to select school directly
        school_names = ["-- Select a school --"] + sorted([s.school_name for s in schools])
        selected_school = st.selectbox(
            "Select School",
            options=school_names,
            index=0,
            label_visibility="collapsed",
            key="school_quick_select"
        )
        
        # If school selected from dropdown, go directly to deep dive
        if selected_school and selected_school != "-- Select a school --":
            selected = next((s for s in schools if s.school_name == selected_school), None)
            if selected:
                st.session_state.view = "deep_dive"
                st.session_state.selected_urn = selected.urn
                st.rerun()
    
    with search_col2:
        # Secondary: Text filter for the table below
        search_query = st.text_input(
            "Filter list",
            placeholder="Type to filter table...",
            label_visibility="collapsed",
            key=f"school_filter_{datetime.now().microsecond}"
        )
    
    # Filter schools by search
    if search_query:
        filtered_schools = [s for s in schools if search_query.lower() in s.school_name.lower()]
        st.caption(f"Showing {len(filtered_schools)} schools matching '{search_query}'")
    else:
        filtered_schools = schools
    
    # Sort by AGENCY SPEND (highest first) - this is what matters most to consultants
    filtered_schools = sorted(
        filtered_schools,
        key=lambda s: s.financial.agency_supply_costs if s.financial and s.financial.agency_supply_costs else 0,
        reverse=True
    )
    
    # Limit display
    display_schools = filtered_schools[:50]
    
    # Table header - UPDATED to show Agency Spend prominently
    st.markdown("""
    <div class="table-header">
        <div class="table-header-cell">School / MAT Name</div>
        <div class="table-header-cell">Agency Spend</div>
        <div class="table-header-cell">Local Authority</div>
        <div class="table-header-cell">Priority</div>
        <div class="table-header-cell"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Table rows
    for school in display_schools:
        agency = get_agency_display(school)
        priority = school.get_combined_priority()
        priority_badge = get_priority_badge(priority)
        la = school.la_name or "Unknown"
        
        # Create columns for the row
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 0.8, 1])
        
        with col1:
            st.markdown(f"""
            <div>
                <span class="school-name">🏫 {school.school_name}</span>
                <span class="new-badge">NEW</span>
                <div class="school-urn">URN: {school.urn}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Highlight agency spend with color coding
            if school.financial and school.financial.agency_supply_costs:
                spend = school.financial.agency_supply_costs
                if spend >= 100000:
                    st.markdown(f'<div class="budget-amount" style="color: #ef4444;">🔥 {agency}</div>', unsafe_allow_html=True)
                elif spend >= 50000:
                    st.markdown(f'<div class="budget-amount" style="color: #f59e0b;">🎯 {agency}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="budget-amount">{agency}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="budget-amount" style="color: #6b7280;">{agency}</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="la-name">{la}</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown(priority_badge, unsafe_allow_html=True)
        
        with col5:
            if st.button("View Deep Dive →", key=f"view_{school.urn}"):
                st.session_state.view = "deep_dive"
                st.session_state.selected_urn = school.urn
                st.rerun()
        
        # Add subtle divider
        st.markdown('<hr style="border: none; border-top: 1px solid #2d3748; margin: 0.5rem 0;">', unsafe_allow_html=True)
    
    # Show count
    st.caption(f"Showing {len(display_schools)} of {len(filtered_schools)} schools (sorted by Agency Spend)")


# =============================================================================
# NEW: SALES INTELLIGENCE SUMMARY COMPONENT
# =============================================================================

def render_sales_intelligence_summary(school: School):
    """
    Render the Sales Intelligence Summary - the hero section that shows
    key metrics with context and actionable insights.
    """
    
    # Get the intelligence summary from the school model
    intel = school.get_sales_intelligence_summary()
    
    st.markdown("""
    <div class="intel-summary-container">
        <div class="intel-summary-title">📊 Sales Intelligence Summary</div>
    """, unsafe_allow_html=True)
    
    # Create three columns for the main intelligence cards
    col1, col2, col3 = st.columns(3)
    
    # Column 1: Agency Spend Intelligence
    with col1:
        agency = intel.get("agency_insight")
        if agency:
            card_class = f"intel-card intel-card-{agency['alert_type']}"
            st.markdown(f"""
            <div class="{card_class}">
                <div class="intel-card-header">
                    <span class="intel-card-headline">💰 Agency Spend</span>
                    <span class="intel-card-icon">{agency['alert_icon']}</span>
                </div>
                <div class="intel-card-amount">{agency['amount']}</div>
                <div class="intel-card-subtext">{agency['per_pupil']}</div>
                <div class="intel-card-action">{agency['sales_action']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="intel-card">
                <div class="intel-card-headline">💰 Agency Spend</div>
                <div class="intel-card-amount">No Data</div>
                <div class="intel-card-subtext">Financial data not available</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Column 2: EHC Plans / SEND Opportunity
    with col2:
        ehc = intel.get("ehc_insight")
        if ehc and ehc['count'] > 0:
            card_class = f"intel-card intel-card-{ehc['alert_type']}"
            top_needs = ehc.get('top_needs', 'Not specified')
            st.markdown(f"""
            <div class="{card_class}">
                <div class="intel-card-header">
                    <span class="intel-card-headline">🎯 EHC Plans</span>
                    <span class="intel-card-icon">{ehc['alert_icon']}</span>
                </div>
                <div class="intel-card-amount">{ehc['count']} Plans</div>
                <div class="intel-card-subtext">{ehc['opportunity']}</div>
                <div class="intel-card-action">{ehc['sales_action']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            send_summary = intel.get("send_insight")
            if send_summary and send_summary['total'] > 0:
                st.markdown(f"""
                <div class="intel-card intel-card-{send_summary['alert_type']}">
                    <div class="intel-card-header">
                        <span class="intel-card-headline">🎯 SEND Pupils</span>
                        <span class="intel-card-icon">{send_summary['alert_icon']}</span>
                    </div>
                    <div class="intel-card-amount">{send_summary['total']} Pupils</div>
                    <div class="intel-card-subtext">{send_summary['percentage']} of school</div>
                    <div class="intel-card-action">{send_summary['context']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="intel-card">
                    <div class="intel-card-headline">🎯 SEND Data</div>
                    <div class="intel-card-amount">No Data</div>
                    <div class="intel-card-subtext">SEND information not available</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Column 3: SEND Infrastructure OR Total Staffing
    with col3:
        infra = intel.get("infrastructure_insight")
        if infra:
            # Show SEN Unit / Resourced Provision - this is HOT
            st.markdown(f"""
            <div class="intel-card intel-card-hot">
                <div class="intel-card-header">
                    <span class="intel-card-headline">🏫 SEND Infrastructure</span>
                    <span class="intel-card-icon">{infra['alert_icon']}</span>
                </div>
                <div class="intel-card-amount">{' + '.join(infra['provisions'])}</div>
                <div class="intel-card-subtext">Dedicated SEND facilities</div>
                <div class="intel-card-action">{infra['sales_action']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show total staffing budget instead
            staffing = intel.get("staffing_insight")
            if staffing:
                card_class = f"intel-card intel-card-{staffing['alert_type']}"
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="intel-card-header">
                        <span class="intel-card-headline">📈 Total Staffing</span>
                        <span class="intel-card-icon">{staffing['alert_icon']}</span>
                    </div>
                    <div class="intel-card-amount">{staffing['amount']}</div>
                    <div class="intel-card-subtext">{staffing['per_pupil']}</div>
                    <div class="intel-card-action">{staffing['detail']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="intel-card">
                    <div class="intel-card-headline">📈 Staffing Budget</div>
                    <div class="intel-card-amount">No Data</div>
                    <div class="intel-card-subtext">Financial data not available</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Why Call This School box
    why_call_reasons = intel.get("why_call_reasons", [])
    if why_call_reasons:
        why_call_text = school.get_why_call_summary()
        st.markdown(f"""
        <div class="why-call-box">
            <div class="why-call-title">📞 Why Call This School</div>
            <div class="why-call-text">{why_call_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# DEEP DIVE VIEW
# =============================================================================

def render_deep_dive(school: School, service):
    """Render the deep dive page for a specific school"""
    
    # Back button - must clear URL params too!
    if st.button("← Back to Search", type="primary"):
        st.session_state.view = "list"
        st.session_state.selected_urn = None
        st.query_params.clear()
        st.rerun()
    
    # School header
    st.markdown(f'<div class="main-title" style="font-size: 2rem; font-weight: 500; margin-top: 0.5rem;">{school.school_name}</div>', unsafe_allow_html=True)
    
    # Quick stats row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("URN", school.urn)
    with col2:
        st.metric("Local Authority", school.la_name or "Unknown")
    with col3:
        agency = get_agency_display(school)
        st.metric("Agency Spend", agency)
    with col4:
        priority = school.get_combined_priority()
        st.markdown(f"**Priority**<br>{get_priority_badge(priority)}", unsafe_allow_html=True)
    with col5:
        if is_in_shortlist(school.urn):
            if st.button("✓ In Shortlist", key="shortlist_toggle"):
                remove_from_shortlist(school.urn)
                st.rerun()
        else:
            if st.button("+ Add to Shortlist", key="shortlist_toggle"):
                add_to_shortlist(school)
                st.rerun()
    
    st.markdown("---")
    
    # NEW: Sales Intelligence Summary - THE HERO SECTION
    render_sales_intelligence_summary(school)
    
    st.markdown("---")
    
    # Main content in tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📞 Contact & Details",
        "💰 Financial Data",
        "🎯 SEND Opportunities",
        "💬 Conversation Starters"
    ])
    
    with tab1:
        render_contact_details(school)
    
    with tab2:
        render_financial_details(school)
    
    with tab3:
        render_send_details(school)
    
    with tab4:
        render_conversation_starters(school, service)


def render_contact_details(school: School):
    """Render contact and basic details"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">📋 School Information</div>
        """, unsafe_allow_html=True)
        
        details = [
            ("School Type", school.school_type or "N/A"),
            ("Phase", school.phase or "N/A"),
            ("Pupils", str(school.pupil_count) if school.pupil_count else "N/A"),
            ("Trust", school.trust_name or "N/A"),
        ]
        
        for label, value in details:
            st.markdown(f"""
            <div class="info-row">
                <span class="info-label">{label}</span>
                <span class="info-value">{value}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">👤 Key Contact</div>
        """, unsafe_allow_html=True)
        
        if school.headteacher:
            head = school.headteacher
            contact_details = [
                ("Name", head.full_name),
                ("Role", "Headteacher"),
                ("Phone", school.phone or "N/A"),
            ]
            
            for label, value in contact_details:
                st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">{label}</span>
                    <span class="info-value">{value}</span>
                </div>
                """, unsafe_allow_html=True)
            
            if school.website:
                website = school.website if school.website.startswith('http') else f"http://{school.website}"
                st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">Website</span>
                    <span class="info-value"><a href="{website}" target="_blank" style="color: #60a5fa;">{school.website}</a></span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<span class="info-label">No contact information available</span>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Address
    st.markdown("""
    <div class="info-card">
        <div class="info-card-title">📍 Address</div>
    """, unsafe_allow_html=True)
    
    address = school.get_full_address() or "Address not available"
    st.markdown(f'<span class="info-value">{address}</span>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # External links
    st.markdown(f"""
    <div style="margin-top: 1rem;">
        <a href="{get_fbit_url(school.urn)}" target="_blank" class="deep-dive-link">
            View on Gov.uk Financial Benchmarking Tool →
        </a>
    </div>
    """, unsafe_allow_html=True)


def render_financial_details(school: School):
    """Render financial data"""
    
    if school.financial and school.financial.has_financial_data():
        fin = school.financial
        
        # Key metrics - AGENCY SPEND FIRST
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if fin.agency_supply_costs:
                st.metric("🔥 Agency Supply Spend", f"£{fin.agency_supply_costs:,.0f}")
            else:
                st.metric("Agency Supply Spend", "£0")
        with col2:
            if fin.total_teaching_support_costs:
                st.metric("Total Staffing Costs", f"£{fin.total_teaching_support_costs:,.0f}")
        with col3:
            if fin.total_expenditure:
                st.metric("Total Expenditure", f"£{fin.total_expenditure:,.0f}")
        
        # Agency spend insight box
        agency_insight = fin.get_agency_spend_insight()
        if agency_insight['alert_type'] == 'hot':
            st.success(f"🔥 **{agency_insight['headline']}** - {agency_insight['sales_action']}")
        elif agency_insight['alert_type'] == 'warm':
            st.info(f"🎯 **{agency_insight['headline']}** - {agency_insight['sales_action']}")
        elif agency_insight['alert_type'] == 'investigate':
            st.warning(f"🔍 **{agency_insight['headline']}** - {agency_insight['sales_action']}")
        
        st.markdown("---")
        
        # Cost breakdown
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">💷 Cost Breakdown</div>
        """, unsafe_allow_html=True)
        
        costs = [
            ("Agency Supply (E26) ⭐", fin.agency_supply_costs, True),
            ("Total Staffing Costs", fin.total_teaching_support_costs, False),
            ("Teaching Staff (E01)", fin.teaching_staff_costs, False),
            ("Supply Teaching (E02)", fin.supply_teaching_costs, False),
            ("Educational Support (E03)", fin.educational_support_costs, False),
            ("Consultancy (E27)", fin.educational_consultancy_costs, False),
        ]
        
        for label, value, highlight in costs:
            if value and value > 0:
                per_pupil = ""
                if fin.total_pupils and fin.total_pupils > 0:
                    per_pupil = f" (£{value/fin.total_pupils:,.0f}/pupil)"
                style = "color: #ef4444; font-weight: 600;" if highlight else ""
                st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">{label}</span>
                    <span class="info-value" style="{style}">£{value:,.0f}{per_pupil}</span>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        st.info("No financial data available for this school")


def render_send_details(school: School):
    """Render SEND data and opportunities"""
    
    if school.send and school.send.has_send_data():
        send = school.send
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total SEND", send.get_total_send())
        with col2:
            st.metric("🔥 EHC Plans", send.ehc_plan or 0)
        with col3:
            st.metric("SEN Support", send.sen_support or 0)
        with col4:
            pct = send.get_send_percentage()
            st.metric("SEND %", f"{pct:.1f}%" if pct else "N/A")
        
        # EHC insight box
        ehc_insight = send.get_ehc_opportunity_insight()
        if ehc_insight['alert_type'] == 'hot':
            st.success(f"🔥 **{ehc_insight['headline']}** - {ehc_insight['sales_action']}")
        elif ehc_insight['alert_type'] == 'warm':
            st.info(f"⚡ **{ehc_insight['headline']}** - {ehc_insight['sales_action']}")
        elif ehc_insight['alert_type'] == 'medium':
            st.info(f"🎯 **{ehc_insight['headline']}** - {ehc_insight['sales_action']}")
        
        # Special provision badges
        if send.has_sen_unit or send.has_resourced_provision:
            st.markdown("---")
            badges_html = ""
            if send.has_sen_unit:
                badges_html += '<span class="sen-badge">🏫 SEN Unit</span>'
            if send.has_resourced_provision:
                badges_html += '<span class="sen-badge">📚 Resourced Provision</span>'
            st.markdown(f'<div style="margin: 1rem 0;">{badges_html}</div>', unsafe_allow_html=True)
            
            infra_insight = send.get_send_infrastructure_insight()
            if infra_insight:
                st.warning(f"🏫 **{infra_insight['headline']}** - {infra_insight['sales_action']}")
        
        st.markdown("---")
        
        # EHC breakdown
        st.markdown("""
        <div class="info-card">
            <div class="info-card-title">📊 EHC Plan Breakdown by Need</div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background-color: rgba(59, 130, 246, 0.1); padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem;">
            <span style="font-size: 0.85rem; color: #93c5fd;">
                💡 <strong>Remember:</strong> Each EHC Plan represents a legally-mandated support position.
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        needs = [
            ("Autism (ASD)", send.ehc_asd, "Hardest to recruit - specialist training required"),
            ("SEMH", send.ehc_semh, "High demand - behaviour management skills needed"),
            ("Speech & Language (SLCN)", send.ehc_slcn, "Specialist SLT support"),
            ("Severe Learning Difficulty", send.ehc_sld, "1:1 intensive support"),
            ("Moderate Learning Difficulty", send.ehc_mld, "General TA support"),
            ("Physical Disability", send.ehc_pd, "Accessibility support"),
            ("Hearing Impairment", send.ehc_hi, "Specialist communication support"),
            ("Visual Impairment", send.ehc_vi, "Specialist support required"),
        ]
        
        sorted_needs = sorted(needs, key=lambda x: x[1] or 0, reverse=True)
        
        for need, count, note in sorted_needs:
            if count and count > 0:
                st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">{need}</span>
                    <span class="info-value">{count} pupils <span style="color: #6b7280; font-size: 0.75rem;">({note})</span></span>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # SEND priority
        priority = send.get_send_priority_level()
        score = send.get_send_priority_score()
        st.markdown(f"**SEND Priority Score:** {score} ({priority})")
        
    else:
        st.info("No SEND data available for this school")


def render_conversation_starters(school: School, service):
    """Render conversation starters with generation buttons"""
    
    # Financial starters section
    st.markdown("### 💰 Financial Conversation Starters")
    st.caption("Based on staffing budget and expenditure data")
    
    financial_starters = [s for s in school.conversation_starters if not (s.source and s.source.startswith("http"))]
    
    if financial_starters:
        for starter in financial_starters:
            st.markdown(f"""
            <div class="starter-card">
                <div class="starter-topic">{starter.topic}</div>
                <div class="starter-detail">{starter.detail}</div>
                <div class="starter-source">Source: {starter.source or 'Financial Data'}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.code(starter.detail, language=None)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        num_fin = st.number_input("Count", min_value=1, max_value=5, value=3, key="num_fin")
    with col2:
        if st.button("🔄 Generate Financial Starters", type="primary"):
            with st.spinner("Generating from financial data..."):
                updated_school = service.get_school_intelligence(
                    school.school_name, force_refresh=True, num_starters=num_fin
                )
            if updated_school:
                if is_in_shortlist(school.urn):
                    st.session_state.shortlist[school.urn]["school"] = updated_school
                st.success("Generated!")
                st.rerun()
    
    st.markdown("---")
    
    # Ofsted starters section
    st.markdown("### 📋 Ofsted Conversation Starters")
    st.caption("Based on latest Ofsted inspection report")
    
    ofsted_starters = [s for s in school.conversation_starters if s.source and s.source.startswith("http")]
    
    if ofsted_starters:
        for starter in ofsted_starters:
            st.markdown(f"""
            <div class="starter-card-ofsted">
                <div class="starter-topic">{starter.topic}</div>
                <div class="starter-detail">{starter.detail}</div>
                <div class="starter-source">Source: <a href="{starter.source}" target="_blank" style="color: #60a5fa;">View Ofsted Report</a></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.code(starter.detail, language=None)
    
    if school.ofsted and school.ofsted.rating:
        st.info(f"**Current Rating:** {school.ofsted.rating} | **Inspected:** {school.ofsted.inspection_date or 'Unknown'}")
    
    st.warning("⏱️ Note: Fetching Ofsted report takes up to 60 seconds (PDF download & analysis)")
    
    if st.button("🔄 Fetch Ofsted & Generate Starters", type="secondary"):
        with st.spinner("Downloading and analyzing Ofsted PDF..."):
            updated_school = service.get_school_intelligence_with_ofsted(
                school.school_name, force_refresh=True, num_starters=3, include_ofsted=True
            )
        if updated_school:
            if is_in_shortlist(school.urn):
                st.session_state.shortlist[school.urn]["school"] = updated_school
            st.success("Generated from Ofsted report!")
            st.rerun()
    
    st.markdown("---")
    
    # SEND starters section
    st.markdown("### 🎯 SEND Conversation Starters")
    st.caption("Based on SEND data - auto-generated from EHC and SEN Support data")
    
    if school.send and school.send.has_send_data():
        send = school.send
        
        # Auto-generate SEND starters based on data
        if send.has_sen_unit or send.has_resourced_provision:
            unit_type = "SEN unit" if send.has_sen_unit else "resourced provision"
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-topic">Dedicated SEND Provision</div>
                <div class="starter-detail">"I noticed you have a dedicated {unit_type} - this must require specialist staffing on an ongoing basis. How are you currently managing cover and recruitment for these roles? We work with schools to provide trained SEND specialists for both permanent and cover positions."</div>
                <div class="starter-source">Source: SEND Data</div>
            </div>
            """, unsafe_allow_html=True)
        
        ehc = send.ehc_plan or 0
        if ehc >= 10:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-topic">EHC Plan Support Requirements</div>
                <div class="starter-detail">"You have {ehc} pupils with EHC plans - that's {ehc} legally-mandated support positions you need to fill. These aren't optional - I know schools can face legal challenges if this support isn't in place. How are you managing your 1:1 staffing? We have ASD-trained and SEMH-specialist TAs available who understand the requirements."</div>
                <div class="starter-source">Source: SEND Data - {ehc} EHC Plans = {ehc} legally-required positions</div>
            </div>
            """, unsafe_allow_html=True)
        elif ehc >= 5:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-topic">EHC Support Staffing</div>
                <div class="starter-detail">"With {ehc} pupils on EHC plans, you'll have specific support requirements that must be met. Are you finding it challenging to recruit staff with the right training? We specialise in placing SEND-trained TAs who can hit the ground running."</div>
                <div class="starter-source">Source: SEND Data</div>
            </div>
            """, unsafe_allow_html=True)
        
        if send.ehc_asd and send.ehc_asd >= 3:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-topic">Autism Specialist Staffing</div>
                <div class="starter-detail">"With {send.ehc_asd} pupils with autism, having the right trained support staff is crucial - and I know autism specialists are some of the hardest roles to fill. Are you finding recruitment difficult in this area? We have autism-trained TAs who understand sensory needs, communication strategies, and creating structured environments."</div>
                <div class="starter-source">Source: SEND Data - {send.ehc_asd} pupils with ASD</div>
            </div>
            """, unsafe_allow_html=True)
        
        if send.ehc_semh and send.ehc_semh >= 3:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-topic">SEMH Specialist Support</div>
                <div class="starter-detail">"I see you have {send.ehc_semh} pupils with SEMH needs - this is one of the most challenging areas to staff. These pupils need consistent support from people trained in de-escalation and therapeutic approaches. We have experienced SEMH specialists who understand trauma-informed practice and behaviour management. Would it help to discuss your current staffing situation?"</div>
                <div class="starter-source">Source: SEND Data - {send.ehc_semh} pupils with SEMH needs</div>
            </div>
            """, unsafe_allow_html=True)
        
        # General SEND opportunity if no specific triggers
        if ehc < 5 and not send.has_sen_unit and not send.has_resourced_provision:
            total_send = send.get_total_send()
            if total_send > 0:
                st.markdown(f"""
                <div class="starter-card-send">
                    <div class="starter-topic">SEND Support</div>
                    <div class="starter-detail">"You have {total_send} pupils with SEND - are you finding it easy to recruit TAs with the right experience? Many schools tell us that finding quality SEND-trained staff is their biggest challenge."</div>
                    <div class="starter-source">Source: SEND Data</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No SEND data available for this school")


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    init_session_state()
    
    # Check URL params for deep linking
    params = st.query_params
    if "urn" in params:
        st.session_state.view = "deep_dive"
        st.session_state.selected_urn = params["urn"]
    
    # Initialize services
    service = get_intelligence_service()
    data_loader = get_data_loader()
    
    # Load data
    with st.spinner("Loading schools..."):
        all_schools = service.get_all_schools()
        stats = service.get_statistics()
    
    # Render sidebar
    selected_la, new_only = render_sidebar(stats, data_loader)
    
    # Filter schools
    if selected_la and selected_la != "All Local Authorities":
        schools = data_loader.get_schools_by_borough(selected_la)
    else:
        schools = all_schools
    
    # Render main content based on view
    if st.session_state.view == "deep_dive" and st.session_state.selected_urn:
        school = data_loader.get_school_by_urn(st.session_state.selected_urn)
        if school:
            # Update URL
            st.query_params["urn"] = school.urn
            render_deep_dive(school, service)
        else:
            st.error("School not found")
            st.session_state.view = "list"
    else:
        # Clear URL params
        st.query_params.clear()
        render_list_view(schools)


if __name__ == "__main__":
    main()
