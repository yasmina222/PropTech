"""
School Research Assistant - Data Loader
Loads and merges: Financial + GIAS + SEND data via URN
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from models_v2 import (
    School, Contact, ContactRole, FinancialData, OfstedData, SENDData
)
from config_v2 import (
    DATA_SOURCE, CSV_FILE_PATH_FINANCIAL, CSV_FILE_PATH_GIAS, 
    CSV_FILE_PATH_SEND, DATABRICKS_CONFIG
)

logger = logging.getLogger(__name__)


class DataLoader:
    
    def __init__(self, source: str = None):
        self.source = source or DATA_SOURCE
        self._schools_cache: Optional[List[School]] = None
        self._schools_by_name: Dict[str, School] = {}
        self._schools_by_urn: Dict[str, School] = {}
        logger.info(f"DataLoader initialized with source: {self.source}")
    
    def load(self) -> List[School]:
        if self._schools_cache is not None:
            return self._schools_cache
        
        if self.source == "csv":
            schools = self._load_and_merge_csvs()
        elif self.source == "databricks":
            schools = self._load_from_databricks()
        else:
            raise ValueError(f"Unknown data source: {self.source}")
        
        self._schools_cache = schools
        self._schools_by_name = {s.school_name: s for s in schools}
        self._schools_by_urn = {s.urn: s for s in schools}
        
        logger.info(f"Loaded {len(schools)} schools from {self.source}")
        return schools
    
    def _find_csv_file(self, csv_path: str) -> Optional[Path]:
        possible_paths = [
            csv_path,
            Path(__file__).parent / csv_path,
            Path(__file__).parent / "data" / Path(csv_path).name,
            f"data/{Path(csv_path).name}",
            Path(csv_path).name,
        ]
        for path in possible_paths:
            p = Path(path)
            if p.exists():
                return p
        return None
    
    def _load_and_merge_csvs(self) -> List[School]:
        schools = []
        
        gias_data = self._load_gias_csv()
        logger.info(f"Loaded {len(gias_data)} schools from GIAS")
        
        financial_data = self._load_financial_csv()
        logger.info(f"Loaded {len(financial_data)} schools from Financial data")
        
        send_data = self._load_send_csv()
        logger.info(f"Loaded {len(send_data)} schools from SEND data")
        
        all_urns = set(gias_data.keys()) | set(financial_data.keys())
        logger.info(f"Merging {len(all_urns)} unique schools")
        
        for urn in all_urns:
            gias = gias_data.get(urn, {})
            fin = financial_data.get(urn, {})
            send = send_data.get(urn, {})
            
            merged = {**fin, **gias}
            if fin:
                merged['_financial'] = fin
            if send:
                merged['_send'] = send
            
            try:
                school = self._merged_row_to_school(merged, urn)
                if school:
                    schools.append(school)
            except Exception as e:
                logger.warning(f"Error creating school {urn}: {e}")
                continue
        
        return schools
    
    def _load_gias_csv(self) -> Dict[str, Dict]:
        gias_path = self._find_csv_file(CSV_FILE_PATH_GIAS)
        if not gias_path:
            logger.warning(f"GIAS CSV not found: {CSV_FILE_PATH_GIAS}")
            return {}
        
        data = {}
        with open(gias_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urn = self._clean_urn(row.get('urn') or row.get('URN'))
                if urn:
                    data[urn] = row
        return data
    
    def _load_financial_csv(self) -> Dict[str, Dict]:
        fin_path = self._find_csv_file(CSV_FILE_PATH_FINANCIAL)
        if not fin_path:
            logger.warning(f"Financial CSV not found: {CSV_FILE_PATH_FINANCIAL}")
            return {}
        
        data = {}
        with open(fin_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status') and row.get('status') != 'success':
                    continue
                urn = self._clean_urn(row.get('URN') or row.get('urn'))
                if urn:
                    data[urn] = row
        return data
    
    def _load_send_csv(self) -> Dict[str, Dict]:
        send_path = self._find_csv_file(CSV_FILE_PATH_SEND)
        if not send_path:
            logger.warning(f"SEND CSV not found: {CSV_FILE_PATH_SEND}")
            return {}
        
        data = {}
        with open(send_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urn = self._clean_urn(row.get('URN') or row.get('urn'))
                if urn:
                    data[urn] = row
        return data
    
    def _clean_urn(self, urn) -> Optional[str]:
        if urn is None or urn == '' or str(urn).lower() == 'nan':
            return None
        try:
            return str(int(float(urn)))
        except (ValueError, TypeError):
            return str(urn).strip()
    
    def _safe_float(self, value) -> Optional[float]:
        if value is None or value == '' or str(value).lower() == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        if value is None or value == '' or str(value).lower() in ('nan', 'x', 'z', 'c'):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _get_value(self, row: Dict[str, Any], *keys) -> Optional[str]:
        for key in keys:
            value = row.get(key)
            if value is not None and value != '' and str(value).lower() != 'nan':
                return str(value).strip()
        return None
    
    def _clean_phone(self, phone) -> Optional[str]:
        if phone is None:
            return None
        phone = str(phone).strip()
        if phone.endswith('.0'):
            phone = phone[:-2]
        if phone.startswith('20') and len(phone) == 10:
            phone = f"020 {phone[2:6]} {phone[6:]}"
        elif phone.startswith('2') and len(phone) == 10:
            phone = f"020 {phone[1:5]} {phone[5:]}"
        return phone if phone else None
    
    def _merged_row_to_school(self, row: Dict[str, Any], urn: str) -> Optional[School]:
        school_name = self._get_value(row, 'school_name', 'SchoolName', 'school_name_gias') or f"School {urn}"
        la_name = self._get_value(row, 'la_name', 'LAName', 'la_name_gias')
        school_type = self._get_value(row, 'school_type', 'SchoolType')
        phase = self._get_value(row, 'phase', 'Phase')
        pupil_count = self._safe_int(row.get('pupil_count') or row.get('TotalPupils'))
        phone = self._clean_phone(row.get('phone'))
        website = self._get_value(row, 'website')
        
        headteacher = None
        head_title = self._get_value(row, 'head_title')
        head_first = self._get_value(row, 'head_first_name')
        head_last = self._get_value(row, 'head_last_name')
        head_full = self._get_value(row, 'headteacher')
        
        if head_full or (head_first and head_last):
            full_name = head_full or f"{head_title or ''} {head_first or ''} {head_last or ''}".strip()
            headteacher = Contact(
                full_name=full_name,
                role=ContactRole.HEADTEACHER,
                title=head_title,
                first_name=head_first,
                last_name=head_last,
                phone=phone,
                confidence_score=1.0
            )
        
        fin = row.get('_financial', row)
        financial = FinancialData(
            total_expenditure=self._safe_float(fin.get('TotalExpenditure') or fin.get('total_expenditure')),
            total_pupils=self._safe_float(fin.get('TotalPupils') or row.get('pupil_count')),
            total_teaching_support_costs=self._safe_float(fin.get('TotalTeachingSupportStaffCosts') or fin.get('total_teaching_support_costs')),
            teaching_staff_costs=self._safe_float(fin.get('TeachingStaffCosts') or fin.get('teaching_staff_costs')),
            supply_teaching_costs=self._safe_float(fin.get('SupplyTeachingStaffCosts') or fin.get('supply_teaching_costs')),
            agency_supply_costs=self._safe_float(fin.get('AgencySupplyTeachingStaffCosts') or fin.get('agency_supply_costs')),
            educational_support_costs=self._safe_float(fin.get('EducationSupportStaffCosts') or fin.get('educational_support_costs')),
            educational_consultancy_costs=self._safe_float(fin.get('EducationalConsultancyCosts') or fin.get('educational_consultancy_costs')),
        )
        
        send = None
        send_row = row.get('_send')
        if send_row:
            sen_unit_val = send_row.get('SEN_Unit', '0')
            rp_unit_val = send_row.get('RP_Unit', '0')
            
            send = SENDData(
                total_pupils=self._safe_int(send_row.get('Total pupils')),
                sen_support=self._safe_int(send_row.get('SEN support')),
                ehc_plan=self._safe_int(send_row.get('EHC plan')),
                has_sen_unit=(str(sen_unit_val).strip() == '1'),
                has_resourced_provision=(str(rp_unit_val).strip() == '1'),
                ehc_asd=self._safe_int(send_row.get('EHC_Primary_need_asd')),
                ehc_semh=self._safe_int(send_row.get('EHC_Primary_need_semh')),
                ehc_slcn=self._safe_int(send_row.get('EHC_Primary_need_slcn')),
                ehc_sld=self._safe_int(send_row.get('EHC_Primary_need_sld')),
                ehc_pmld=self._safe_int(send_row.get('EHC_Primary_need_pmld')),
                ehc_mld=self._safe_int(send_row.get('EHC_Primary_need_mld')),
                ehc_spld=self._safe_int(send_row.get('EHC_Primary_need_spld')),
                ehc_hi=self._safe_int(send_row.get('EHC_Primary_need_hi')),
                ehc_vi=self._safe_int(send_row.get('EHC_Primary_need_vi')),
                ehc_pd=self._safe_int(send_row.get('EHC_Primary_need_pd')),
                sup_asd=self._safe_int(send_row.get('SUP_Primary_need_asd')),
                sup_semh=self._safe_int(send_row.get('SUP_Primary_need_semh')),
                sup_slcn=self._safe_int(send_row.get('SUP_Primary_need_slcn')),
            )
        
        address_1 = self._get_value(row, 'address_1')
        address_2 = self._get_value(row, 'address_2')
        address_3 = self._get_value(row, 'address_3')
        town = self._get_value(row, 'town')
        county = self._get_value(row, 'county')
        postcode = self._get_value(row, 'postcode')
        trust_code = self._get_value(row, 'trust_code')
        trust_name = self._get_value(row, 'trust_name')
        
        school = School(
            urn=urn,
            school_name=school_name,
            la_name=la_name,
            school_type=school_type,
            phase=phase,
            address_1=address_1,
            address_2=address_2,
            address_3=address_3,
            town=town,
            county=county,
            postcode=postcode,
            phone=phone,
            website=website,
            trust_code=trust_code,
            trust_name=trust_name,
            pupil_count=pupil_count,
            headteacher=headteacher,
            contacts=[headteacher] if headteacher else [],
            financial=financial,
            send=send,
            data_source="csv_merged"
        )
        
        return school
    
    def _load_from_databricks(self) -> List[School]:
        logger.warning("Databricks connection not yet implemented")
        return self._load_and_merge_csvs()
    
    def get_all_schools(self) -> List[School]:
        return self.load()
    
    def get_school_names(self) -> List[str]:
        schools = self.load()
        return sorted([s.school_name for s in schools])
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        self.load()
        return self._schools_by_name.get(name)
    
    def get_school_by_urn(self, urn: str) -> Optional[School]:
        self.load()
        clean_urn = self._clean_urn(urn)
        return self._schools_by_urn.get(clean_urn)
    
    def search_schools(self, query: str) -> List[School]:
        schools = self.load()
        query_lower = query.lower()
        return [s for s in schools if query_lower in s.school_name.lower()]
    
    def get_schools_by_priority(self, priority: str) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.get_sales_priority() == priority]
    
    def get_schools_by_borough(self, borough: str) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.la_name and s.la_name.lower() == borough.lower()]
    
    def get_schools_with_staffing_spend(self, min_spend: float = 0) -> List[School]:
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.total_teaching_support_costs 
            and s.financial.total_teaching_support_costs > min_spend
        ]
    
    def get_schools_with_agency_spend(self, min_spend: float = 0) -> List[School]:
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.agency_supply_costs 
            and s.financial.agency_supply_costs > min_spend
        ]
    
    def get_top_spenders(self, limit: int = 20, spend_type: str = "total") -> List[School]:
        schools = self.load()
        if spend_type == "agency":
            schools_with_spend = [s for s in schools if s.financial and s.financial.agency_supply_costs]
            return sorted(schools_with_spend, key=lambda s: s.financial.agency_supply_costs or 0, reverse=True)[:limit]
        else:
            schools_with_spend = [s for s in schools if s.financial and s.financial.total_teaching_support_costs]
            return sorted(schools_with_spend, key=lambda s: s.financial.total_teaching_support_costs or 0, reverse=True)[:limit]
    
    def get_top_agency_spenders(self, limit: int = 20) -> List[School]:
        return self.get_top_spenders(limit=limit, spend_type="agency")
    
    def get_schools_with_send_data(self) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.send and s.send.has_send_data()]
    
    def get_schools_with_sen_unit(self) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.send and s.send.has_sen_unit]
    
    def get_schools_with_resourced_provision(self) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.send and s.send.has_resourced_provision]
    
    def get_top_send_schools(self, limit: int = 20) -> List[School]:
        schools = self.load()
        schools_with_send = [s for s in schools if s.send and s.send.has_send_data()]
        return sorted(schools_with_send, key=lambda s: s.send.get_send_priority_score(), reverse=True)[:limit]
    
    def get_schools_by_send_priority(self, priority: str) -> List[School]:
        schools = self.load()
        return [s for s in schools if s.get_send_priority() == priority]
    
    def get_boroughs(self) -> List[str]:
        schools = self.load()
        boroughs = set(s.la_name for s in schools if s.la_name)
        return sorted(list(boroughs))
    
    def get_statistics(self) -> Dict[str, Any]:
        schools = self.load()
        
        total_staffing_spend = sum(
            s.financial.total_teaching_support_costs or 0 
            for s in schools if s.financial
        )
        total_agency_spend = sum(
            s.financial.agency_supply_costs or 0 
            for s in schools if s.financial
        )
        
        high = len([s for s in schools if s.get_sales_priority() == "HIGH"])
        medium = len([s for s in schools if s.get_sales_priority() == "MEDIUM"])
        low = len([s for s in schools if s.get_sales_priority() == "LOW"])
        
        with_contacts = len([s for s in schools if s.headteacher])
        with_phone = len([s for s in schools if s.phone])
        with_financial = len([s for s in schools if s.financial and s.financial.total_teaching_support_costs])
        
        with_send = len([s for s in schools if s.send and s.send.has_send_data()])
        with_sen_unit = len([s for s in schools if s.send and s.send.has_sen_unit])
        with_rp = len([s for s in schools if s.send and s.send.has_resourced_provision])
        send_high = len([s for s in schools if s.get_send_priority() == "HIGH"])
        
        total_ehc = sum(s.send.ehc_plan or 0 for s in schools if s.send)
        total_sen_support = sum(s.send.sen_support or 0 for s in schools if s.send)
        
        return {
            "total_schools": len(schools),
            "with_contacts": with_contacts,
            "with_phone": with_phone,
            "with_financial_data": with_financial,
            "with_agency_spend": len(self.get_schools_with_agency_spend()),
            "total_staffing_spend": f"£{total_staffing_spend:,.0f}",
            "total_agency_spend": f"£{total_agency_spend:,.0f}",
            "high_priority": high,
            "medium_priority": medium,
            "low_priority": low,
            "boroughs": len(self.get_boroughs()),
            "with_send_data": with_send,
            "with_sen_unit": with_sen_unit,
            "with_resourced_provision": with_rp,
            "send_high_priority": send_high,
            "total_ehc_plans": total_ehc,
            "total_sen_support": total_sen_support,
            "data_source": self.source,
        }
    
    def refresh(self) -> List[School]:
        self._schools_cache = None
        self._schools_by_name = {}
        self._schools_by_urn = {}
        return self.load()


_loader_instance: Optional[DataLoader] = None

def get_data_loader() -> DataLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DataLoader()
    return _loader_instance
