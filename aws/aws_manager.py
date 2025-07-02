#!/usr/bin/env python3
"""
AWS 통신 중앙 관리 모듈
S3와 DynamoDB와의 모든 통신을 담당하는 핵심 모듈입니다.
"""

import boto3
import json
import os
from datetime import datetime, timezone
from typing import Any, List, Dict
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
import mimetypes
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSManager:
    """AWS 리소스 관리 클래스"""
    
    def __init__(self, region_name: str = 'ap-northeast-2', profile_name: str = None):
        """
        AWS Manager 초기화
        
        Args:
            region_name: AWS 리전명
            profile_name: AWS 프로필명 (None이면 기본 프로필)
        """
        self.region_name = region_name
        self.profile_name = profile_name
    
        
        # 클라이언트 초기화
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region_name)
        
        # 설정 로드
        self.config = self._load_config()
        self.bucket_name = self.config.get('s3', {}).get('bucket_name', 'sw-fashion-image-data')
        self.table_name = self.config.get('dynamodb', {}).get('table_name', 'ProductAssets')
        
        if not self.bucket_name:
            raise ValueError("S3 버킷 이름이 설정되지 않았습니다. config.json을 확인해주세요.")
        
        logger.info(f"AWS Manager 초기화 완료 - 리전: {region_name}, 버킷: {self.bucket_name}, 테이블: {self.table_name}")
    
    def _load_config(self) -> dict[str, Any]:
        """설정 파일을 로드합니다."""
        # boto3/config.json 파일 찾기
        #TODO : 파일경로 주의 필요
        config_path = Path(__file__).parent / 'config.json'
        
        # 현재 디렉토리에서 boto3/config.json도 시도
        if not config_path.exists():
            config_path = Path('boto3') / 'config.json'
        
        # 현재 디렉토리의 config.json도 시도
        if not config_path.exists():
            config_path = Path('config.json')
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 JSON 형식 오류: {e}")
            return {}
    
    def _get_current_timestamp(self) -> str:
        """현재 시각을 ISO 8601 형식으로 반환합니다."""
        return datetime.now(timezone.utc).isoformat()
    
    def _convert_dynamodb_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        DynamoDB client 응답 아이템을 일반 딕셔너리로 변환합니다.
        
        Args:
            item: DynamoDB에서 쿼리 반환결과인 Item 키에 대한 데이터 (타입 정보 포함)
            
        Returns:
            dict: 변환된 일반 딕셔너리
        """
        converted = {}
        for key, value in item.items():
            if 'S' in value:  # String
                converted[key] = value['S']
            elif 'N' in value:  # Number
                # 정수로 변환 시도, 실패하면 float
                try:
                    converted[key] = int(value['N'])
                except ValueError:
                    converted[key] = float(value['N'])
            elif 'SS' in value:  # String Set
                converted[key] = value['SS']
            elif 'NS' in value:  # Number Set
                converted[key] = [int(n) for n in value['NS']]
            elif 'BOOL' in value:  # Boolean
                converted[key] = value['BOOL']
            elif 'NULL' in value:  # Null
                converted[key] = None
            elif 'M' in value:  # Map
                converted[key] = self._convert_dynamodb_item(value['M'])
            elif 'L' in value:  # List
                # List 내부 아이템들을 변환
                converted_list = []
                for list_item in value['L']:
                    if 'S' in list_item:  # String 아이템
                        converted_list.append(list_item['S'])
                    else:
                        # 다른 타입의 아이템은 재귀 변환
                        converted_list.append(self._convert_dynamodb_item({'item': list_item})['item'])
                converted[key] = converted_list
            else:
                # 알 수 없는 타입은 그대로 유지
                converted[key] = value
        
        # JSON 문자열 필드들 파싱
        json_fields = ['product_info', 'representative_assets']
        for field in json_fields:
            if field in converted and isinstance(converted[field], str):
                try:
                    converted[field] = json.loads(converted[field])
                except json.JSONDecodeError:
                    pass
                
        return converted
    
    def _get_s3_object_key(self, main_category: str, sub_category: int, product_id: str, relative_path: str) -> str:
        """
        S3 객체 키를 생성합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            relative_path: 상대 경로 (예: 'detail/0.jpg', 'meta.json')
            
        Returns:
            str: S3 객체 키 (예: 'main_category/1005/79823/detail/0.jpg')
        """
        return f"{main_category}/{sub_category}/{product_id}/{relative_path}"
    
    # =============================================================================
    # S3 관련 함수들
    # =============================================================================
    
    def upload_file_to_s3(self, local_file_path: str, s3_key: str, 
                          metadata: dict[str, str]|None = None,
                          tags: dict[str, str]|None = None) -> bool:
        """
        로컬 파일을 S3에 업로드합니다.
        
        Args:
            local_file_path: 로컬 파일 경로
            s3_key: S3 객체 키
            metadata: 파일 메타데이터
            tags: S3 객체 태그
            
        Returns:
            bool: 업로드 성공 여부
        """
        try:
            # MIME 타입 추론
            content_type, _ = mimetypes.guess_type(local_file_path)
            if content_type is None:
                content_type = 'binary/octet-stream'
            
            extra_args = {
                'ContentType': content_type
            }
            
            # 메타데이터 추가
            if metadata:
                extra_args['Metadata'] = metadata
            
            # 파일 업로드
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # 태그 추가 (별도 API 호출 필요)
            if tags:
                self.tag_s3_object(s3_key, tags)
            
            logger.info(f"S3 업로드 성공: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 업로드 실패 {s3_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"S3 업로드 중 예상치 못한 오류 {s3_key}: {e}")
            return False
    

    
    def tag_s3_object(self, s3_key: str, tags: dict[str, str]) -> bool:
        """
        S3 객체에 태그를 지정합니다.
        
        Args:
            s3_key: S3 객체 키
            tags: 태그 딕셔너리
            
        Returns:
            bool: 태그 지정 성공 여부
        """
        try:
            tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
            
            self.s3_client.put_object_tagging(
                Bucket=self.bucket_name,
                Key=s3_key,
                Tagging={'TagSet': tag_set}
            )
            
            logger.info(f"S3 객체 태그 지정 성공: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 객체 태그 지정 실패 {s3_key}: {e}")
            return False
    
    def move_s3_object(self, source_key: str, dest_key: str) -> bool:
        """
        S3 객체를 이동합니다 (복사 후 삭제).
        
        Args:
            source_key: 원본 객체 키
            dest_key: 대상 객체 키
            
        Returns:
            bool: 이동 성공 여부
        """
        try:
            # 객체 복사
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )
            
            # 원본 객체 삭제
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=source_key)
            
            logger.info(f"S3 객체 이동 성공: {source_key} -> {dest_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 객체 이동 실패 {source_key} -> {dest_key}: {e}")
            return False
    
    def batch_move_s3_objects(self, move_operations: list[tuple[str, str]]) -> dict[str, bool]:
        """
        여러 S3 객체를 배치로 이동합니다.
        
        Args:
            move_operations: 이동 작업 목록 [(source_key, dest_key), ...]
            
        Returns:
            Dict[str, bool]: 각 이동 작업의 성공/실패 결과 {source_key: success}
        """
        results = {}
        
        for source_key, dest_key in move_operations:
            try:
                success = self.move_s3_object(source_key, dest_key)
                results[source_key] = success
                
                if success:
                    logger.info(f"배치 이동 성공: {source_key} -> {dest_key}")
                else:
                    logger.error(f"배치 이동 실패: {source_key} -> {dest_key}")
                    
            except Exception as e:
                logger.error(f"배치 이동 중 예외 발생 {source_key}: {e}")
                results[source_key] = False
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(move_operations)
        
        logger.info(f"배치 이동 완료: {success_count}/{total_count} 성공")
        return results
    
    def get_meta_json(self, main_category: str, sub_category: int, product_id: str) -> dict[str, Any]|None:
        """
        제품의 meta.json 파일을 다운로드하고 파싱합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            
        Returns:
            Optional[Dict[str, Any]]: meta.json 내용 (실패 시 None)
        """
        try:
            meta_key = f"{main_category}/{sub_category}/{product_id}/meta.json"
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=meta_key)
            content = response['Body'].read().decode('utf-8')
            
            # JSON 파싱
            meta_data = json.loads(content)
            
            logger.info(f"meta.json 다운로드 성공: {product_id}")
            return meta_data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"meta.json 파일이 없습니다: {product_id}")
            else:
                logger.error(f"meta.json 다운로드 실패 {product_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"meta.json JSON 파싱 실패 {product_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"meta.json 처리 중 예상치 못한 오류 {product_id}: {e}")
            return None

    def delete_s3_object(self, s3_key: str) -> bool:
        """
        S3 객체를 삭제합니다.
        
        Args:
            s3_key: 삭제할 객체 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"S3 객체 삭제 성공: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 객체 삭제 실패 {s3_key}: {e}")
            return False
    
    # =============================================================================
    # DynamoDB 관련 함수들
    # =============================================================================
    
    def create_product_item(self, main_category: str, sub_category: int, product_id: str, 
                           file_lists: dict[str, list[str]] = None) -> tuple[bool, bool]:
        """
        DynamoDB에 제품 아이템을 생성하거나 업데이트합니다.
        기존 아이템이 있으면 덮어쓰고, 없으면 새로 생성합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            file_lists: 폴더별 파일 리스트 (선택적)
            
        Returns:
            tuple[bool, bool]: (처리 성공 여부, 새 제품 여부)
        """
        try:
            # 먼저 기존 아이템 존재 여부 확인
            existing_item = self.get_product_detail(sub_category, product_id)
            is_new_product = existing_item is None
            
            current_time = self._get_current_timestamp()
            
            # DynamoDB client용 아이템 구성 (타입 명시 필요)
            item = {
                'main_category': {'S': main_category},
                'sub_category': {'N': str(sub_category)}, # 파티션 키 
                'product_id': {'S': product_id}, # 정렬 키 
                'current_status': {'S': 'PENDING'}, # GSI 인덱스의 파티션 키 
                'last_updated_at': {'S': current_time}, # GSI 인덱스의 정렬 키 
            }
            
            # 새 제품이면 created_at 추가, 기존 제품이면 생략 (기존 값 유지)
            if is_new_product:
                item['created_at'] = {'S': current_time}
            
            # 파일 리스트 추가 (빈 리스트 포함)
            if file_lists:
                supported_folders = ['detail', 'summary', 'segment', 'text']
                for folder in supported_folders:
                    if folder in file_lists:
                        # 파일명 리스트를 DynamoDB List로 저장 (빈 리스트 허용)
                        string_list = [{'S': filename} for filename in file_lists[folder]]
                        item[folder] = {'L': string_list}
            
            self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=item
            )
            
            if is_new_product:
                logger.info(f"DynamoDB 새 아이템 생성 완료: {main_category}-{sub_category}-{product_id}")
            else:
                logger.info(f"DynamoDB 기존 아이템 업데이트 완료: {main_category}-{sub_category}-{product_id}")
            
            if file_lists:
                logger.debug(f"파일 리스트 포함하여 저장: {file_lists}")
            
            return True, is_new_product
            
        except ClientError as e:
            logger.error(f"DynamoDB 아이템 처리 실패 {main_category}-{sub_category}-{product_id}: {e}")
            return False, False
    
    def get_product_list(self, sub_category: int, limit: int = 50, 
                        exclusive_start_key: dict[str, Any]|None = None) -> tuple[list[dict[str, Any]], dict[str, Any]|None]:
        """
        특정 카테고리의 상품 목록을 페이지 단위로 가져옵니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            limit: 한 번에 가져올 아이템 수
            exclusive_start_key: 페이지네이션을 위한 시작 키
            
        Returns:
            Tuple[List[Dict], Optional[Dict]]: (아이템 리스트, 다음 페이지 키)
        """
        try:
            query_params = {
                'TableName': self.table_name,
                'KeyConditionExpression': 'sub_category = :sub_category',
                'ExpressionAttributeValues': {
                    ':sub_category': {'N': str(sub_category)}
                },
                'Limit': limit,
                'ScanIndexForward': True  # 오름차순 정렬
            }
            
            if exclusive_start_key:
                query_params['ExclusiveStartKey'] = exclusive_start_key
            
            response = self.dynamodb_client.query(**query_params)
            
            # DynamoDB client 응답을 일반 딕셔너리로 변환
            items = []
            for item in response.get('Items', []):
                converted_item = self._convert_dynamodb_item(item)
                items.append(converted_item)
                
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"DynamoDB 상품 목록 조회 완료: 카테고리 {sub_category}, 개수: {len(items)}")
            return items, next_key
            
        except ClientError as e:
            logger.error(f"DynamoDB 상품 목록 조회 실패 카테고리 {sub_category}: {e}")
            return [], None
    
    def get_product_by_status(self, status: str, limit: int = 50,
                             exclusive_start_key: dict[str, Any]|None = None) -> tuple[list[dict[str, Any]], dict[str, Any]|None]:
        """
        특정 상태의 상품 목록을 GSI를 통해 조회합니다.
        
        Args:
            status: 큐레이션 상태 ('PENDING', 'COMPLETED')
            limit: 한 번에 가져올 아이템 수
            exclusive_start_key: 페이지네이션을 위한 시작 키
            
        Returns:
            Tuple[List[Dict], Optional[Dict]]: (아이템 리스트, 다음 페이지 키)
        """
        try:
            query_params = {
                'TableName': self.table_name,
                'IndexName': 'CurrentStatus-LastUpdatedAt-GSI',
                'KeyConditionExpression': 'current_status = :status',
                'ExpressionAttributeValues': {
                    ':status': {'S': status}
                },
                'Limit': limit,
                'ScanIndexForward': False  # 최신순 정렬
            }
            
            if exclusive_start_key:
                query_params['ExclusiveStartKey'] = exclusive_start_key
            
            response = self.dynamodb_client.query(**query_params)
            
            # DynamoDB client 응답을 일반 딕셔너리로 변환
            items = []
            for item in response.get('Items', []):
                converted_item = self._convert_dynamodb_item(item)
                items.append(converted_item)
                
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"DynamoDB 상태별 상품 조회 완료: 상태 {status}, 개수: {len(items)}")
            return items, next_key
            
        except ClientError as e:
            logger.error(f"DynamoDB 상태별 상품 조회 실패 상태 {status}: {e}")
            return [], None
    
    def update_curation_result(self, sub_category: int, product_id: str, 
                            curation_data: dict[str, Any], 
                            completed_by: str|None = None) -> bool:
        """
        DynamoDB에 큐레이션 결과를 업데이트합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            curation_data: 큐레이션 결과 데이터
            completed_by: 작업자 ID
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            current_time = self._get_current_timestamp()
            
            update_expression = "SET current_status = :status, last_updated_at = :timestamp"
            expression_values = {
                ':status': {'S': 'COMPLETED'},
                ':timestamp': {'S': current_time}
            }
            
            # 큐레이션 결과 추가
            if curation_data:
                update_expression += ", representative_assets = :assets"
                expression_values[':assets'] = {'S': json.dumps(curation_data, ensure_ascii=False)}
            
            # 작업자 정보 추가
            if completed_by:
                update_expression += ", completed_by = :completed_by"
                expression_values[':completed_by'] = {'S': completed_by}
            
            self.dynamodb_client.update_item(
                TableName=self.table_name,
                Key={
                    'sub_category': {'N': str(sub_category)},
                    'product_id': {'S': product_id}
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"DynamoDB 큐레이션 결과 업데이트 성공: {sub_category}-{product_id}")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB 큐레이션 결과 업데이트 실패 {sub_category}-{product_id}: {e}")
            return False
    
    def update_product_file_lists(self, sub_category: int, product_id: str, 
                                file_lists: dict[str, list[str]]) -> bool:
        """
        DynamoDB에 제품의 파일 리스트를 업데이트합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            file_lists: 폴더별 파일 리스트 {'detail': ['file1.jpg', 'file2.jpg'], 'summary': [...], ...}
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            current_time = self._get_current_timestamp()
            
            # 업데이트할 필드들 정의
            supported_folders = ['detail', 'summary', 'segment', 'text']
            
            update_expression_parts = ["last_updated_at = :timestamp"]
            expression_values = {':timestamp': {'S': current_time}}
            
            # 각 폴더별 파일 리스트 추가
            for folder in supported_folders:
                if folder in file_lists:
                    # 파일명 리스트를 DynamoDB List로 저장 (빈 리스트 허용)
                    update_expression_parts.append(f"{folder} = :{folder}")
                    string_list = [{'S': filename} for filename in file_lists[folder]]
                    expression_values[f':{folder}'] = {'L': string_list}
            
            if len(update_expression_parts) == 1:  # timestamp만 있는 경우
                logger.warning(f"업데이트할 파일 리스트가 없습니다: {sub_category}-{product_id}")
                return True
            
            update_expression = "SET " + ", ".join(update_expression_parts)
            
            self.dynamodb_client.update_item(
                TableName=self.table_name,
                Key={
                    'sub_category': {'N': str(sub_category)},
                    'product_id': {'S': product_id}
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"DynamoDB 파일 리스트 업데이트 성공: {sub_category}-{product_id}")
            logger.debug(f"업데이트된 파일 리스트: {file_lists}")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB 파일 리스트 업데이트 실패 {sub_category}-{product_id}: {e}")
            return False
    
    def get_product_file_lists(self, sub_category: int, product_id: str) -> dict[str, list[str]]:
        """
        DynamoDB에서 제품의 파일 리스트를 조회합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            
        Returns:
            Dict[str, List[str]]: 폴더별 파일 리스트
        """
        try:
            product_detail = self.get_product_detail(sub_category, product_id)
            
            if product_detail is None:
                logger.warning(f"제품을 찾을 수 없습니다: {sub_category}-{product_id}")
                return {}
            
            file_lists = {}
            supported_folders = ['detail', 'summary', 'segment', 'text']
            
            for folder in supported_folders:
                if folder in product_detail:
                    # DynamoDB에서 List로 저장된 데이터를 리스트로 변환
                    if isinstance(product_detail[folder], list):
                        file_lists[folder] = product_detail[folder]
                    else:
                        file_lists[folder] = []
            
            logger.info(f"파일 리스트 조회 성공: {sub_category}-{product_id}")
            return file_lists
            
        except Exception as e:
            logger.error(f"파일 리스트 조회 실패 {sub_category}-{product_id}: {e}")
            return {}
    
    def construct_s3_keys_from_file_lists(self, main_category: str, sub_category: int, 
                                        product_id: str, file_lists: dict[str, list[str]]) -> list[str]:
        """
        파일 리스트로부터 S3 객체 키들을 구성합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            file_lists: 폴더별 파일 리스트
            
        Returns:
            List[str]: S3 객체 키 리스트
        """
        s3_keys = []
        
        for folder, filenames in file_lists.items():
            for filename in filenames:
                s3_key = f"{main_category}/{sub_category}/{product_id}/{folder}/{filename}"
                s3_keys.append(s3_key)
        
        return s3_keys
    
    def get_product_detail(self, sub_category: int, product_id: str) -> dict[str, Any]|None:
        """
        특정 제품의 상세 정보를 조회합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            
        Returns:
            Optional[Dict]: 제품 정보 (없으면 None)
        """
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key={
                    'sub_category': {'N': str(sub_category)},
                    'product_id': {'S': product_id}
                }
            )
            
            item = response.get('Item')
            if item:
                # DynamoDB client 응답을 일반 딕셔너리로 변환
                converted_item = self._convert_dynamodb_item(item)
                logger.info(f"DynamoDB 제품 상세 조회 성공: {sub_category}-{product_id}")
                return converted_item
            else:
                logger.warning(f"DynamoDB 제품 없음: {sub_category}-{product_id}")
                return None
            
        except ClientError as e:
            logger.error(f"DynamoDB 제품 상세 조회 실패 {sub_category}-{product_id}: {e}")
            return None
    
    # =============================================================================
    # 카테고리 메타데이터 관리 함수들
    # =============================================================================
    
    def get_category_metadata(self) -> dict[str, Any]|None:
        """
        DynamoDB에서 카테고리 메타데이터를 조회합니다. 
        - 파티션 키인 sub_category는 0으로 고정되어 있고, 정렬키인 product_id는 CATEGORY_METADATA로 입력한경우 해당 table의 메타데이터를 조회합니다.
        - 메타데이터는 categories_info 항목에 저장되어 있습니다.
            - main_categories: 메인 카테고리 목록
            - sub_categories: 서브 카테고리 목록
            - product_counts: 카테고리별 제품 수
            - total_products: 총 제품 수
        Returns:
            Optional[Dict]: 카테고리 메타데이터 (없으면 None)
        """
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key={
                    'sub_category': {'N': '0'},  # 메타데이터 식별자
                    'product_id': {'S': 'CATEGORY_METADATA'}
                }
            )
            
            item = response.get('Item')
            if item:
                converted_item = self._convert_dynamodb_item(item)
                logger.info("카테고리 메타데이터 조회 성공")
                return converted_item
            else:
                logger.info("카테고리 메타데이터가 존재하지 않습니다")
                return None
                
        except ClientError as e:
            logger.error(f"카테고리 메타데이터 조회 실패: {e}")
            return None
    
    def update_category_metadata(self, categories_info: dict[str, Any]) -> bool:
        """
        DynamoDB에 카테고리 메타데이터를 업데이트합니다.
        
        Args:
            categories_info: 카테고리 정보 딕셔너리
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            current_time = self._get_current_timestamp()
            
            # 메타데이터 항목 구성 (다른 아이템들과 필드명 통일)
            item = {
                'sub_category': {'N': '0'},  # 메타데이터 식별자
                'product_id': {'S': 'CATEGORY_METADATA'},
                'categories_info': {'S': json.dumps(categories_info, ensure_ascii=False)},
                'last_updated_at': {'S': current_time}  # 다른 아이템들과 일관성 유지
            }
            
            self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=item
            )
            
            logger.info("카테고리 메타데이터 업데이트 성공")
            return True
            
        except ClientError as e:
            logger.error(f"카테고리 메타데이터 업데이트 실패: {e}")
            return False
    
    def collect_category_statistics_from_s3(self) -> dict[str, Any]:
        """
        S3에서 현재 존재하는 카테고리 구조와 제품 수를 수집합니다.
        
        Returns:
            Dict: 카테고리 통계 정보
        """
        try:
            categories_info = {
                "main_categories": [],
                "sub_categories": {},
                "product_counts": {},
                "total_products": 0
            }
            
            # 메인 카테고리 조회
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Delimiter='/'
            )
            
            for prefix in response.get('CommonPrefixes', []):
                main_category = prefix['Prefix'].rstrip('/')
                categories_info["main_categories"].append(main_category)
                categories_info["sub_categories"][main_category] = []
                categories_info["product_counts"][main_category] = {}
                
                # 서브 카테고리 조회
                sub_response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=f"{main_category}/",
                    Delimiter='/'
                )
                
                for sub_prefix in sub_response.get('CommonPrefixes', []):
                    try:
                        sub_category = int(sub_prefix['Prefix'].split('/')[-2])
                        categories_info["sub_categories"][main_category].append(sub_category)
                        
                        # 제품 수 조회
                        product_response = self.s3_client.list_objects_v2(
                            Bucket=self.bucket_name,
                            Prefix=f"{main_category}/{sub_category}/",
                            Delimiter='/'
                        )
                        
                        product_count = len(product_response.get('CommonPrefixes', []))
                        categories_info["product_counts"][main_category][str(sub_category)] = product_count
                        categories_info["total_products"] += product_count
                        
                    except ValueError:
                        logger.warning(f"서브 카테고리 ID가 숫자가 아닙니다: {sub_prefix['Prefix']}")
                        continue
                
                # 서브 카테고리 정렬
                categories_info["sub_categories"][main_category].sort()
            
            # 메인 카테고리 정렬
            categories_info["main_categories"].sort()
            
            logger.info(f"S3 카테고리 통계 수집 완료 - 총 제품 수: {categories_info['total_products']}")
            return categories_info
            
        except ClientError as e:
            logger.error(f"S3 카테고리 통계 수집 실패: {e}")
            return {}
    
    def get_main_categories(self) -> list[str]:
        """
        사용 가능한 메인 카테고리 목록을 조회합니다.
        
        Returns:
            List[str]: 메인 카테고리 목록
        """
        metadata = self.get_category_metadata()
        if metadata and 'categories_info' in metadata:
            categories_info = metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            return categories_info.get('main_categories', [])
        return []
    
    def get_sub_categories(self, main_category: str) -> list[int]:
        """
        특정 메인 카테고리의 서브 카테고리 목록을 조회합니다.
        
        Args:
            main_category: 메인 카테고리명
            
        Returns:
            List[int]: 서브 카테고리 목록
        """
        metadata = self.get_category_metadata()
        if metadata and 'categories_info' in metadata:
            categories_info = metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            return categories_info.get('sub_categories', {}).get(main_category, [])
        return []
    
    def get_product_counts_by_category(self) -> dict[str, dict[str, int]]:
        """
        카테고리별 제품 수를 조회합니다.
        
        Returns:
            Dict[str, Dict[str, int]]: 카테고리별 제품 수
        """
        metadata = self.get_category_metadata()
        if metadata and 'categories_info' in metadata:
            categories_info = metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            return categories_info.get('product_counts', {})
        return {}
    
    def increment_product_count(self, main_category: str, sub_category: int) -> bool:
        """
        특정 카테고리의 제품 수를 1 증가시킵니다.
        메타데이터가 미리 초기화되어 있어야 합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 현재 메타데이터 조회
            metadata = self.get_category_metadata()
            
            if metadata is None:
                logger.error("카테고리 메타데이터가 없습니다. 먼저 초기화해야 합니다.")
                return False
            
            categories_info = metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            
            # 메인 카테고리가 없으면 추가
            if main_category not in categories_info["main_categories"]:
                categories_info["main_categories"].append(main_category)
                categories_info["main_categories"].sort()
                logger.info(f"새 메인 카테고리 추가: {main_category}")
            
            # 서브 카테고리 구조 초기화
            if main_category not in categories_info["sub_categories"]:
                categories_info["sub_categories"][main_category] = []
            if main_category not in categories_info["product_counts"]:
                categories_info["product_counts"][main_category] = {}
            
            # 서브 카테고리가 없으면 추가
            if sub_category not in categories_info["sub_categories"][main_category]:
                categories_info["sub_categories"][main_category].append(sub_category)
                categories_info["sub_categories"][main_category].sort()
                logger.info(f"새 서브 카테고리 추가: {main_category}-{sub_category}")
            
            # 제품 수 증가
            sub_category_str = str(sub_category)
            if sub_category_str not in categories_info["product_counts"][main_category]:
                categories_info["product_counts"][main_category][sub_category_str] = 0
            
            categories_info["product_counts"][main_category][sub_category_str] += 1
            categories_info["total_products"] += 1
            
            logger.debug(f"카테고리 제품 수 증가: {main_category}-{sub_category} -> {categories_info['product_counts'][main_category][sub_category_str]}개")
            
            # 메타데이터 업데이트
            return self.update_category_metadata(categories_info)
            
        except Exception as e:
            logger.error(f"제품 수 증가 실패 {main_category}-{sub_category}: {e}")
            return False
    
    def decrement_product_count(self, main_category: str, sub_category: int) -> bool:
        """
        특정 카테고리의 제품 수를 1 감소시킵니다.
        제품 삭제 시 사용됩니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 현재 메타데이터 조회
            metadata = self.get_category_metadata()
            
            if metadata is None:
                logger.error("카테고리 메타데이터가 없습니다.")
                return False
            
            categories_info = metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            
            # 카테고리 존재 확인
            if main_category not in categories_info.get("main_categories", []):
                logger.warning(f"존재하지 않는 메인 카테고리: {main_category}")
                return False
            
            if sub_category not in categories_info.get("sub_categories", {}).get(main_category, []):
                logger.warning(f"존재하지 않는 서브 카테고리: {main_category}-{sub_category}")
                return False
            
            # 제품 수 감소
            sub_category_str = str(sub_category)
            current_count = categories_info.get("product_counts", {}).get(main_category, {}).get(sub_category_str, 0)
            
            if current_count <= 0:
                logger.warning(f"이미 제품 수가 0입니다: {main_category}-{sub_category}")
                return False
            
            categories_info["product_counts"][main_category][sub_category_str] -= 1
            categories_info["total_products"] -= 1
            
            logger.info(f"카테고리 제품 수 감소: {main_category}-{sub_category} -> {categories_info['product_counts'][main_category][sub_category_str]}개")
            
            # 해당 서브 카테고리에 제품이 없으면 서브 카테고리 제거 (선택사항)
            if categories_info["product_counts"][main_category][sub_category_str] == 0:
                logger.info(f"서브 카테고리 {main_category}-{sub_category}에 제품이 없어짐")
                # 필요하다면 여기서 서브 카테고리를 완전히 제거할 수도 있음
                # categories_info["sub_categories"][main_category].remove(sub_category)
                # del categories_info["product_counts"][main_category][sub_category_str]
            
            # 메타데이터 업데이트
            return self.update_category_metadata(categories_info)
            
        except Exception as e:
            logger.error(f"제품 수 감소 실패 {main_category}-{sub_category}: {e}")
            return False
    
    # =============================================================================
    # 유틸리티 함수들
    # =============================================================================
    
    def test_connection(self) -> dict[str, bool]:
        """
        AWS 연결 상태를 테스트합니다.
        
        Returns:
            Dict[str, bool]: 각 서비스별 연결 상태
        """
        results = {}
        
        # S3 연결 테스트
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            results['s3'] = True
            logger.info("S3 연결 테스트 성공")
        except ClientError:
            results['s3'] = False
            logger.error("S3 연결 테스트 실패")
        
        # DynamoDB 연결 테스트
        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            results['dynamodb'] = True
            logger.info("DynamoDB 연결 테스트 성공")
        except ClientError:
            results['dynamodb'] = False
            logger.error("DynamoDB 연결 테스트 실패")
        
        return results
    
    def get_statistics(self) -> dict[str, Any]:
        """
        프로젝트 통계 정보를 조회합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        try:
            # DynamoDB 테이블 정보
            table_info = self.dynamodb_client.describe_table(TableName=self.table_name)
            item_count = table_info['Table'].get('ItemCount', 0)
            
            # 상태별 카운트 (GSI 사용)
            status_counts = {}
            for status in ['PENDING', 'COMPLETED']:
                items, _ = self.get_product_by_status(status, limit=1000)  # 대략적인 카운트
                status_counts[status] = len(items)
            
            stats = {
                'total_products': item_count,
                'status_breakdown': status_counts,
                'last_updated': self._get_current_timestamp()
            }
            
            logger.info(f"통계 정보 조회 완료: {stats}")
            return stats
            
        except ClientError as e:
            logger.error(f"통계 정보 조회 실패: {e}")
            return {}



    def batch_get_product_images_from_data(self, main_category: str, sub_category: int, 
                                          product_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        이미 가져온 제품 데이터에서 직접 파일 리스트를 추출하여 이미지 정보를 배치로 수집합니다.
        DynamoDB 추가 호출 없이 pagination으로 가져온 데이터를 활용하여 S3 키를 구성합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_data_list: 이미 조회된 제품 데이터 목록 (DynamoDB에서 가져온 데이터)
            
        Returns:
            List[Dict]: 다운로드 작업 목록 [{'product_id': str, 'folder': str, 'filename': str, 'url': str}]
        """
        download_tasks = []
        
        try:
            # 지원하는 폴더명들
            supported_folders = ['detail', 'summary', 'segment', 'text']
            
            for product_data in product_data_list:
                try:
                    product_id = product_data.get('product_id')
                    if not product_id:
                        logger.warning("제품 데이터에 product_id가 없습니다.")
                        continue
                    
                    # 각 폴더별로 파일 리스트 추출
                    for folder in supported_folders:
                        filenames = product_data.get(folder, [])
                        
                        # 빈 리스트인 경우 건너뛰기
                        if not filenames or not isinstance(filenames, list):
                            continue
                        
                        # 각 파일명에 대해 S3 키 구성 및 Presigned URL 생성
                        for filename in filenames:
                            if not filename:  # 빈 문자열 체크
                                continue
                                
                            # S3 키 구성: main_category/sub_category/product_id/folder/filename
                            s3_key = f"{main_category}/{sub_category}/{product_id}/{folder}/{filename}"
                            
                            try:
                                # Presigned URL 생성 (1시간 유효)
                                url = self.s3_client.generate_presigned_url(
                                    'get_object',
                                    Params={'Bucket': self.bucket_name, 'Key': s3_key},
                                    ExpiresIn=3600
                                )
                                
                                download_tasks.append({
                                    'product_id': product_id,
                                    'folder': folder,
                                    'filename': filename,
                                    'url': url,
                                    'key': s3_key
                                })
                                
                            except ClientError as e:
                                logger.warning(f"Presigned URL 생성 실패 {s3_key}: {e}")
                                continue
                    
                    # meta.json 파일도 다운로드 태스크에 추가
                    meta_json_key = f"{main_category}/{sub_category}/{product_id}/meta.json"
                    try:
                        # meta.json Presigned URL 생성 (1시간 유효)
                        meta_url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': self.bucket_name, 'Key': meta_json_key},
                            ExpiresIn=3600
                        )
                        
                        download_tasks.append({
                            'product_id': product_id,
                            'folder': 'meta',  # meta.json을 구분하기 위한 특별한 폴더명
                            'filename': 'meta.json',
                            'url': meta_url,
                            'key': meta_json_key
                        })
                        
                    except ClientError as e:
                        logger.debug(f"meta.json Presigned URL 생성 실패 {meta_json_key}: {e}")
                        # meta.json은 필수가 아니므로 경고만 남기고 계속 진행
                    
                    logger.debug(f"제품 {product_id} 이미지 수집 완료 (데이터 기반)")
                    
                except Exception as e:
                    logger.error(f"제품 데이터 처리 실패: {e}")
                    continue
            
            logger.info(f"배치 이미지 수집 완료 (데이터 기반): {len(product_data_list)}개 제품, {len(download_tasks)}개 이미지")
            return download_tasks
            
        except Exception as e:
            logger.error(f"배치 이미지 수집 중 오류 (데이터 기반): {e}")
            return []




# 전역 인스턴스 생성 함수
def create_aws_manager(region_name: str = 'ap-northeast-2', profile_name: str = None) -> AWSManager:
    """
    AWS Manager 인스턴스를 생성합니다.
    
    Args:
        region_name: AWS 리전명
        profile_name: AWS 프로필명
        
    Returns:
        AWSManager: AWS Manager 인스턴스
    """
    return AWSManager(region_name=region_name, profile_name=profile_name)


if __name__ == '__main__':
    # 테스트 코드
    try:
        aws_manager = create_aws_manager()
        
        # 연결 테스트
        connection_results = aws_manager.test_connection()
        print("연결 테스트 결과:", connection_results)
        
        # 통계 조회
        stats = aws_manager.get_statistics()
        print("통계 정보:", stats)
        
    except Exception as e:
        print(f"테스트 실패: {e}") 


        