import boto3
import os
from typing import List, Optional
from botocore.exceptions import ClientError, NoCredentialsError


class S3Manager:
    """AWS S3와 상호작용하기 위한 간단한 클래스"""
    
    def __init__(self, aws_access_key_id: Optional[str] = None, 
                 aws_secret_access_key: Optional[str] = None,
                 region_name: str = 'us-east-1'):
        """
        S3Manager 초기화
        
        Args:
            aws_access_key_id: AWS Access Key ID (환경변수에서 자동 로드 가능)
            aws_secret_access_key: AWS Secret Access Key (환경변수에서 자동 로드 가능)
            region_name: AWS 리전 (기본값: us-east-1)
        """
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name
                )
            else:
                # 환경변수나 AWS 설정에서 자동으로 크리덴셜 로드
                self.s3_client = boto3.client('s3', region_name=region_name)
                
            print("S3 클라이언트가 성공적으로 초기화되었습니다.")
            
        except NoCredentialsError:
            print("AWS 크리덴셜을 찾을 수 없습니다. AWS 설정을 확인해주세요.")
            raise
    
    def list_buckets(self) -> List[str]:
        """모든 S3 버킷 리스트를 반환"""
        try:
            response = self.s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            print(f"총 {len(buckets)}개의 버킷을 찾았습니다.")
            return buckets
        except ClientError as e:
            print(f"버킷 리스트 조회 중 오류 발생: {e}")
            return []
    
    def list_objects(self, bucket_name: str, prefix: str = '') -> List[str]:
        """특정 버킷의 객체 리스트를 반환"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
                print(f"버킷 '{bucket_name}'에서 {len(objects)}개의 객체를 찾았습니다.")
                return objects
            else:
                print(f"버킷 '{bucket_name}'이 비어있거나 접근할 수 없습니다.")
                return []
                
        except ClientError as e:
            print(f"객체 리스트 조회 중 오류 발생: {e}")
            return []
    
    def upload_file(self, local_file_path: str, bucket_name: str, s3_key: str) -> bool:
        """로컬 파일을 S3에 업로드"""
        try:
            if not os.path.exists(local_file_path):
                print(f"로컬 파일을 찾을 수 없습니다: {local_file_path}")
                return False
            
            self.s3_client.upload_file(local_file_path, bucket_name, s3_key)
            print(f"파일 업로드 성공: {local_file_path} -> s3://{bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            print(f"파일 업로드 중 오류 발생: {e}")
            return False
    
    def download_file(self, bucket_name: str, s3_key: str, local_file_path: str) -> bool:
        """S3에서 파일을 다운로드"""
        try:
            # 로컬 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            self.s3_client.download_file(bucket_name, s3_key, local_file_path)
            print(f"파일 다운로드 성공: s3://{bucket_name}/{s3_key} -> {local_file_path}")
            return True
            
        except ClientError as e:
            print(f"파일 다운로드 중 오류 발생: {e}")
            return False
    
    def delete_object(self, bucket_name: str, s3_key: str) -> bool:
        """S3에서 객체 삭제"""
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            print(f"객체 삭제 성공: s3://{bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            print(f"객체 삭제 중 오류 발생: {e}")
            return False
    
    def check_object_exists(self, bucket_name: str, s3_key: str) -> bool:
        """S3에 객체가 존재하는지 확인"""
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


def main():
    """S3Manager 사용 예시"""
    print("=== AWS S3 접근 예시 ===")
    
    try:
        # S3Manager 인스턴스 생성
        # AWS 크리덴셜은 환경변수에서 자동으로 로드됩니다:
        # export AWS_ACCESS_KEY_ID=your_access_key
        # export AWS_SECRET_ACCESS_KEY=your_secret_key
        s3_manager = S3Manager()
        
        # 1. 모든 버킷 리스트 조회
        print("\n1. 버킷 리스트 조회:")
        buckets = s3_manager.list_buckets()
        for bucket in buckets:
            print(f"  - {bucket}")
        
        if not buckets:
            print("사용 가능한 버킷이 없습니다.")
            return
        
        # 첫 번째 버킷 사용 (또는 특정 버킷명 지정)
        bucket_name = buckets[0]
        print(f"\n'{bucket_name}' 버킷을 사용합니다.")
        
        # 2. 버킷의 객체 리스트 조회
        print(f"\n2. '{bucket_name}' 버킷의 객체 리스트:")
        objects = s3_manager.list_objects(bucket_name)
        for obj in objects[:5]:  # 처음 5개만 출력
            print(f"  - {obj}")
        if len(objects) > 5:
            print(f"  ... 총 {len(objects)}개 객체")
        
        # # 3. 파일 업로드 예시 (README.md 파일이 있다면)
        # if os.path.exists('README.md'):
        #     print(f"\n3. README.md 파일 업로드 시도:")
        #     upload_success = s3_manager.upload_file(
        #         'README.md', 
        #         bucket_name, 
        #         'test-uploads/README.md'
        #     )
            
        #     # 4. 업로드된 파일 존재 확인
        #     if upload_success:
        #         exists = s3_manager.check_object_exists(bucket_name, 'test-uploads/README.md')
        #         print(f"업로드된 파일 존재 확인: {exists}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        print("\nAWS 크리덴셜 설정 방법:")
        print("1. 환경변수 설정:")
        print("   export AWS_ACCESS_KEY_ID=your_access_key")
        print("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("2. 또는 AWS CLI 설정:")
        print("   aws configure")


if __name__ == "__main__":
    main() 