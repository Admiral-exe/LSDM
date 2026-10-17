"""
Pydantic schemas for data validation and API contracts.
"""
from typing import Optional
from pydantic import BaseModel, Field

class MonthlySampleBase(BaseModel):
    file_name: str
    month_name: str
    year: int
    sheet_name: str
    group_code: str
    sr_no: Optional[int] = None
    receive_date: Optional[str] = None
    sample_no: int
    division: Optional[str] = ""
    tp_proce: Optional[str] = ""
    catgo_name: Optional[str] = ""
    catego_no: Optional[str] = ""
    g_og: Optional[str] = ""
    sample_name: str
    batch_no: str
    exp_date: Optional[str] = ""
    name_of_mfg: Optional[str] = ""
    di_name_city: Optional[str] = ""
    inspector_name: Optional[str] = ""
    city_district: Optional[str] = ""
    memorandum: str
    distributed_to: Optional[str] = ""
    distribution_date: Optional[str] = ""
    weightage: Optional[str] = ""

class MonthlySampleCreate(MonthlySampleBase):
    pass

class MonthlySampleUpdate(MonthlySampleBase):
    id: int

class MasterDispatchBase(BaseModel):
    file_name: str
    sheet_name: str
    sampno: str
    sampno_raw: Optional[str] = None
    year_prefix: int
    group_letter: str
    sample_no: int
    recdate_iso: Optional[str] = None
    sampdate_iso: Optional[str] = None
    type: Optional[str] = ""
    namecd: Optional[str] = ""
    sender_name: Optional[str] = ""
    distocd: Optional[int] = None
    distoname: Optional[str] = ""
    placecd: Optional[str] = ""
    placenm: Optional[str] = ""
    sampname: str
    batchno: str
    licence: Optional[str] = ""
    mfgname: Optional[str] = ""
    mfgadd1: Optional[str] = ""
    mfgadd2: Optional[str] = ""
    mfgadd3: Optional[str] = ""
    distcd: Optional[str] = ""
    statecd: Optional[str] = ""
    testrepo_q: Optional[str] = "Q"
    testrepo_quarter: Optional[int] = 1
    testrepo_no: Optional[str] = ""
    testrepo_yyyy: Optional[int] = 2026
    testrepo_group: Optional[str] = ""
    testdate_iso: Optional[str] = None
    result: Optional[int] = 1 # 1: Standard, 2: NSQ
    nsq: Optional[str] = ""
    det1_nsq: Optional[str] = ""
    fees: Optional[str] = "NIL"
    ar_report_no: Optional[str] = ""
    ar_report_date_iso: Optional[str] = None
    di_memo_no: Optional[str] = ""
    di_memo_date_iso: Optional[str] = None
    govt_analyst: Optional[str] = ""
    extra_fees: Optional[str] = ""
    monthly_sample_id: Optional[int] = None

class MasterDispatchCreate(MasterDispatchBase):
    pass

class MasterDispatchUpdate(MasterDispatchBase):
    id: int

class ManufacturerModel(BaseModel):
    id: Optional[int] = None
    short_name_alias: str
    licence: str
    mfgname: str
    mfgadd1: Optional[str] = ""
    mfgadd2: Optional[str] = ""
    mfgadd3: Optional[str] = ""
    distcd: Optional[str] = ""
    statecd: Optional[str] = ""

class InspectorModel(BaseModel):
    id: Optional[int] = None
    inspector_name: str
    default_district_name: Optional[str] = ""
    default_district_code: Optional[int] = None

class NewMonthFileRequest(BaseModel):
    month_name: str
    year: int

class WorkspaceConfigRequest(BaseModel):
    workspace_folder_path: str
