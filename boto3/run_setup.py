#!/usr/bin/env python3
"""
AWS 인프라 구축 통합 실행 스크립트
설정 확인 -> 인프라 구축을 순차적으로 실행합니다.
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


from setup_aws_infrastructure import AWSInfrastructureSetup

def load_config(config_path: str = None) -> dict:
    """
    설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로 (None이면 기본 경로 사용)
        
    Returns:
        dict: 설정 정보
    """
    if config_path is None:
        config_path = current_dir / 'config.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ 설정 파일 JSON 형식 오류: {e}")
        return {}

def print_banner():
    """배너를 출력합니다."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    AWS 인프라 구축 도구                        ║
║                AI Dataset Curation Tool                      ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_step(step_num: int, title: str, description: str = ""):
    """단계별 제목을 출력합니다."""
    print(f"\n{'='*60}")
    print(f"📋 STEP {step_num}: {title}")
    if description:
        print(f"💭 {description}")
    print('='*60)

def confirm_proceed(message: str) -> bool:
    """사용자 확인을 받습니다."""
    while True:
        response = input(f"\n{message} (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            return False
        else:
            print("y(yes) 또는 n(no)를 입력해주세요.")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='AWS 인프라 구축 통합 실행 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예제:
  python run_setup.py --bucket-name my-ai-dataset-bucket
  python run_setup.py --bucket-name my-bucket --table-name MyProductAssets --region us-west-2
  python run_setup.py --config custom_config.json --skip-check
        """
    )
    
    parser.add_argument('--bucket-name', help='S3 버킷 이름 (필수 또는 config에서 로드)')
    parser.add_argument('--table-name', help='DynamoDB 테이블 이름 (기본값: config 또는 ProductAssets)')
    parser.add_argument('--region', help='AWS 리전 (기본값: config 또는 ap-northeast-2)')
    parser.add_argument('--profile', help='AWS 프로필명 (기본값: config 또는 default)')
    parser.add_argument('--config', help='설정 파일 경로 (기본값: config.json)')
    parser.add_argument('--skip-check', action='store_true', help='AWS 설정 확인 단계 건너뛰기')
    parser.add_argument('--check-only', action='store_true', help='AWS 설정 확인만 실행')
    parser.add_argument('--force', action='store_true', help='확인 프롬프트 없이 강제 실행')
    
    args = parser.parse_args()
    
    # 배너 출력
    print_banner()
    
    # 설정 파일 로드
    config = load_config(args.config)
    
    # 매개변수 우선순위: CLI 인수 > 설정 파일 > 기본값
    bucket_name = args.bucket_name or config.get('s3', {}).get('bucket_name', '')
    table_name = args.table_name or config.get('dynamodb', {}).get('table_name', 'ProductAssets')
    region = args.region or config.get('aws', {}).get('region', 'ap-northeast-2')
    
    # 필수 매개변수 확인
    if not bucket_name:
        print("❌ S3 버킷 이름이 필요합니다. --bucket-name 옵션을 사용하거나 config.json에서 설정해주세요.")
        return 1
    
    # 설정 정보 출력
    print(f"📋 설정 정보:")
    print(f"   🪣 S3 버킷: {bucket_name}")
    print(f"   🗃️  DynamoDB 테이블: {table_name}")
    print(f"   📍 AWS 리전: {region}")
    
    if not args.force:
        if not confirm_proceed("위 설정으로 진행하시겠습니까?"):
            print("작업이 취소되었습니다.")
            return 0
    
    # STEP 2: AWS 인프라 구축
    print_step(2, "AWS 인프라 구축", "S3 버킷과 DynamoDB 테이블을 생성합니다.")
    
    if not args.force and not args.skip_check:
        print("⚠️  주의: 이 작업은 AWS 리소스를 생성하며 요금이 발생할 수 있습니다.")
        if not confirm_proceed("정말로 인프라를 구축하시겠습니까?"):
            print("작업이 취소되었습니다.")
            return 0
    
    setup = AWSInfrastructureSetup(region_name=region)
    setup_results = setup.setup_infrastructure(bucket_name=bucket_name, table_name=table_name)
    
    # 구축 결과 평가
    if all(setup_results.values()):
        print_step(3, "구축 완료", "모든 AWS 인프라가 성공적으로 구축되었습니다.")
        
        print("🎉 축하합니다! AWS 인프라 구축이 완료되었습니다.")
        return 0
    else:
        print("\n❌ 일부 리소스 생성에 실패했습니다.")
        failed_resources = [resource for resource, success in setup_results.items() if not success]
        print(f"실패한 리소스: {', '.join(failed_resources)}")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 작업이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1) 