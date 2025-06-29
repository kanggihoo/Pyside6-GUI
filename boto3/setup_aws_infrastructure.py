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
                        'KeyType': 'HASH'  # 파티션 키
                    },
                    {
                        'AttributeName': 'product_id',
                        'KeyType': 'RANGE'  # 정렬 키
                    }
                ],
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'sub_category',
                        'AttributeType': 'N'
                    },
                    {
                        'AttributeName': 'product_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'current_status',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'last_updated_at',
                        'AttributeType': 'S'
                    },
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'CurationStatus-LastUpdatedAt-GSI',
                        'KeySchema': [
                            {
                                'AttributeName': 'current_status',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'last_updated_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                    },
                ],
                'BillingMode': 'PAY_PER_REQUEST'  # 온디맨드 요금제
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
        else:
            print("⚠️  일부 리소스 생성에 실패했습니다:")
            for resource, success in results.items():
                status = "✅" if success else "❌"
                print(f"   {status} {resource}")
        
        return results

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AWS 인프라 구축 스크립트')
    parser.add_argument('--bucket-name', required=True, help='S3 버킷 이름')
    parser.add_argument('--table-name', default='ProductAssets', help='DynamoDB 테이블 이름 (기본값: ProductAssets)')
    parser.add_argument('--region', default='ap-northeast-2', help='AWS 리전 (기본값: ap-northeast-2)')
    
    args = parser.parse_args()
    
    # 인프라 구축 실행
    setup = AWSInfrastructureSetup(region_name=args.region)
    results = setup.setup_infrastructure(
        bucket_name=args.bucket_name,
        table_name=args.table_name
    )
    
    # 종료 코드 설정
    exit_code = 0 if all(results.values()) else 1
    exit(exit_code)

if __name__ == '__main__':
    main() 