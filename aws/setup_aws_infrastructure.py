#!/usr/bin/env python3
"""
AWS 인프라 구축 스크립트
S3 버킷과 DynamoDB 테이블을 생성합니다.
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
import time
from pathlib import Path

class AWSInfrastructureSetup:
    def __init__(self, region_name: str = 'ap-northeast-2'):
        """
        AWS 인프라 구축 클래스 초기화
        
        Args:
            region_name: AWS 리전명 (기본값: ap-northeast-2, 서울)
        """
        self.region_name = region_name
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region_name)
        
    def create_s3_bucket(self, bucket_name: str) -> bool:
        """
        S3 버킷을 생성합니다.
        - 퍼블릭 액세스 차단
        - 버전 관리 활성화
        - 수명 주기 정책 설정 (대표 이미지가 아닌 이미지들을 Glacier로 이동)
        
        Args:
            bucket_name: 생성할 버킷 이름
            
        Returns:
            bool: 생성 성공 여부
        """
        try:
            
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.region_name}
            )
            
            print(f"✅ S3 버킷 '{bucket_name}' 생성 완료")
            
            # 퍼블릭 액세스 차단 설정
            # self.s3_client.put_public_access_block(
            #     Bucket=bucket_name,
            #     PublicAccessBlockConfiguration={
            #         'BlockPublicAcls': True,
            #         'IgnorePublicAcls': True,
            #         'BlockPublicPolicy': True,
            #         'RestrictPublicBuckets': True
            #     }
            # )
            # print(f"✅ S3 버킷 '{bucket_name}' 퍼블릭 액세스 차단 설정 완료")
            
            # 버전 관리 활성화
            # self.s3_client.put_bucket_versioning(
            #     Bucket=bucket_name,
            #     VersioningConfiguration={'Status': 'Enabled'}
            # )
            # print(f"✅ S3 버킷 '{bucket_name}' 버전 관리 활성화 완료")
            
            # 수명 주기 정책 설정
            # lifecycle_policy = {
            #     'Rules': [
            #         {
            #             'ID': 'NonRepresentativeImagesArchiving',
            #             'Status': 'Enabled',
            #             'Filter': {
            #                 'And': {
            #                     'Tags': [
            #                         {
            #                             'Key': 'status',
            #                             'Value': 'non-representative'
            #                         }
            #                     ]
            #                 }
            #             },
            #             'Transitions': [
            #                 {
            #                     'Days': 30,
            #                     'StorageClass': 'GLACIER_IR'  # Glacier Instant Retrieval
            #                 }
            #             ]
            #         }
            #     ]
            # }
            
            # self.s3_client.put_bucket_lifecycle_configuration(
            #     Bucket=bucket_name,
            #     LifecycleConfiguration=lifecycle_policy
            # )
            # print(f"✅ S3 버킷 '{bucket_name}' 수명 주기 정책 설정 완료")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyExists':
                print(f"⚠️  S3 버킷 '{bucket_name}'이 이미 존재합니다.")
                return True
            elif error_code == 'BucketAlreadyOwnedByYou':
                print(f"⚠️  S3 버킷 '{bucket_name}'을 이미 소유하고 있습니다.")
                return True
            else:
                print(f"❌ S3 버킷 생성 실패: {e}")
                return False
        except Exception as e:
            print(f"❌ S3 버킷 생성 중 예상치 못한 오류 발생: {e}")
            return False
    
    def create_dynamodb_table(self, table_name: str = 'ProductAssets') -> bool:
        """
        DynamoDB 테이블을 생성합니다.
        
        테이블 구조:
        - 파티션 키: sub_category (서브 카테고리 ID)
        - 정렬 키: product_id (제품 ID)
        
        주요 필드들:
        - main_category: 메인 카테고리명 (String)
        - current_status: 큐레이션 상태 ('PENDING' | 'COMPLETED')
        - created_at: 생성 시각 (ISO 8601)
        - last_updated_at: 최종 수정 시각 (ISO 8601)
        - representative_assets: 큐레이션 결과 (JSON 문자열)
        - completed_by: 작업자 ID (String, 선택적)
        
        파일 리스트 필드들 (List):
        - detail: detail 폴더의 이미지 파일명 리스트 (빈 리스트 허용)
        - summary: summary 폴더의 이미지 파일명 리스트 (빈 리스트 허용)
        - segment: segment 폴더의 이미지 파일명 리스트 (빈 리스트 허용)
        - text: text 폴더의 이미지 파일명 리스트 (빈 리스트 허용)
        
        GSI:
        - CurrentStatus-LastUpdatedAt-GSI: 상태별 최신순 조회용
        
        Args:
            table_name: 생성할 테이블 이름
            
        Returns:
            bool: 생성 성공 여부
        """
        try:
            # 테이블 스키마 정의
            table_schema = {
                'TableName': table_name,
                'KeySchema': [
                    {
                        'AttributeName': 'sub_category',
                        'KeyType': 'HASH'  # 파티션 키 (서브 카테고리 ID)
                    },
                    {
                        'AttributeName': 'product_id',
                        'KeyType': 'RANGE'  # 정렬 키 (제품 ID)
                    }
                ],
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'sub_category',
                        'AttributeType': 'N'  # 숫자 타입
                    },
                    {
                        'AttributeName': 'product_id',
                        'AttributeType': 'S'  # 문자열 타입
                    },
                    {
                        'AttributeName': 'curation_status',
                        'AttributeType': 'S'  # GSI 파티션 키
                    },
                    {
                        'AttributeName': 'recommendation_order',
                        'AttributeType': 'N'  # GSI 정렬 키
                    },
                    {
                        'AttributeName': 'caption_status',
                        'AttributeType': 'S'  # GSI 파티션 키
                    },
                    {
                        'AttributeName': 'caption_updated_at',
                        'AttributeType': 'S'  # GSI 정렬 키
                    },
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'CurationStatus-LastUpdatedAt-GSI',
                        'KeySchema': [
                            {
                                'AttributeName': 'curation_status',
                                'KeyType': 'HASH'  # 큐레이션 상태별 조회
                            },
                            {
                                'AttributeName': 'recommendation_order',
                                'KeyType': 'RANGE'  # 최신순 정렬
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'  # 모든 속성 프로젝션
                        },
                    },
                    {
                        'IndexName': 'CaptionStatus-LastUpdatedAt-GSI',
                        'KeySchema': [
                            {
                                'AttributeName': 'caption_status',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'caption_updated_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'  # 모든 속성 프로젝션
                        },
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'  # 온디맨드 요금제 (사용량 기반)
            }
            
            # 테이블 생성
            response = self.dynamodb_client.create_table(**table_schema)
            print(f"✅ DynamoDB 테이블 '{table_name}' 생성 시작")
            
            # 테이블이 ACTIVE 상태가 될 때까지 대기
            print("⏳ 테이블 생성 중...")
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(
                TableName=table_name,
                WaiterConfig={
                    'Delay': 5,  # 5초마다 확인
                    'MaxAttempts': 60  # 최대 5분 대기
                }
            )
            
            print(f"✅ DynamoDB 테이블 '{table_name}' 생성 완료")
            
            # 테이블 정보 출력
            table_info = self.dynamodb_client.describe_table(TableName=table_name)
            print(f"📊 테이블 상태: {table_info['Table']['TableStatus']}")
            print(f"📊 테이블 ARN: {table_info['Table']['TableArn']}")
            print(f"📊 GSI 개수: {len(table_info['Table'].get('GlobalSecondaryIndexes', []))}")
            print()
            print("📋 테이블 구조 정보:")
            print("   🔑 파티션 키: sub_category (서브 카테고리 ID)")
            print("   🔑 정렬 키: product_id (제품 ID)")
            print("   📁 파일 리스트 필드:")
            print("      - detail: detail 폴더 이미지 파일명 (List, 빈 리스트 허용)")
            print("      - summary: summary 폴더 이미지 파일명 (List, 빈 리스트 허용)")
            print("      - segment: segment 폴더 이미지 파일명 (List, 빈 리스트 허용)")
            print("      - text: text 폴더 이미지 파일명 (List, 빈 리스트 허용)")
            print("   🗂️  GSI: CurrentStatus-LastUpdatedAt-GSI (상태별 최신순 조회)")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceInUseException':
                print(f"⚠️  DynamoDB 테이블 '{table_name}'이 이미 존재합니다.")
                return True
            else:
                print(f"❌ DynamoDB 테이블 생성 실패: {e}")
                return False
        except Exception as e:
            print(f"❌ DynamoDB 테이블 생성 중 예상치 못한 오류 발생: {e}")
            return False
    
    def setup_infrastructure(self, bucket_name: str, table_name: str = 'ProductAssets') -> Dict[str, bool]:
        """
        전체 AWS 인프라를 구축합니다.
        
        Args:
            bucket_name: S3 버킷 이름
            table_name: DynamoDB 테이블 이름
            
        Returns:
            Dict[str, bool]: 각 리소스 생성 결과
        """
        print("🚀 AWS 인프라 구축을 시작합니다...")
        print(f"📍 리전: {self.region_name}")
        print(f"🪣 S3 버킷: {bucket_name}")
        print(f"🗃️  DynamoDB 테이블: {table_name}")
        print("-" * 50)
        
        results = {}
        
        # S3 버킷 생성
        print("1️⃣  S3 버킷 생성 중...")
        results['s3_bucket'] = self.create_s3_bucket(bucket_name)
        
        print()
        
        # DynamoDB 테이블 생성
        print("2️⃣  DynamoDB 테이블 생성 중...")
        results['dynamodb_table'] = self.create_dynamodb_table(table_name)
        
        print()
        print("-" * 50)
        
        # 결과 요약
        if all(results.values()):
            print("🎉 모든 AWS 인프라 구축이 완료되었습니다!")
            print()
            print("✨ 주요 기능:")
            print("   📸 이미지 파일을 S3에 저장")
            print("   🗄️  제품 정보를 DynamoDB에 관리")
            print("   📁 폴더별 파일 리스트를 DynamoDB에 저장하여 S3 조회 최적화")
            print("   🚀 list_objects_v2 호출 최소화로 비용 효율성 극대화")
            print()
            print("🔧 다음 단계:")
            print("   1. initial_upload.py로 로컬 데이터 업로드")
            print("   2. gui_main.py로 이미지 큐레이션 작업 시작")
        else:
            print("⚠️  일부 리소스 생성에 실패했습니다:")
            for resource, success in results.items():
                status = "✅" if success else "❌"
                print(f"   {status} {resource}")
        
        return results

def _load_config() -> dict:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def main():
    """메인 함수"""
    config = _load_config()
    region_name = config.get('aws', {}).get('region_name', 'ap-northeast-2')
    bucket_name = config.get('s3' , {}).get('bucket_name', 'sw-fashion-image-data')
    table_name = config.get('dynamodb' , {}).get('table_name', 'ProductAssets')
    
    
    # 인프라 구축 실행
    setup = AWSInfrastructureSetup(region_name=region_name)
    results = setup.setup_infrastructure(
        bucket_name=bucket_name,
        table_name=table_name
    )
    
    # 종료 코드 설정
    exit_code = 0 if all(results.values()) else 1
    exit(exit_code)

if __name__ == '__main__':
    main() 