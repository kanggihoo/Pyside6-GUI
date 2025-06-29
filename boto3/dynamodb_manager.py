import boto3
import os
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError


class DynamoDBManager:
    """AWS DynamoDB와 상호작용하기 위한 간단한 클래스"""
    
    def __init__(self, aws_access_key_id: Optional[str] = None, 
                 aws_secret_access_key: Optional[str] = None,
                 region_name: str = 'us-east-1'):
        """
        DynamoDBManager 초기화
        
        Args:
            aws_access_key_id: AWS Access Key ID (환경변수에서 자동 로드 가능)
            aws_secret_access_key: AWS Secret Access Key (환경변수에서 자동 로드 가능)
            region_name: AWS 리전 (기본값: us-east-1)
        """
        try:
            
            self.dynamodb_client = boto3.client('dynamodb')
            print("DynamoDB 클라이언트가 성공적으로 초기화되었습니다.")
            
        except NoCredentialsError:
            print("AWS 크리덴셜을 찾을 수 없습니다. AWS 설정을 확인해주세요.")
            raise
    
    def create_table(self, table_name: str) -> bool:
        """간단한 DynamoDB 테이블 생성 (기본 구조)"""
        try:
            response = self.dynamodb_client.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'  # 파티션 키
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'  # String 타입
                    }
                ],
                BillingMode='PAY_PER_REQUEST'  # 온디맨드 요금제
            )
            
            print(f"테이블 '{table_name}' 생성을 시작했습니다.")
            print(f"테이블 상태: {response['TableDescription']['TableStatus']}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"테이블 '{table_name}'이 이미 존재합니다.")
                return True
            else:
                print(f"테이블 생성 중 오류 발생: {e}")
                return False
    
    def list_tables(self) -> List[str]:
        """모든 DynamoDB 테이블 리스트를 반환"""
        try:
            response = self.dynamodb_client.list_tables()
            tables = response['TableNames']
            print(f"총 {len(tables)}개의 테이블을 찾았습니다: {tables}")
            return tables
        except ClientError as e:
            print(f"테이블 리스트 조회 중 오류 발생: {e}")
            return []
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """DynamoDB 테이블에 새로운 아이템 추가"""
        try:
            # Python 딕셔너리를 DynamoDB 형식으로 변환
            dynamodb_item = self._convert_to_dynamodb_format(item)
            
            response = self.dynamodb_client.put_item(
                TableName=table_name,
                Item=dynamodb_item
            )
            
            print(f"아이템이 '{table_name}' 테이블에 성공적으로 추가되었습니다.")
            print(f"추가된 아이템: {item}")
            return True
            
        except ClientError as e:
            print(f"아이템 추가 중 오류 발생: {e}")
            return False
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """DynamoDB 테이블에서 특정 아이템 조회"""
        try:
            # 키를 DynamoDB 형식으로 변환
            dynamodb_key = self._convert_to_dynamodb_format(key)
            
            response = self.dynamodb_client.get_item(
                TableName=table_name,
                Key=dynamodb_key
            )
            
            if 'Item' in response:
                # DynamoDB 형식을 Python 딕셔너리로 변환
                item = self._convert_from_dynamodb_format(response['Item'])
                print(f"아이템 조회 성공: {item}")
                return item
            else:
                print("아이템을 찾을 수 없습니다.")
                return None
                
        except ClientError as e:
            print(f"아이템 조회 중 오류 발생: {e}")
            return None
    
    def scan_table(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """DynamoDB 테이블의 모든 아이템을 스캔 (제한된 개수)"""
        try:
            response = self.dynamodb_client.scan(
                TableName=table_name,
                Limit=limit
            )
            
            items = []
            if 'Items' in response:
                for dynamodb_item in response['Items']:
                    item = self._convert_from_dynamodb_format(dynamodb_item)
                    items.append(item)
            
            print(f"'{table_name}' 테이블에서 {len(items)}개의 아이템을 조회했습니다.")
            return items
            
        except ClientError as e:
            print(f"테이블 스캔 중 오류 발생: {e}")
            return []
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """DynamoDB 테이블에서 특정 아이템 삭제"""
        try:
            # 키를 DynamoDB 형식으로 변환
            dynamodb_key = self._convert_to_dynamodb_format(key)
            
            response = self.dynamodb_client.delete_item(
                TableName=table_name,
                Key=dynamodb_key
            )
            
            print(f"아이템이 '{table_name}' 테이블에서 성공적으로 삭제되었습니다.")
            return True
            
        except ClientError as e:
            print(f"아이템 삭제 중 오류 발생: {e}")
            return False
    
    def _convert_to_dynamodb_format(self, item: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Python 딕셔너리를 DynamoDB 형식으로 변환"""
        dynamodb_item = {}
        
        for key, value in item.items():
            if isinstance(value, str):
                dynamodb_item[key] = {'S': value}
            elif isinstance(value, int):
                dynamodb_item[key] = {'N': str(value)}
            elif isinstance(value, float):
                dynamodb_item[key] = {'N': str(value)}
            elif isinstance(value, bool):
                dynamodb_item[key] = {'BOOL': value}
            elif isinstance(value, list):
                # 리스트는 문자열 리스트로 가정
                dynamodb_item[key] = {'SS': [str(v) for v in value]}
            elif value is None:
                dynamodb_item[key] = {'NULL': True}
            else:
                # 기타는 문자열로 변환
                dynamodb_item[key] = {'S': str(value)}
        
        return dynamodb_item
    
    def _convert_from_dynamodb_format(self, dynamodb_item: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """DynamoDB 형식을 Python 딕셔너리로 변환"""
        item = {}
        
        for key, value_dict in dynamodb_item.items():
            for type_key, value in value_dict.items():
                if type_key == 'S':
                    item[key] = value
                elif type_key == 'N':
                    # 숫자는 정수 또는 실수로 변환
                    if '.' in value:
                        item[key] = float(value)
                    else:
                        item[key] = int(value)
                elif type_key == 'BOOL':
                    item[key] = value
                elif type_key == 'SS':
                    item[key] = value
                elif type_key == 'NULL':
                    item[key] = None
                else:
                    item[key] = value
        
        return item

