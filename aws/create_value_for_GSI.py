import boto3
import time

dynamodb_client = boto3.client('dynamodb', region_name='ap-northeast-2')
table_name = 'ProductAssets' # 실제 메인 테이블 이름으로 변경

# 구분자 (delimiter) 설정. GSI 쿼리 시 `begins_with` 등에 활용 가능
DELIMITER = '#'

print(f"테이블 '{table_name}'의 항목들을 업데이트하여 'sub_category_curation_status' 속성 추가 시작...")

def get_all_sub_categories():
    """테이블에서 모든 고유한 sub_category 값을 가져옵니다."""
    print("모든 sub_category 값을 수집 중...")
    
    # Scan을 통해 모든 sub_category 값을 수집
    response = dynamodb_client.query(
        TableName=table_name,
        KeyConditionExpression="sub_category = :sub_category",
        ExpressionAttributeValues={
            ':sub_category': {'N': '0'},
        }
    )
    items = response['Items']
    all_sub_categories = []
    for item in items:
        product_id = item.get('product_id', {}).get('S')
        product_id = int(product_id.split('_')[-1])
        all_sub_categories.append(product_id)
    return all_sub_categories
    # sub_categories = set()
    # for page in scan_iterator:
    #     for item in page.get('Items', []):
    #         sub_category = item.get('sub_category', {}).get('N')
    #         if sub_category:
    #             sub_categories.add(sub_category)
    
    # print(f"총 {len(sub_categories)}개의 고유한 sub_category 발견: {sorted(sub_categories)}")
    # return sorted(sub_categories)

def update_items_by_sub_category(sub_category):
    """특정 sub_category에 해당하는 모든 항목을 업데이트합니다."""
    print(f"\nsub_category '{sub_category}' 처리 중...")
    
    # Query를 사용하여 특정 sub_category의 모든 항목을 가져옵니다
    paginator = dynamodb_client.get_paginator('query')
    query_iterator = paginator.paginate(
        TableName=table_name,
        KeyConditionExpression='sub_category = :sub_category',
        ExpressionAttributeValues={
            ':sub_category': {'N': str(sub_category)}
        }
    )
    
    updated_count = 0
    for page in query_iterator:
        items = page.get('Items', [])
        
        for item in items:
            curation_status = item.get('curation_status', {}).get('S')
            product_id = item.get('product_id', {}).get('S')
            
            if curation_status and product_id:
                # 새로운 합성 키 값 생성
                new_gsi_pk_value = f"{sub_category}{DELIMITER}{curation_status}"
                
                Key = {
                    'sub_category': {'N': str(sub_category)},
                    'product_id': {'S': product_id}
                }
                
                try:
                    update_response = dynamodb_client.update_item(
                        TableName=table_name,
                        Key=Key,
                        UpdateExpression="SET #gsi_pk = :gsi_pk_val",
                        ExpressionAttributeNames={
                            '#gsi_pk': 'sub_category_curation_status'
                        },
                        ExpressionAttributeValues={
                            ':gsi_pk_val': {'S': new_gsi_pk_value}
                        }
                    )
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"sub_category '{sub_category}': {updated_count}개 항목 업데이트 완료")
                except Exception as e:
                    print(f"Error updating item {product_id}: {e}")
            
        # API 호출량 조절을 위한 짧은 지연
        time.sleep(0.05)
    
    print(f"  sub_category '{sub_category}': {updated_count}개 항목 업데이트 완료")
    return updated_count

def main():
    """메인 실행 함수"""
    total_updated_items = 0
    
    # 모든 sub_category 값을 가져옵니다
    # sub_categories = get_all_sub_categories()
    sub_categories = [1005,1002,1003]

    
    if not sub_categories:
        print("업데이트할 sub_category가 없습니다.")
        return
    
    # 각 sub_category에 대해 쿼리를 수행하여 업데이트합니다
    for sub_category in sub_categories:
        updated_count = update_items_by_sub_category(sub_category)
        total_updated_items += updated_count
    
    print(f"\n총 {total_updated_items}개의 항목에 'sub_category_curation_status' 속성 업데이트 완료.")

if __name__ == "__main__":
    main()