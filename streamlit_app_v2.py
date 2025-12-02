"""
School Research Assistant - Streamlit App (v2)
With SEND Opportunities Tab and Shortlist Feature
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

st.set_page_config(
    page_title="School Research Assistant",
    page_icon="🎓",
    layout="wide"
)


def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "shortlist" not in st.session_state:
        st.session_state.shortlist = {}
    if "selected_school" not in st.session_state:
        st.session_state.selected_school = None


def check_password() -> bool:
    return True

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
    schools = get_shortlist_schools()
    
    summary_data = []
    starters_data = []
    
    for school in schools:
        fin_priority = school.get_sales_priority()
        send_priority = school.get_send_priority()
        staffing_spend = ""
        if school.financial and school.financial.total_teaching_support_costs:
            staffing_spend = f"£{school.financial.total_teaching_support_costs:,.0f}"
        
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
            "SEND Priority": send_priority,
            "EHC Plans": ehc_plans,
            "SEN Support": sen_support,
            "Has SEN Unit": has_sen_unit,
            "Has Resourced Provision": has_rp,
            "Gov.uk Link": get_fbit_url(school.urn)
        })
        
        for starter in school.conversation_starters:
            source = starter.source or "Financial/School Data"
            if starter.source and starter.source.startswith("http"):
                source = starter.source
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
        else:
            df_empty = pd.DataFrame([{"Note": "No conversation starters generated yet. Generate starters for each school first."}])
            df_empty.to_excel(writer, sheet_name='Conversation Starters', index=False)
        
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 60)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output.getvalue()


st.markdown("""
<style>
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #E8E8E8 !important;
    }
    .stApp p, .stApp span, .stApp label, .stApp div {
        color: #D0D0D0 !important;
    }
    
    div[data-baseweb="select"] li[aria-selected="true"],
    div[data-baseweb="select"] li:hover {
        background-color: #28a745 !important;
    }
    
    .starter-card {
        background-color: #2D2D3A;
        border-left: 4px solid #0066ff;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .starter-card-ofsted {
        background-color: #2D2D3A;
        border-left: 4px solid #ff6600;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .starter-card-send {
        background-color: #2D2D3A;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .starter-detail {
        color: #E0E0E0 !important;
        line-height: 1.6;
    }
    .priority-high {
        background-color: #dc3545;
        color: white !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .priority-medium {
        background-color: #ffc107;
        color: black !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .priority-low {
        background-color: #28a745;
        color: white !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
    }
    .send-highlight {
        background-color: #1a3a4a;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #17a2b8;
    }
    .sen-unit-badge {
        background-color: #6f42c1;
        color: white !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 0.5rem;
    }
    .staffing-spend-high {
        background-color: #1a3d2a;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
    .contact-card {
        background-color: #2A3D4D;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .shortlist-section {
        background-color: #2D3748;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #4A5568;
        margin: 0.5rem 0;
    }
    .shortlist-header {
        color: #48BB78 !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .section-header {
        background-color: #2D3748;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 1rem 0 0.5rem 0;
        border-left: 4px solid #4A90D9;
    }
    .section-header-financial {
        border-left-color: #0066ff;
    }
    .section-header-ofsted {
        border-left-color: #ff6600;
    }
    .section-header-send {
        border-left-color: #17a2b8;
    }
</style>
""", unsafe_allow_html=True)


def get_fbit_url(urn: str) -> str:
    return f"https://schools-financial-benchmarking.service.gov.uk/school?urn={urn}"


def main():
    init_session_state()
    service = get_intelligence_service()
    data_loader = get_data_loader()
    
    st.title("Automate your Prospecting and Research so you can Focus on Selling")
    st.caption("London Schools Dataset | Financial, Contact & SEND Intelligence")
    
    with st.spinner("Loading schools..."):
        school_names = service.get_school_names()
        stats = service.get_statistics()
    
    with st.sidebar:
        st.header("Dashboard")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Schools", f"{stats['total_schools']:,}")
        with col2:
            st.metric("High Priority", stats["high_priority"])
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric("With Contacts", stats.get("with_contacts", 0))
        with col4:
            st.metric("Local Authorities", stats.get("boroughs", 33))
        
        st.divider()
        
        st.subheader("Filter by Local Authority")
        local_authorities = data_loader.get_boroughs()
        selected_la = st.selectbox(
            "Select Local Authority",
            options=["All Local Authorities"] + local_authorities,
            index=0
        )
        
        st.divider()
        
        st.markdown(f"""
        <div class="shortlist-section">
            <div class="shortlist-header">MY SHORTLIST ({len(st.session_state.shortlist)}/{MAX_SHORTLIST})</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.shortlist:
            for urn, item in list(st.session_state.shortlist.items()):
                school = item["school"]
                col_name, col_remove = st.columns([4, 1])
                with col_name:
                    if st.button(school.school_name[:30], key=f"load_{urn}", help="Click to load school"):
                        st.session_state.selected_school = school.school_name
                        st.rerun()
                with col_remove:
                    if st.button("X", key=f"remove_{urn}", help="Remove from shortlist"):
                        remove_from_shortlist(urn)
                        st.rerun()
            
            st.divider()
            
            excel_data = export_shortlist_to_excel()
            st.download_button(
                label="Download Shortlist (Excel)",
                data=excel_data,
                file_name=f"school_shortlist_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else:
            st.caption("No schools added yet. Research schools and add them to your shortlist.")
    
    st.header("Search Schools")
    
    if selected_la and selected_la != "All Local Authorities":
        filtered_names = [s.school_name for s in data_loader.get_schools_by_borough(selected_la)]
        display_names = sorted(filtered_names)
        st.info(f"Showing {len(display_names)} schools in {selected_la}")
    else:
        display_names = school_names
    
    default_index = 0
    if st.session_state.selected_school and st.session_state.selected_school in display_names:
        default_index = display_names.index(st.session_state.selected_school) + 1
    
    selected_school_name = st.selectbox(
        "Select a school",
        options=[""] + display_names,
        index=default_index,
        placeholder="Choose a school...",
        help="Select a school to view details and generate conversation starters"
    )
    
    if selected_school_name:
        st.session_state.selected_school = selected_school_name
        school = service.get_school_by_name(selected_school_name)
        if school:
            display_school(school, service)
        else:
            st.error(f"School not found: {selected_school_name}")
    else:
        st.session_state.selected_school = None
        display_home_view(data_loader)


def display_home_view(data_loader):
    tab1, tab2, tab3 = st.tabs(["Top Staffing Spenders", "Top SEND Opportunities", "Schools with SEN Units"])
    
    with tab1:
        st.subheader("Top Staffing Spenders")
        st.caption("Schools with largest staffing budgets - select from dropdown above to view details")
        
        top_spenders = data_loader.get_top_spenders(limit=15, spend_type="total")
        if top_spenders:
            table_data = []
            for school in top_spenders:
                spend = school.financial.total_teaching_support_costs or 0
                table_data.append({
                    "School": school.school_name,
                    "Staffing Spend": f"£{spend:,.0f}",
                    "Local Authority": school.la_name or "",
                    "Priority": school.get_sales_priority()
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
    
    with tab2:
        st.subheader("Top SEND Opportunities")
        st.caption("Schools with highest SEND demand - select from dropdown above to view details")
        
        top_send = data_loader.get_top_send_schools(limit=15)
        if top_send:
            table_data = []
            for school in top_send:
                ehc = school.send.ehc_plan or 0 if school.send else 0
                sen = school.send.sen_support or 0 if school.send else 0
                score = school.send.get_send_priority_score() if school.send else 0
                flags = []
                if school.send and school.send.has_sen_unit:
                    flags.append("SEN Unit")
                if school.send and school.send.has_resourced_provision:
                    flags.append("RP")
                table_data.append({
                    "School": school.school_name,
                    "EHC Plans": ehc,
                    "SEN Support": sen,
                    "Score": score,
                    "Flags": " | ".join(flags) if flags else "-"
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
    
    with tab3:
        st.subheader("Schools with SEN Units / Resourced Provisions")
        st.caption("Hottest leads - select from dropdown above to view details")
        
        sen_unit_schools = data_loader.get_schools_with_sen_unit()
        rp_schools = data_loader.get_schools_with_resourced_provision()
        all_special = list({s.urn: s for s in (sen_unit_schools + rp_schools)}.values())
        all_special.sort(key=lambda s: s.send.get_send_priority_score() if s.send else 0, reverse=True)
        
        if all_special:
            table_data = []
            for school in all_special[:20]:
                ehc = school.send.ehc_plan or 0 if school.send else 0
                flags = []
                if school.send and school.send.has_sen_unit:
                    flags.append("SEN Unit")
                if school.send and school.send.has_resourced_provision:
                    flags.append("Resourced Provision")
                table_data.append({
                    "School": school.school_name,
                    "EHC Plans": ehc,
                    "Local Authority": school.la_name or "",
                    "Provision Type": " | ".join(flags)
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No schools with SEN Units or Resourced Provisions found in current data")


def display_school(school: School, service):
    st.subheader(school.school_name)
    
    col_info, col_shortlist = st.columns([5, 1])
    with col_shortlist:
        if is_in_shortlist(school.urn):
            if st.button("Remove from Shortlist", key="remove_main"):
                remove_from_shortlist(school.urn)
                st.rerun()
        else:
            if len(st.session_state.shortlist) >= MAX_SHORTLIST:
                st.warning(f"Shortlist full ({MAX_SHORTLIST})")
            else:
                if st.button("Add to Shortlist", key="add_main", type="primary"):
                    shortlist_school = service.get_school_by_name(school.school_name)
                    if shortlist_school:
                        add_to_shortlist(shortlist_school)
                        st.success("Added!")
                        st.rerun()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("URN", school.urn)
    with col2:
        st.metric("Local Authority", school.la_name or "Unknown")
    with col3:
        st.metric("Type", school.school_type or "Unknown")
    with col4:
        st.metric("Pupils", school.pupil_count or "Unknown")
    with col5:
        priority = school.get_combined_priority()
        if priority == "HIGH":
            st.markdown('<span class="priority-high">HIGH PRIORITY</span>', unsafe_allow_html=True)
        elif priority == "MEDIUM":
            st.markdown('<span class="priority-medium">MEDIUM</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="priority-low">LOW</span>', unsafe_allow_html=True)
    
    if school.financial and school.financial.total_teaching_support_costs:
        spend = school.financial.total_teaching_support_costs
        st.markdown(f"""
        <div class="staffing-spend-high">
            <h3>Total Staffing Budget: £{spend:,.0f}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    if school.send and school.send.has_send_data():
        total_send = school.send.get_total_send()
        ehc = school.send.ehc_plan or 0
        badges = ""
        if school.send.has_sen_unit:
            badges += '<span class="sen-unit-badge">SEN Unit</span>'
        if school.send.has_resourced_provision:
            badges += '<span class="sen-unit-badge">Resourced Provision</span>'
        
        st.markdown(f"""
        <div class="send-highlight">
            <h3>SEND Profile: {total_send} pupils ({ehc} EHC Plans) {badges}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Conversation Starters",
        "Contact Details",
        "Financial Data",
        "SEND Opportunities",
        "Full Details"
    ])
    
    with tab1:
        display_conversation_starters(school, service)
    with tab2:
        display_contact_info(school)
    with tab3:
        display_financial_data(school)
    with tab4:
        display_send_data(school)
    with tab5:
        display_full_details(school)


def display_conversation_starters(school: School, service):
    st.subheader("Conversation Starters")
    
    financial_starters = [s for s in school.conversation_starters if not (s.source and s.source.startswith("http"))]
    ofsted_starters = [s for s in school.conversation_starters if s.source and s.source.startswith("http")]
    
    st.markdown('<div class="section-header section-header-financial"><strong>FINANCIAL CONVERSATION STARTERS</strong></div>', unsafe_allow_html=True)
    
    if financial_starters:
        for i, starter in enumerate(financial_starters, 1):
            with st.expander(f"**{i}. {starter.topic}**", expanded=(i == 1)):
                st.markdown(f"""
                <div class="starter-card">
                    <div class="starter-detail">{starter.detail}</div>
                </div>
                """, unsafe_allow_html=True)
                if starter.source:
                    st.caption(f"Source: {starter.source}")
                st.code(starter.detail, language=None)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        num_starters = st.number_input("How many?", min_value=1, max_value=10, value=5, key="fin_starters")
    with col2:
        if st.button("Generate Financial Conversation Starters", type="primary"):
            with st.spinner("Generating insights from financial data..."):
                school_with_starters = service.get_school_intelligence(
                    school.school_name, force_refresh=True, num_starters=num_starters
                )
            if school_with_starters and school_with_starters.conversation_starters:
                if is_in_shortlist(school.urn):
                    st.session_state.shortlist[school.urn]["school"] = school_with_starters
                st.success(f"Generated {len(school_with_starters.conversation_starters)} starters!")
                st.rerun()
            else:
                st.error("Failed to generate starters. Check your API key.")
    
    st.divider()
    
    st.markdown('<div class="section-header section-header-ofsted"><strong>OFSTED CONVERSATION STARTERS</strong></div>', unsafe_allow_html=True)
    
    if ofsted_starters:
        for i, starter in enumerate(ofsted_starters, 1):
            with st.expander(f"**{i}. {starter.topic}**", expanded=(i == 1)):
                st.markdown(f"""
                <div class="starter-card-ofsted">
                    <div class="starter-detail">{starter.detail}</div>
                </div>
                """, unsafe_allow_html=True)
                if starter.source:
                    st.markdown(f"**Source:** [View Ofsted Report]({starter.source})")
                st.code(starter.detail, language=None)
    
    if school.ofsted and school.ofsted.rating:
        st.info(f"**Current Ofsted Rating:** {school.ofsted.rating} | **Inspected:** {school.ofsted.inspection_date or 'Unknown'}")
        if school.ofsted.report_url:
            st.markdown(f"[View Full Ofsted Report]({school.ofsted.report_url})")
    
    st.markdown("""
    <div style="background-color: #1a3a5c; padding: 0.75rem 1rem; border-radius: 6px; border-left: 4px solid #3182ce; margin: 0.5rem 0;">
        <strong>Note:</strong> Fetching Ofsted report takes up to 60 seconds as we download and analyze the PDF.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    col_ofsted1, col_ofsted2 = st.columns([1, 3])
    with col_ofsted2:
        if st.button("Fetch Ofsted Report & Generate Starters", type="primary", key="ofsted_btn"):
            with st.spinner("Downloading Ofsted PDF and analyzing... This takes up to 60 seconds..."):
                school_with_ofsted = service.get_school_intelligence_with_ofsted(
                    school.school_name, force_refresh=True, num_starters=3, include_ofsted=True
                )
            if school_with_ofsted:
                if is_in_shortlist(school.urn):
                    st.session_state.shortlist[school.urn]["school"] = school_with_ofsted
                new_ofsted_starters = [s for s in school_with_ofsted.conversation_starters if s.source and s.source.startswith("http")]
                if new_ofsted_starters:
                    st.success(f"Generated {len(new_ofsted_starters)} Ofsted-based starters!")
                    st.rerun()
                elif school_with_ofsted.ofsted:
                    st.info("Ofsted data fetched but no specific improvement areas found for conversation starters.")
                    st.rerun()
                else:
                    st.warning("Could not fetch Ofsted report for this school.")
            else:
                st.error("Failed to analyze Ofsted report.")
    
    st.divider()
    st.caption("For SEND-focused conversation starters, see the SEND Opportunities tab.")


def display_contact_info(school: School):
    st.subheader("Key Contacts")
    
    if school.headteacher:
        head = school.headteacher
        st.markdown(f"""
        <div class="contact-card">
            <h4>{head.full_name}</h4>
            <p><strong>Role:</strong> Headteacher</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Phone:**")
            st.write(school.phone or "Not available")
        with col2:
            st.write("**Website:**")
            if school.website:
                website = school.website if school.website.startswith('http') else f"http://{school.website}"
                st.markdown(f"[{school.website}]({website})")
            else:
                st.write("Not available")
    else:
        st.info("No headteacher information available")
    
    st.divider()
    st.write("**Address:**")
    st.write(school.get_full_address() or "Address not available")
    
    if school.trust_name:
        st.divider()
        st.write("**Trust:**")
        st.write(school.trust_name)


def display_financial_data(school: School):
    st.subheader("Financial Data")
    st.caption("Data from Government Financial Benchmarking Tool")
    
    fbit_url = get_fbit_url(school.urn)
    st.markdown(f"[View on Gov.uk Financial Benchmarking Tool]({fbit_url})")
    
    if school.financial and school.financial.has_financial_data():
        fin = school.financial
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if fin.total_teaching_support_costs:
                st.metric("Total Staffing Costs", f"£{fin.total_teaching_support_costs:,.0f}")
            else:
                st.metric("Total Staffing Costs", "No data")
        with col2:
            if fin.total_expenditure:
                st.metric("Total Expenditure", f"£{fin.total_expenditure:,.0f}")
        with col3:
            if fin.agency_supply_costs and fin.agency_supply_costs > 0:
                st.metric("Agency Supply", f"£{fin.agency_supply_costs:,.0f}")
            else:
                st.metric("Agency Supply", "£0")
        
        st.divider()
        st.write("**Cost Breakdown:**")
        
        costs = [
            ("Total Staffing Costs", fin.total_teaching_support_costs, True),
            ("Teaching Staff (E01)", fin.teaching_staff_costs, False),
            ("Supply Teaching (E02)", fin.supply_teaching_costs, False),
            ("Educational Support (E03)", fin.educational_support_costs, False),
            ("Agency Supply (E26)", fin.agency_supply_costs, False),
            ("Consultancy (E27)", fin.educational_consultancy_costs, False),
        ]
        
        for label, value, highlight in costs:
            if value and value > 0:
                if fin.total_pupils and fin.total_pupils > 0:
                    per_pupil = value / fin.total_pupils
                    if highlight:
                        st.write(f"- **{label}:** £{value:,.0f} (£{per_pupil:,.0f} per pupil)")
                    else:
                        st.write(f"- {label}: £{value:,.0f} (£{per_pupil:,.0f} per pupil)")
                else:
                    st.write(f"- {label}: £{value:,.0f}")
        
        st.divider()
        if fin.total_teaching_support_costs and fin.total_teaching_support_costs >= 500000:
            st.markdown(f'<span class="priority-high">HIGH PRIORITY</span> This school invests **£{fin.total_teaching_support_costs:,.0f}** in staffing annually!', unsafe_allow_html=True)
        elif fin.total_teaching_support_costs and fin.total_teaching_support_costs >= 200000:
            st.info(f"**Sales Insight:** This school invests **£{fin.total_teaching_support_costs:,.0f}** in staffing annually.")
    else:
        st.info("No financial data available for this school")
        st.markdown(f"You can check manually: [Gov.uk Financial Benchmarking Tool]({fbit_url})")


def display_send_data(school: School):
    st.subheader("SEND Opportunities")
    st.caption("Data from DfE Special Educational Needs in England")
    
    if school.send and school.send.has_send_data():
        send = school.send
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total = send.get_total_send()
            st.metric("Total SEND", total)
        with col2:
            st.metric("EHC Plans", send.ehc_plan or 0)
        with col3:
            st.metric("SEN Support", send.sen_support or 0)
        with col4:
            pct = send.get_send_percentage()
            st.metric("SEND %", f"{pct:.1f}%" if pct else "N/A")
        
        if send.has_sen_unit or send.has_resourced_provision:
            st.divider()
            badges = []
            if send.has_sen_unit:
                badges.append("**SEN Unit** - Dedicated SEND infrastructure (HOT LEAD)")
            if send.has_resourced_provision:
                badges.append("**Resourced Provision** - Specialist provision (HOT LEAD)")
            for b in badges:
                st.markdown(b)
        
        st.divider()
        st.write("**EHC Plan Breakdown by Need:**")
        
        needs = [
            ("Autism (ASD)", send.ehc_asd),
            ("SEMH", send.ehc_semh),
            ("Speech & Language (SLCN)", send.ehc_slcn),
            ("Severe Learning Difficulty", send.ehc_sld),
            ("Moderate Learning Difficulty", send.ehc_mld),
            ("Physical Disability", send.ehc_pd),
            ("Hearing Impairment", send.ehc_hi),
            ("Visual Impairment", send.ehc_vi),
            ("Profound & Multiple LD", send.ehc_pmld),
            ("Specific Learning Difficulty", send.ehc_spld),
        ]
        
        sorted_needs = sorted(needs, key=lambda x: x[1] or 0, reverse=True)
        for need, count in sorted_needs:
            if count and count > 0:
                st.write(f"- {need}: **{count}** pupils")
        
        st.divider()
        priority = send.get_send_priority_level()
        score = send.get_send_priority_score()
        
        if priority == "HIGH":
            st.markdown(f'<span class="priority-high">HIGH PRIORITY</span> SEND Priority Score: {score}', unsafe_allow_html=True)
        elif priority == "MEDIUM":
            st.markdown(f'<span class="priority-medium">MEDIUM</span> SEND Priority Score: {score}', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="priority-low">LOW</span> SEND Priority Score: {score}', unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<div class="section-header section-header-send"><strong>SEND CONVERSATION STARTERS</strong></div>', unsafe_allow_html=True)
        
        ehc = send.ehc_plan or 0
        
        if send.has_sen_unit or send.has_resourced_provision:
            unit_type = "SEN unit" if send.has_sen_unit else "resourced provision"
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-detail">"I noticed you have a dedicated {unit_type} - how are you currently staffing it? We work with schools to provide trained SEND specialists for both permanent and cover positions."</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(f"I noticed you have a dedicated {unit_type} - how are you currently staffing it? We work with schools to provide trained SEND specialists for both permanent and cover positions.", language=None)
        
        if ehc >= 10:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-detail">"You have {ehc} pupils with EHC plans - that's a significant support requirement. How are you managing their 1:1 support? We have ASD-trained and SEMH-specialist TAs available."</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(f"You have {ehc} pupils with EHC plans - that's a significant support requirement. How are you managing their 1:1 support? We have ASD-trained and SEMH-specialist TAs available.", language=None)
        
        if send.ehc_asd and send.ehc_asd >= 3:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-detail">"With {send.ehc_asd} pupils with autism, having the right trained support staff is crucial. Are you finding it difficult to recruit autism-trained TAs? We specialise in placing SEND specialists."</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(f"With {send.ehc_asd} pupils with autism, having the right trained support staff is crucial. Are you finding it difficult to recruit autism-trained TAs? We specialise in placing SEND specialists.", language=None)
        
        if send.ehc_semh and send.ehc_semh >= 3:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-detail">"I see you have {send.ehc_semh} pupils with SEMH needs - this is one of the hardest areas to recruit for. We have experienced SEMH specialists who understand de-escalation and behaviour management."</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(f"I see you have {send.ehc_semh} pupils with SEMH needs - this is one of the hardest areas to recruit for. We have experienced SEMH specialists who understand de-escalation and behaviour management.", language=None)
        
        total = send.get_total_send()
        if total >= 15:
            st.markdown(f"""
            <div class="starter-card-send">
                <div class="starter-detail">"With {total} SEND pupils, what happens when your SENCO or specialist TAs are absent? We can provide trained cover at short notice to maintain continuity for your vulnerable learners."</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(f"With {total} SEND pupils, what happens when your SENCO or specialist TAs are absent? We can provide trained cover at short notice to maintain continuity for your vulnerable learners.", language=None)
        
        if not (send.has_sen_unit or send.has_resourced_provision or ehc >= 10 or (send.ehc_asd and send.ehc_asd >= 3) or (send.ehc_semh and send.ehc_semh >= 3) or total >= 15):
            st.caption("This school has lower SEND numbers - focus on general supply and cover needs.")
    
    else:
        st.info("No SEND data available for this school")
        st.caption("This may be because the school is not in the DfE SEND dataset (e.g., independent schools)")


def display_full_details(school: School):
    st.subheader("Full School Details")
    
    details = {
        "URN": school.urn,
        "School Name": school.school_name,
        "Local Authority": school.la_name,
        "School Type": school.school_type,
        "Phase": school.phase,
        "Number of Pupils": school.pupil_count,
        "Headteacher": school.headteacher.full_name if school.headteacher else "N/A",
        "Phone": school.phone,
        "Website": school.website,
        "Address": school.get_full_address(),
        "Trust Name": school.trust_name or "N/A",
        "Financial Priority": school.get_sales_priority(),
        "SEND Priority": school.get_send_priority(),
        "Combined Priority": school.get_combined_priority(),
    }
    
    if school.financial:
        details["Total Staffing Spend"] = school.financial.get_total_staffing_formatted()
        if school.financial.agency_supply_costs:
            details["Agency Spend"] = school.financial.get_agency_spend_formatted()
    
    if school.send:
        details["Total SEND Pupils"] = school.send.get_total_send()
        details["EHC Plans"] = school.send.ehc_plan or 0
        details["SEN Support"] = school.send.sen_support or 0
        details["Has SEN Unit"] = "Yes" if school.send.has_sen_unit else "No"
        details["Has Resourced Provision"] = "Yes" if school.send.has_resourced_provision else "No"
    
    df = pd.DataFrame([{"Field": k, "Value": str(v) if v else "N/A"} for k, v in details.items()])
    st.dataframe(df, hide_index=True, use_container_width=True)
    
    st.divider()
    st.markdown(f"[View Financial Data on Gov.uk]({get_fbit_url(school.urn)})")
    st.caption(f"Data source: {school.data_source}")


if __name__ == "__main__":
    main()
