"""
HIS (Hospital Information System) 医院信息系统对接
支持：HL7 v2.x消息解析、FHIR R4标准API、DICOM影像集成
用于实现与医院系统的数据互通和业务协同
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class HL7MessageType(Enum):
    """HL7消息类型"""
    ADT = "ADT"       # 入院/转科/出院
    ORM = "ORM"       # 检验/检查申请
    ORU = "ORU"       # 检验/检查结果
    DFT = "DFT"       # 财务/账单
    MDM = "MDM"       # 病历文档
    PPR = "PPR"       # 患者问题列表
    VXU = "VXU"       # 疫苗接种


class FHIRResourceType(Enum):
    """FHIR资源类型"""
    PATIENT = "Patient"
    OBSERVATION = "Observation"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    CONDITION = "Condition"
    MEDICATION_REQUEST = "MedicationRequest"
    ENCOUNTER = "Encounter"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    CARE_PLAN = "CarePlan"


@dataclass
class HISConnectionConfig:
    """HIS系统连接配置"""
    
    # 连接基本信息
    his_name: str = "Default Hospital"
    endpoint_url: str = ""
    fhir_base_url: str = ""              # FHIR REST API基础地址
    
    # 认证信息
    auth_type: str = "basic"             # basic/oauth2/api_key
    username: str = ""
    password: str = ""
    api_key: str = ""
    oauth_token_url: str = ""
    
    # HL7配置（MLLP协议）
    mllp_host: str = ""
    mllp_port: int = 2575
    sending_facility: str = "ZHIHEALTH"
    receiving_facility: str = "HIS"
    
    # 超时设置
    connection_timeout: int = 30
    read_timeout: int = 60
    
    # 数据映射配置
    patient_id_prefix: str = "ZH"        # ZhiHealth患者ID前缀
    
    @classmethod
    def from_env(cls) -> 'HISConnectionConfig':
        """从环境变量加载"""
        import os
        
        return cls(
            his_name=os.getenv('HIS_NAME', 'Default Hospital'),
            endpoint_url=os.getenv('HIS_ENDPOINT_URL', ''),
            fhir_base_url=os.getenv('HIS_FHIR_BASE_URL', ''),
            auth_type=os.getenv('HIS_AUTH_TYPE', 'basic'),
            username=os.getenv('HIS_USERNAME', ''),
            password=os.getenv('HIS_PASSWORD', ''),
            api_key=os.getenv('HIS_API_KEY', ''),
            mllp_host=os.getenv('HIS_MLLP_HOST', ''),
            mllp_port=int(os.getenv('HIS_MLLP_PORT', '2575')),
            sending_facility=os.getenv('HIS_SENDING_FACILITY', 'ZHIHEALTH'),
            receiving_facility=os.getenv('HIS_RECEIVING_FACILITY', 'HIS')
        )


@dataclass
class PatientRecord:
    """患者记录（标准化格式）"""
    external_id: str                     # HIS系统中的患者ID
    internal_id: str                     # ZhiHealth内部ID
    
    name: str = ""
    gender: str = ""
    birth_date: Optional[str] = None
    phone: str = ""
    id_card: str = ""
    
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    
    # 医疗信息
    blood_type: Optional[str] = None
    allergies: List[str] = field(default_factory=list)
    chronic_diseases: List[str] = field(default_factory=list)
    
    # 同步状态
    last_sync_time: Optional[str] = None
    sync_status: str = "synced"          # synced/pending/conflict/error


class HL7Parser:
    """
    HL7 v2.x消息解析器
    支持消息的构建、解析和验证
    """
    
    SEGMENT_DELIMITER = '|'
    FIELD_DELIMITER = '^'
    COMPONENT_DELIMITER = '&'
    SUBCOMPONENT_DELIMITER = '&'
    REPETITION_DELIMITER = '~'
    ESCAPE_CHAR = '\\'
    
    @staticmethod
    def parse_message(raw_hl7: str) -> Dict[str, Any]:
        """
        解析原始HL7消息为结构化字典
        
        Args:
            raw_hl7: HL7原始消息字符串
            
        Returns:
            结构化字典，包含MSH、PID等段数据
        """
        lines = [line.strip() for line in raw_hl7.strip().split('\n') if line.strip()]
        
        if not lines or not lines[0].startswith('MSH'):
            raise ValueError("Invalid HL7 message: must start with MSH segment")
        
        message = {
            'raw': raw_hl7,
            'segments': {},
            'message_type': None,
            'message_control_id': None
        }
        
        for line in lines:
            parts = line.split(HL7Parser.SEGMENT_DELIMITER)
            segment_id = parts[0]
            
            message['segments'][segment_id] = {
                'fields': parts[1:],  # 去掉segment ID本身
                'raw_fields': parts
            }
            
            # 提取关键信息
            if segment_id == 'MSH':
                message['message_type'] = (
                    parts[8].split(HL7Parser.FIELD_DELIMITER)[0]
                    if len(parts) > 8 else None
                )
                message['message_control_id'] = parts[9] if len(parts) > 9 else None
            
            elif segment_id == 'PID':
                message['patient_info'] = HL7Parser._parse_pid_segment(parts)
                
        return message
    
    @staticmethod
    def _parse_pid_segment(fields: List[str]) -> Dict:
        """解析PID段（患者身份）"""
        pid_data = {}
        
        try:
            # PID-3: Patient Identifier List
            if len(fields) > 3:
                identifiers = fields[3].split(HL7Parser.REPETITION_DELIMITER)
                pid_data['identifiers'] = [
                    id.split(HL7Parser.COMPONENT_DELIMITER)[0] 
                    for id in identifiers if id
                ]
            
            # PID-5: Patient Name
            if len(fields) > 5:
                name_parts = fields[5].split(HL7Parser.COMPONENT_DELIMITER)
                pid_data['name'] = {
                    'family_name': name_parts[0] if len(name_parts) > 0 else '',
                    'given_name': name_parts[1] if len(name_parts) > 1 else ''
                }
            
            # PID-7: Date/Time of Birth
            if len(fields) > 7 and fields[7]:
                pid_data['birth_date'] = fields[7][:8]  # YYYYMMDD
            
            # PID-8: Administrative Sex
            if len(fields) > 8:
                sex_map = {'M': 'male', 'F': 'female', 'O': 'other'}
                pid_data['gender'] = sex_map.get(fields[8], fields[8])
            
            # PID-13: Phone Number - Home
            if len(fields) > 13:
                phone_parts = fields[13].split(HL7Parser.COMPONENT_DELIMITER)
                if phone_parts:
                    pid_data['phone_home'] = phone_parts[0].replace('-', '')
                    
        except Exception as e:
            logger.warning(f"PID段解析异常: {e}")
        
        return pid_data
    
    @staticmethod
    def build_adt_message(event_code: str, 
                         patient: PatientRecord,
                         control_id: Optional[str] = None) -> str:
        """
        构建ADT消息（入院/出院/转科）
        
        Args:
            event_code: A01(入院)/A02(转科)/A03(出院) 等
            patient: 患者记录
            control_id: 消息控制ID
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        ctrl_id = control_id or f"CTRL{int(datetime.now().timestamp())}"
        
        msg = (
            f"MSH|^~\\&|{HISConnectionConfig.sending_facility}|ZHIHEALTH_APP|"
            f"{HISConnectionConfig.receiving_facility}|HIS|{timestamp}||"
            f"ADT^{event_code}^ADT_A{event_code}|{ctrl_id}|P|2.5.1|||AL|AL|\n"
            f"PID|||{patient.external_id}^^^{HISConnectionConfig.patient_id_prefix}&ISO|"
            f"|{patient.name}^^^^^{patient.name}||{patient.birth_date or ''}|"
            f"{patient.gender.upper() if patient.gender else ''}|||||"
            f"{patient.phone}^^^^^PRN~PH|\n"
            f"PV1|1|I|^^^^^^^^^^^^^^^^||||||||||||||||"
            f"{patient.internal_id}^^^^visit_{ctrl_id}"
        )
        
        return msg


class FHIRClient:
    """
    FHIR R4标准REST客户端
    用于与现代HIS/EMR系统进行互操作
    """
    
    def __init__(self, config: Optional[HISConnectionConfig] = None):
        self.config = config or HISConnectionConfig.from_env()
        self._auth_token: Optional[str] = None
    
    def search_patient(self,
                      identifier: str = None,
                      name: str = None,
                      birth_date: str = None,
                      gender: str = None) -> Dict:
        """
        搜索FHIR Patient资源
        
        Args:
            identifier: 患者标识符
            name: 患者姓名
            birth_date: 出生日期 (YYYY-MM-DD)
            gender: 性别 male/female/other
            
        Returns:
            FHIR Bundle响应
        """
        params = {}
        
        if identifier:
            params['identifier'] = identifier
        if name:
            params['name'] = name
        if birth_date:
            params['birthdate'] = f'eq{birth_date}'
        if gender:
            params['gender'] = gender
        
        return self._fhir_request(
            method='GET',
            resource_type=FHIRResourceType.PATIENT.value,
            params=params
        )
    
    def get_patient(self, patient_id: str) -> Dict:
        """获取单个患者完整信息"""
        return self._fhir_request(
            method='GET',
            resource_type=FHIRResourceType.PATIENT.value,
            resource_id=patient_id
        )
    
    def create_observation(self, observation_data: Dict) -> Dict:
        """
        创建Observation资源（检验结果/生命体征）
        
        Args:
            observation_data: 符合FHIR规范的Observation数据
        """
        return self._fhir_request(
            method='POST',
            resource_type=FHIRResourceType.OBSERVATION.value,
            json_body=observation_data
        )
    
    def batch_create_observations(self, observations: List[Dict]) -> Dict:
        """批量创建Observation（使用FHIR Batch操作）"""
        bundle = {
            'resourceType': 'Bundle',
            'type': 'batch',
            'entry': [
                {
                    'request': {
                        'method': 'POST',
                        'url': f'{FHIRResourceType.OBSERVATION.value}'
                    },
                    'resource': obs
                }
                for obs in observations
            ]
        }
        
        return self._fhir_request(
            method='POST',
            url_suffix='',
            json_body=bundle
        )
    
    def query_observations(self,
                          patient_id: str,
                          code: str = None,
                          category: str = 'vital-signs',
                          date_from: str = None,
                          date_to: str = None,
                          count: int = 50) -> Dict:
        """
        查询患者的观察值（检验/体征数据）
        
        Args:
            patient_id: FHIR Patient ID
            code: LOINC编码筛选
            category: 类别 vital-signs/laboratory/survey
            date_from: 开始日期
            date_to: 结束日期
            count: 返回数量限制
        """
        params = {
            'subject': f'Patient/{patient_id}',
            'category': category,
            '_count': count,
            '_sort': '-date'
        }
        
        if code:
            params['code'] = code
        if date_from:
            params['date'] = f'ge{date_from}'
        if date_to:
            params['date'] = f'{params.get("date", "")}&le{date_to}'
        
        return self._fhir_request(
            method='GET',
            resource_type=FHIRResourceType.OBSERVATION.value,
            params=params
        )
    
    def create_encounter(self, encounter_data: Dict) -> Dict:
        """创建就诊记录（Encounter）"""
        return self._fhir_request(
            method='POST',
            resource_type=FHIRResourceType.ENCOUNTER.value,
            json_body=encounter_data
        )
    
    def get_diagnostic_reports(self,
                              patient_id: str,
                              category: str = None) -> Dict:
        """获取诊断报告"""
        params = {'subject': f'Patient/{patient_id}'}
        
        if category:
            params['category'] = category
        
        return self._fhir_request(
            method='GET',
            resource_type=FHIRResourceType.DIAGNOSTIC_REPORT.value,
            params=params
        )
    
    def _fhir_request(self,
                     method: str,
                     resource_type: str = None,
                     resource_id: str = None,
                     url_suffix: str = None,
                     params: Dict = None,
                     json_body: Dict = None) -> Dict:
        """
        执行FHIR REST请求
        
        Args:
            method: HTTP方法 GET/POST/PUT/DELETE
            resource_type: 资源类型
            resource_id: 资源ID
            url_suffix: URL后缀
            params: 查询参数
            json_body: JSON请求体
        """
        import requests
        
        base_url = self.config.fhir_base_url.rstrip('/')
        
        # 构建URL
        url_parts = []
        if resource_type:
            url_parts.append(resource_type)
        if resource_id:
            url_parts.append(resource_id)
        if url_suffix:
            url_parts.append(url_suffix)
        
        url = f"{base_url}/{'/'.join(url_parts)}"
        
        headers = {
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json'
        }
        
        # 添加认证头
        if self.config.auth_type == 'api_key':
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        elif self.config.auth_type == 'basic':
            import base64
            credentials = base64.b64encode(
                f'{self.config.username}:{self.config.password}'.encode()
            ).decode()
            headers['Authorization'] = f'Basic {credentials}'
        elif self._auth_token:
            headers['Authorization'] = f'Bearer {self._auth_token}'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=self.config.read_timeout
            )
            
            result = response.json()
            
            # 处理OperationOutcome错误
            if result.get('resourceType') == 'OperationOutcome':
                issues = result.get('issue', [])
                error_msg = '; '.join([
                    issue.get('diagnostics', issue.get('details', {}).get('text', 'Unknown'))
                    for issue in issues
                ])
                logger.error(f"[FHIR] 操作失败: {error_msg}")
                return {'success': False, 'error': error_msg, 'issues': issues}
            
            logger.debug(f"[FHIR] {method} {url} -> {response.status_code}")
            return {'success': True, 'data': result, 'status_code': response.status_code}
            
        except requests.exceptions.Timeout:
            logger.error(f"[FHIR] 请求超时: {url}")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[FHIR] 连接失败: {e}")
            return {'success': False, 'error': f'Connection error: {str(e)}'}
        except Exception as e:
            logger.error(f"[FHIR] 请求异常: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


class HISDataSynchronizer:
    """
    HIS数据同步器
    实现ZhiHealth与HIS系统之间的双向数据同步
    """
    
    def __init__(self, 
                 fhir_client: Optional[FHIRClient] = None,
                 config: Optional[HISConnectionConfig] = None):
        self.fhir_client = fhir_client or FHIRClient(config)
        self.config = config or HISConnectionConfig.from_env()
        
        # 同步日志
        self.sync_history: List[Dict] = []
    
    def push_health_data_to_his(self,
                               user_id: int,
                               health_records: List[Dict],
                               batch_size: int = 20) -> Dict:
        """
        将ZhiHealth健康数据推送到HIS系统（转为FHIR Observation）
        
        Args:
            user_id: ZhiHealth用户ID
            health_records: 健康数据记录列表
            batch_size: 批量大小
            
        Returns:
            同步结果统计
        """
        results = {
            'total_records': len(health_records),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'sync_time': datetime.now().isoformat()
        }
        
        # 分批处理
        for i in range(0, len(health_records), batch_size):
            batch = health_records[i:i + batch_size]
            
            # 转换为FHIR Observation格式
            fhir_observations = [
                self._convert_to_fhir_observation(record, user_id)
                for record in batch
            ]
            
            # 批量提交
            response = self.fhir_client.batch_create_observations(fhir_observations)
            
            if response.get('success'):
                results['successful'] += len(batch)
            else:
                results['failed'] += len(batch)
                results['errors'].append({
                    'batch_start': i,
                    'error': response.get('error', 'Unknown')
                })
        
        # 记录同步历史
        self.sync_history.append(results)
        
        logger.info(f"[HIS Sync] 数据推送完成 | 成功: {results['successful']} | "
                   f"失败: {results['failed']} | 总计: {results['total_records']}")
        
        return results
    
    def pull_patient_data_from_his(self, 
                                  his_patient_id: str) -> Optional[PatientRecord]:
        """
        从HIS拉取患者数据到ZhiHealth
        
        Args:
            his_patient_id: HIS系统中的患者ID
            
        Returns:
            标准化的患者记录
        """
        try:
            # 获取患者基本信息
            patient_response = self.fhir_client.get_patient(his_patient_id)
            
            if not patient_response.get('success'):
                logger.error(f"[HIS Pull] 获取患者信息失败: {patient_response.get('error')}")
                return None
            
            fhir_patient = patient_response['data']
            
            # 转换为内部格式
            record = self._convert_fhir_to_internal(fhir_patient)
            
            # 获取最近的检验/体征数据
            obs_response = self.fhir_client.query_observations(
                patient_id=his_patient_id,
                count=100
            )
            
            if obs_response.get('success'):
                record['_recent_observations'] = obs_response['data'].get('entry', [])
            
            logger.info(f"[HIS Pull] 患者数据拉取成功 | ID: {his_patient_id}")
            return record
            
        except Exception as e:
            logger.error(f"[HIS Pull] 数据拉取异常: {e}", exc_info=True)
            return None
    
    def _convert_to_fhir_observation(self, 
                                    health_record: Dict,
                                    user_id: int) -> Dict:
        """
        将ZhiHealth健康记录转换为FHIR Observation资源
        
        Args:
            health_record: 内部健康数据格式
            user_id: 用户ID
            
        Returns:
            FHIR Observation字典
        """
        data_type = health_record.get('data_type', 'unknown')
        
        loinc_mapping = {
            'heart_rate': ('8867-4', 'Heart rate', 'beats/min'),
            'blood_pressure_systolic': ('8480-6', 'Systolic blood pressure', 'mmHg'),
            'blood_pressure_diastolic': ('8462-4', 'Diastolic blood pressure', 'mmHg'),
            'body_temp': ('8310-5', 'Temperature', 'Cel'),
            'steps': ('41950-7', 'Number of steps in 24 hour Measured', ''),
            'sleep_hours': ('93802-2', 'Sleep duration - reported', 'h'),
            'weight': ('29463-7', 'Body weight', 'kg'),
            'blood_oxygen': ('59408-5', 'Oxygen saturation', '%'),
            'blood_glucose': ('41653-7', 'Glucose', 'mg/dL')
        }
        
        loinc_code, display_name, unit = loinc_mapping.get(data_type, 
                                                           ('unknown', data_type, ''))
        
        value_field = 'valueQuantity' if unit else 'valueString'
        value_value = {
            'value': health_record.get('value', 0),
            'unit': unit,
            'system': 'http://unitsofmeasure.org'
        } if unit else str(health_record.get('value', 'N/A'))
        
        observation = {
            'resourceType': 'Observation',
            'status': 'final',
            'category': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'vital-signs',
                    'display': 'Vital Signs'
                }]
            }],
            'code': {
                'coding': [{
                    'system': 'http://loinc.org',
                    'code': loinc_code,
                    'display': display_name
                }],
                'text': display_name
            },
            'subject': {
                'reference': f'Patient/ZH{user_id}',
                'display': f'ZhiHealth User {user_id}'
            },
            value_field: value_value,
            'effectiveDateTime': health_record.get('collect_time', datetime.now().isoformat()),
            'issued': datetime.now().isoformat()
        }
        
        # 添加设备信息
        if health_record.get('source') == 'wearable':
            observation['device'] = {
                'reference': 'Device/wearable-device-001',
                'display': 'Smart Wearable Device'
            }
        
        return observation
    
    def _convert_fhir_to_internal(self, fhir_patient: Dict) -> PatientRecord:
        """将FHIR Patient转换为内部格式"""
        name_entry = fhir_patient.get('name', [{}])[0] if fhir_patient.get('name') else {}
        
        gender_map = {
            'male': '男', 'female': '女', 'other': '其他', 'unknown': '未知'
        }
        
        telecom = fhir_patient.get('telecom', [])
        phone = next(
            (t.get('value', '') for t in telecom if t.get('system') == 'phone'), 
            ''
        )
        
        return PatientRecord(
            external_id=fhir_patient.get('id', ''),
            internal_id=f"ZH_{datetime.now().timestamp():.0f}",
            name=f"{name_entry.get('given', [''])[0]} {name_entry.get('family', '')}".strip(),
            gender=gender_map.get(fhir_patient.get('gender', ''), fhir_patient.get('gender', '')),
            birth_date=fhir_patient.get('birthDate'),
            phone=phone,
            last_sync_time=datetime.now().isoformat()
        )


# 全局实例
_fhir_client: Optional[FHIRClient] = None
_his_synchronizer: Optional[HISDataSynchronizer] = None

def get_fhir_client(config: Optional[HISConnectionConfig] = None) -> FHIRClient:
    global _fhir_client
    if _fhir_client is None:
        _fhir_client = FHIRClient(config)
    return _fhir_client

def get_his_synchronizer(config: Optional[HISConnectionConfig] = None) -> HISDataSynchronizer:
    global _his_synchronizer
    if _his_synchronizer is None:
        _his_synchronizer = HISDataSynchronizer(config=config)
    return _his_synchronizer