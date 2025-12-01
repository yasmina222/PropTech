"""
School Research Assistant - Pydantic Models (v2)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ContactRole(str, Enum):
    HEADTEACHER = "headteacher"
    DEPUTY_HEAD = "deputy_head"
    ASSISTANT_HEAD = "assistant_head"
    BUSINESS_MANAGER = "business_manager"
    SENCO = "senco"
    UNKNOWN = "unknown"


class Contact(BaseModel):
    full_name: str = Field(description="Full name of the contact")
    role: ContactRole = Field(default=ContactRole.UNKNOWN)
    title: Optional[str] = Field(default=None)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @field_validator('phone', mode='before')
    @classmethod
    def clean_phone(cls, v):
        if v is None:
            return None
        v = str(v)
        if v.endswith('.0'):
            v = v[:-2]
        if v.startswith('20') and len(v) == 10:
            v = f"020 {v[2:6]} {v[6:]}"
        return v


class FinancialData(BaseModel):
    total_expenditure: Optional[float] = Field(default=None)
    total_pupils: Optional[float] = Field(default=None)
    teaching_staff_costs: Optional[float] = Field(default=None)
    supply_teaching_costs: Optional[float] = Field(default=None)
    educational_support_costs: Optional[float] = Field(default=None)
    agency_supply_costs: Optional[float] = Field(default=None)
    educational_consultancy_costs: Optional[float] = Field(default=None)
    total_teaching_support_costs: Optional[float] = Field(default=None)
    total_teaching_support_spend_per_pupil: Optional[str] = Field(default=None)
    comparison_to_other_schools: Optional[str] = Field(default=None)
    
    def has_financial_data(self) -> bool:
        return self.total_teaching_support_costs is not None or self.total_expenditure is not None
    
    def has_agency_spend(self) -> bool:
        if self.agency_supply_costs is None:
            return False
        return self.agency_supply_costs > 0
    
    def get_total_staffing_formatted(self) -> str:
        if self.total_teaching_support_costs is None or self.total_teaching_support_costs == 0:
            return "No data"
        return f"£{self.total_teaching_support_costs:,.0f}"
    
    def get_agency_spend_formatted(self) -> str:
        if self.agency_supply_costs is None or self.agency_supply_costs == 0:
            return "£0"
        return f"£{self.agency_supply_costs:,.0f}"
    
    def get_agency_per_pupil(self) -> Optional[float]:
        if self.agency_supply_costs and self.total_pupils and self.total_pupils > 0:
            return self.agency_supply_costs / self.total_pupils
        return None
    
    def get_agency_per_pupil_formatted(self) -> str:
        per_pupil = self.get_agency_per_pupil()
        if per_pupil is None or per_pupil == 0:
            return "£0 per pupil"
        return f"£{per_pupil:,.0f} per pupil"
    
    def get_teaching_per_pupil(self) -> Optional[float]:
        if self.teaching_staff_costs and self.total_pupils and self.total_pupils > 0:
            return self.teaching_staff_costs / self.total_pupils
        return None
    
    def get_priority_level(self) -> str:
        spend = self.total_teaching_support_costs
        if spend is None:
            return "UNKNOWN"
        if spend >= 500000:
            return "HIGH"
        elif spend >= 200000:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_financial_summary(self) -> str:
        lines = []
        if self.total_pupils:
            lines.append(f"Total Pupils: {int(self.total_pupils)}")
        if self.total_expenditure:
            lines.append(f"Total Expenditure: £{self.total_expenditure:,.0f}")
        if self.total_teaching_support_costs:
            lines.append(f"Total Staffing Costs: £{self.total_teaching_support_costs:,.0f}")
            if self.total_pupils and self.total_pupils > 0:
                per_pupil = self.total_teaching_support_costs / self.total_pupils
                lines.append(f"  → £{per_pupil:,.0f} per pupil on staffing")
        if self.teaching_staff_costs:
            lines.append(f"Teaching Staff Costs (E01): £{self.teaching_staff_costs:,.0f}")
        if self.supply_teaching_costs and self.supply_teaching_costs > 0:
            lines.append(f"Supply Teaching Costs (E02): £{self.supply_teaching_costs:,.0f}")
        if self.agency_supply_costs and self.agency_supply_costs > 0:
            lines.append(f"Agency Supply Costs (E26): £{self.agency_supply_costs:,.0f}")
            if self.total_pupils and self.total_pupils > 0:
                per_pupil = self.agency_supply_costs / self.total_pupils
                lines.append(f"  → £{per_pupil:,.0f} per pupil on agency staff")
        if self.educational_support_costs:
            lines.append(f"Educational Support Costs (E03): £{self.educational_support_costs:,.0f}")
        if self.educational_consultancy_costs and self.educational_consultancy_costs > 0:
            lines.append(f"Educational Consultancy (E27): £{self.educational_consultancy_costs:,.0f}")
        return "\n".join(lines) if lines else "No financial data available"


class SENDData(BaseModel):
    """SEND data from DfE Special Educational Needs dataset"""
    total_pupils: Optional[int] = Field(default=None)
    sen_support: Optional[int] = Field(default=None, description="Pupils with SEN Support (no EHC plan)")
    ehc_plan: Optional[int] = Field(default=None, description="Pupils with EHC plans (legally binding)")
    
    has_sen_unit: bool = Field(default=False, description="School has dedicated SEN unit")
    has_resourced_provision: bool = Field(default=False, description="School has resourced provision")
    
    ehc_asd: Optional[int] = Field(default=None, description="Autism spectrum")
    ehc_semh: Optional[int] = Field(default=None, description="Social, emotional, mental health")
    ehc_slcn: Optional[int] = Field(default=None, description="Speech, language, communication")
    ehc_sld: Optional[int] = Field(default=None, description="Severe learning difficulty")
    ehc_pmld: Optional[int] = Field(default=None, description="Profound & multiple learning difficulty")
    ehc_mld: Optional[int] = Field(default=None, description="Moderate learning difficulty")
    ehc_spld: Optional[int] = Field(default=None, description="Specific learning difficulty")
    ehc_hi: Optional[int] = Field(default=None, description="Hearing impairment")
    ehc_vi: Optional[int] = Field(default=None, description="Visual impairment")
    ehc_pd: Optional[int] = Field(default=None, description="Physical disability")
    
    sup_asd: Optional[int] = Field(default=None, description="SEN Support - Autism")
    sup_semh: Optional[int] = Field(default=None, description="SEN Support - SEMH")
    sup_slcn: Optional[int] = Field(default=None, description="SEN Support - SLCN")
    
    def has_send_data(self) -> bool:
        return self.sen_support is not None or self.ehc_plan is not None
    
    def get_total_send(self) -> int:
        return (self.sen_support or 0) + (self.ehc_plan or 0)
    
    def get_send_percentage(self) -> Optional[float]:
        if not self.total_pupils or self.total_pupils == 0:
            return None
        total_send = self.get_total_send()
        return (total_send / self.total_pupils) * 100
    
    def get_ehc_percentage(self) -> Optional[float]:
        if not self.total_pupils or self.total_pupils == 0:
            return None
        return ((self.ehc_plan or 0) / self.total_pupils) * 100
    
    def get_send_priority_score(self) -> int:
        """
        Priority scoring based on sales value analysis:
        - SEN Unit or Resourced Provision = guaranteed ongoing demand
        - EHC plans = legally binding, school MUST provide support
        - ASD/SEMH = specialist needs, harder to staff
        """
        score = 0
        if self.has_sen_unit:
            score += 50
        if self.has_resourced_provision:
            score += 50
        score += (self.ehc_plan or 0) * 3
        score += (self.sen_support or 0) * 1
        score += (self.ehc_asd or 0) * 2
        score += (self.ehc_semh or 0) * 2
        return score
    
    def get_send_priority_level(self) -> str:
        if self.has_sen_unit or self.has_resourced_provision:
            return "HIGH"
        ehc_pct = self.get_ehc_percentage()
        if ehc_pct and ehc_pct > 5:
            return "HIGH"
        if (self.ehc_plan or 0) >= 10:
            return "HIGH"
        if (self.ehc_plan or 0) >= 5 or (self.sen_support or 0) >= 30:
            return "MEDIUM"
        return "LOW"
    
    def get_top_needs(self, limit: int = 3) -> List[tuple]:
        """Get the top EHC need types by count"""
        needs = [
            ("Autism (ASD)", self.ehc_asd or 0),
            ("SEMH", self.ehc_semh or 0),
            ("Speech & Language", self.ehc_slcn or 0),
            ("Severe LD", self.ehc_sld or 0),
            ("Moderate LD", self.ehc_mld or 0),
            ("Physical Disability", self.ehc_pd or 0),
            ("Hearing Impairment", self.ehc_hi or 0),
            ("Visual Impairment", self.ehc_vi or 0),
        ]
        sorted_needs = sorted(needs, key=lambda x: x[1], reverse=True)
        return [(n, c) for n, c in sorted_needs[:limit] if c > 0]
    
    def get_send_summary(self) -> str:
        lines = []
        total = self.get_total_send()
        if total > 0:
            lines.append(f"Total SEND Pupils: {total}")
            pct = self.get_send_percentage()
            if pct:
                lines.append(f"SEND as % of school: {pct:.1f}%")
        if self.ehc_plan:
            lines.append(f"EHC Plans: {self.ehc_plan} (legally binding support required)")
        if self.sen_support:
            lines.append(f"SEN Support: {self.sen_support}")
        if self.has_sen_unit:
            lines.append("⭐ Has dedicated SEN Unit")
        if self.has_resourced_provision:
            lines.append("⭐ Has Resourced Provision")
        top_needs = self.get_top_needs()
        if top_needs:
            lines.append("Top needs: " + ", ".join([f"{n}: {c}" for n, c in top_needs]))
        return "\n".join(lines) if lines else "No SEND data available"


class OfstedData(BaseModel):
    rating: Optional[str] = Field(default=None)
    inspection_date: Optional[str] = Field(default=None)
    report_url: Optional[str] = Field(default=None)
    areas_for_improvement: List[str] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)


class ConversationStarter(BaseModel):
    topic: str = Field(description="Brief topic heading")
    detail: str = Field(description="The actual conversation starter script")
    source: Optional[str] = Field(default=None)
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Staffing Budget Opportunity",
                "detail": "I noticed from government data that you invest over £2 million annually in staffing.",
                "source": "Financial Benchmarking Data",
                "relevance_score": 0.95
            }
        }


class School(BaseModel):
    urn: str = Field(description="Unique Reference Number")
    school_name: str = Field(description="Official school name")
    
    la_name: Optional[str] = Field(default=None)
    address_1: Optional[str] = Field(default=None)
    address_2: Optional[str] = Field(default=None)
    address_3: Optional[str] = Field(default=None)
    town: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    postcode: Optional[str] = Field(default=None)
    
    school_type: Optional[str] = Field(default=None)
    phase: Optional[str] = Field(default=None)
    pupil_count: Optional[int] = Field(default=None)
    
    trust_code: Optional[str] = Field(default=None)
    trust_name: Optional[str] = Field(default=None)
    
    phone: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    
    headteacher: Optional[Contact] = Field(default=None)
    contacts: List[Contact] = Field(default_factory=list)
    
    financial: Optional[FinancialData] = Field(default=None)
    send: Optional[SENDData] = Field(default=None)
    ofsted: Optional[OfstedData] = Field(default=None)
    
    conversation_starters: List[ConversationStarter] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=datetime.now)
    data_source: str = Field(default="csv")
    
    @field_validator('pupil_count', mode='before')
    @classmethod
    def parse_pupil_count(cls, v):
        if v is None or v == '':
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None
    
    @field_validator('phone', mode='before')
    @classmethod
    def clean_phone(cls, v):
        if v is None:
            return None
        v = str(v)
        if v.endswith('.0'):
            v = v[:-2]
        return v
    
    def get_full_address(self) -> str:
        parts = [self.address_1, self.address_2, self.address_3, self.town, self.county, self.postcode]
        return ", ".join([p for p in parts if p])
    
    def get_sales_priority(self) -> str:
        if not self.financial:
            return "UNKNOWN"
        return self.financial.get_priority_level()
    
    def get_send_priority(self) -> str:
        if not self.send:
            return "UNKNOWN"
        return self.send.get_send_priority_level()
    
    def get_combined_priority(self) -> str:
        """Combined priority considering both financial and SEND"""
        fin_priority = self.get_sales_priority()
        send_priority = self.get_send_priority()
        if fin_priority == "HIGH" or send_priority == "HIGH":
            return "HIGH"
        if fin_priority == "MEDIUM" or send_priority == "MEDIUM":
            return "MEDIUM"
        return "LOW"
    
    def has_contact_details(self) -> bool:
        return self.headteacher is not None
    
    def to_llm_context(self) -> str:
        lines = [
            f"SCHOOL: {self.school_name}",
            f"URN: {self.urn}",
            f"Type: {self.school_type or 'Unknown'} ({self.phase or 'Unknown phase'})",
            f"Local Authority: {self.la_name or 'Unknown'}",
            f"Pupil Count: {self.pupil_count or 'Unknown'}",
        ]
        
        if self.headteacher:
            lines.append(f"\nHEADTEACHER: {self.headteacher.full_name}")
            if self.phone:
                lines.append(f"School Phone: {self.phone}")
            if self.website:
                lines.append(f"Website: {self.website}")
        
        address = self.get_full_address()
        if address:
            lines.append(f"Address: {address}")
        
        if self.financial:
            lines.append("\nFINANCIAL DATA (from Government Benchmarking Tool):")
            lines.append(self.financial.get_financial_summary())
            priority = self.financial.get_priority_level()
            if priority == "HIGH":
                lines.append("\n⭐ SALES PRIORITY: HIGH - Large staffing budget!")
            elif priority == "MEDIUM":
                lines.append("\n📊 SALES PRIORITY: MEDIUM - Mid-size staffing budget")
        
        if self.send and self.send.has_send_data():
            lines.append("\nSEND DATA (from DfE Special Educational Needs data):")
            lines.append(self.send.get_send_summary())
            send_priority = self.send.get_send_priority_level()
            if send_priority == "HIGH":
                lines.append("\n🎯 SEND PRIORITY: HIGH - Strong demand for SEND specialists!")
        
        if self.ofsted:
            lines.append(f"\nOFSTED RATING: {self.ofsted.rating or 'Unknown'}")
            if self.ofsted.inspection_date:
                lines.append(f"Inspection Date: {self.ofsted.inspection_date}")
            if self.ofsted.areas_for_improvement:
                lines.append("Areas for improvement:")
                for area in self.ofsted.areas_for_improvement:
                    lines.append(f"  - {area}")
        
        return "\n".join(lines)


class SchoolSearchResult(BaseModel):
    schools: List[School] = Field(default_factory=list)
    total_count: int = Field(default=0)
    query: Optional[str] = Field(default=None)


class ConversationStarterResponse(BaseModel):
    conversation_starters: List[ConversationStarter] = Field(
        description="List of conversation starters for sales consultants"
    )
    summary: Optional[str] = Field(default=None)
    sales_priority: str = Field(default="MEDIUM")
