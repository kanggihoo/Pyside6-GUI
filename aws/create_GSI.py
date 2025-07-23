import boto3
import time

# DynamoDB 클라이언트 생성
dynamodb_client = boto3.client('dynamodb', region_name='ap-northeast-2') # 실제 리전으로 변경

# 테이블 이름
table_name = 'ProductAssets'

# 추가할 GSI 정의
gsi_name = 'CurationStatus-SubCategory-GSI'
gsi_partition_key = 'sub_category_curation_status'
gsi_sort_key = 'recommendation_order'

try:
    print(f"테이블 '{table_name}'에 GSI '{gsi_name}' 추가 시작...")

    response = dynamodb_client.update_table(
        TableName=table_name,
        AttributeDefinitions=[
            # GSI의 키로 사용할 속성들을 정의합니다.
            # 이미 테이블에 정의되어 있어도 여기에 다시 포함해야 합니다.
            {'AttributeName': gsi_partition_key, 'AttributeType': 'S'},
            {'AttributeName': gsi_sort_key, 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': gsi_name,
                    'KeySchema': [
                        {'AttributeName': gsi_partition_key, 'KeyType': 'HASH'}, # GSI 파티션 키
                        {'AttributeName': gsi_sort_key, 'KeyType': 'RANGE'}   # GSI 정렬 키
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL' # 'KEYS_ONLY', 'INCLUDE' 중 선택 가능
                        
                    },
                }
            }
        ]
    )

    print(f"GSI 생성 요청 완료. 응답: {response['TableDescription']['TableStatus']}")

    # GSI 생성 완료 대기 (선택 사항, 하지만 실제 배포에서는 중요)
    print(f"GSI '{gsi_name}' 활성화 대기 중...")
    waiter = dynamodb_client.get_waiter('table_exists')

except dynamodb_client.exceptions.ResourceInUseException:
    print(f"오류: GSI '{gsi_name}'이(가) 이미 '{table_name}' 테이블에 존재합니다.")
except Exception as e:
    print(f"GSI 추가 중 오류 발생: {e}")