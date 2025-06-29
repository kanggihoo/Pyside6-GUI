#!/usr/bin/env python3
"""
AWS 통신 중앙 관리 모듈
S3와 DynamoDB와의 모든 통신을 담당하는 핵심 모듈입니다.
"""

import boto3
import json
import os
from datetime import datetime, timezone
from typing import Any
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
        
        # 세션 생성
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name)
        else:
            self.session = boto3.Session()
        
        # 클라이언트 초기화
        self.s3_client = self.session.client('s3', region_name=region_name)
        self.dynamodb_client = self.session.client('dynamodb', region_name=region_name)
        
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
            item: DynamoDB 아이템 (타입 정보 포함)
            
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
                converted[key] = [self._convert_dynamodb_item({'item': item})['item'] for item in value['L']]
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
    
    def get_s3_image_urls(self, sub_category: int, product_id: str, folder_name: str = None) -> list[dict[str, str]]:
        """
        특정 상품의 S3 이미지 URL 목록을 가져옵니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            folder_name: 특정 폴더명 (None이면 모든 폴더)
            
        Returns:
            List[Dict[str, str]]: 이미지 정보 리스트 [{'key': '...', 'url': '...', 'folder': '...'}]
        """
        try:
            prefix = f"main_category/{sub_category}/{product_id}/"
            if folder_name:
                prefix += f"{folder_name}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # 이미지 파일만 필터링
                    if key.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        # Presigned URL 생성 (1시간 유효)
                        url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': self.bucket_name, 'Key': key},
                            ExpiresIn=3600
                        )
                        
                        # 폴더명 추출
                        path_parts = key.split('/')
                        folder = path_parts[-2] if len(path_parts) > 1 else ''
                        
                        images.append({
                            'key': key,
                            'url': url,
                            'folder': folder,
                            'filename': path_parts[-1]
                        })
            
            logger.info(f"S3 이미지 조회 완료: {product_id}, 폴더: {folder_name}, 개수: {len(images)}")
            return images
            
        except ClientError as e:
            logger.error(f"S3 이미지 조회 실패 {product_id}: {e}")
            return []
    
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
    
    def create_product_item(self, sub_category: int, product_id: str, 
                           product_info: dict[str, Any]) -> bool:
        """
        DynamoDB에 새로운 제품 아이템을 생성합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            product_info: meta.json에서 읽은 제품 정보
            
        Returns:
            bool: 생성 성공 여부
        """
        try:
            current_time = self._get_current_timestamp()
            
            # DynamoDB client용 아이템 구성 (타입 명시 필요)
            item = {
                'sub_category': {'N': str(sub_category)},
                'product_id': {'S': product_id},
                'product_info': {'S': json.dumps(product_info, ensure_ascii=False)},
                'current_status': {'S': 'PENDING'},
                'last_updated_at': {'S': current_time},
                'created_at': {'S': current_time}
            }
            
            # 색상 정보가 있다면 추가
            if 'colors' in product_info:
                colors = product_info['colors']
                if isinstance(colors, list):
                    item['available_colors'] = {'SS': colors}
                elif isinstance(colors, str):
                    item['available_colors'] = {'SS': [colors]}
            
            self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=item
            )
            logger.info(f"DynamoDB 아이템 생성 성공: {sub_category}-{product_id}")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB 아이템 생성 실패 {sub_category}-{product_id}: {e}")
            return False
    
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
                'IndexName': 'CurationStatus-LastUpdatedAt-GSI',
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