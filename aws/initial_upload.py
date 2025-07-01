#!/usr/bin/env python3
"""
초기 데이터 업로드 스크립트
로컬 데이터 디렉토리의 모든 파일을 AWS S3와 DynamoDB로 업로드합니다.
"""

import os
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import argparse

# 현재 스크립트 경로 기준으로 aws_manager 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent))
from aws_manager import create_aws_manager


#TODO : 로깅에서의 메시지 출력 , loger file 관련 추가 필요 . (업로드 실패한 경우에 대해서는 )
#TODO : 나중에 업로드 실패한 제품에 대해서는 다시 올릴 수 있는 코드와, s3에 파일 업로드 시에는 해당 객체가 있는 경우 덮어쓸지, 아니면 업로드 하지 않을지 확인하는 코드??
#TODO : 파일 업로드시 덮어쓰기 여부 추가하는거 필요할듯

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InitialUploader:
    """초기 데이터 업로드 담당 클래스"""
    
    def __init__(self, data_root_path: str, aws_manager):
        """
        초기화
        
        Args:
            data_root_path: 로컬 데이터 루트 경로 (1005 디렉토리 포함)
            aws_manager: AWS Manager 인스턴스
        """
        self.data_root_path = Path(data_root_path)
        self.aws_manager = aws_manager
        
        # 통계 정보
        self.stats = {
            'total_products': 0,
            'uploaded_products': 0,
            'failed_products': 0,
            'total_files': 0,
            'uploaded_files': 0,
            'failed_files': 0,
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # 카테고리 통계 정보
        self.category_stats = {
            "main_categories": [],
            "sub_categories": {},
            "product_counts": {},
            "total_products": 0
        }
        
        # 지원하는 이미지 확장자
        self.image_extensions = {'.jpg', '.jpeg', '.png'}
        
        logger.info(f"초기 업로더 초기화 완료 - 데이터 경로: {self.data_root_path}")
    
    def discover_products(self) -> List[Dict[str, Any]]:
        """
        로컬 데이터 디렉토리에서 제품 정보를 발견합니다. \n
        서브카테고리 Id , 서브 카테고리 안의 제품 Id , 제품 디렉토리 경로, meta.json 파일 담은 리스트 반환 
        
        Returns:
            List[Dict]: 발견된 제품 정보 리스트
        """
        products = []
        category_stats = {
            "main_categories": [],
            "sub_categories": {},
            "product_counts": {},
            "total_products": 0
        }
        
        # 서브 카테고리 디렉토리 순회
        main_category = self.data_root_path.name
        
        # 메인 카테고리 초기화
        if main_category not in category_stats["main_categories"]:
            category_stats["main_categories"].append(main_category)
            category_stats["sub_categories"][main_category] = []
            category_stats["product_counts"][main_category] = {}
        
        for sub_category_dir in self.data_root_path.iterdir():
            if not sub_category_dir.is_dir():
                continue
                
            try:
                sub_category_id = int(sub_category_dir.name)
            except ValueError:
                logger.warning(f"서브 카테고리 ID가 숫자가 아닙니다: {sub_category_dir.name}")
                continue
            
            # 서브 카테고리 추가
            if sub_category_id not in category_stats["sub_categories"][main_category]:
                category_stats["sub_categories"][main_category].append(sub_category_id)
            
            product_count = 0
            
            # 제품 ID 디렉토리 순회
            for product_dir in sub_category_dir.iterdir():
                if not product_dir.is_dir():
                    continue
                
                product_id = product_dir.name
                meta_file = product_dir / 'meta.json'
                
                if meta_file.exists():
                    products.append({
                        'main_category': main_category,
                        'sub_category': sub_category_id,
                        'product_id': product_id,
                        'local_path': product_dir,
                        'meta_file': meta_file
                    })
                    product_count += 1
                else:
                    logger.warning(f"meta.json 파일이 없습니다: {product_dir}")
            
            # 제품 수 저장
            category_stats["product_counts"][main_category][str(sub_category_id)] = product_count
            category_stats["total_products"] += product_count
        
        # 서브 카테고리 정렬
        category_stats["sub_categories"][main_category].sort()
        
        # 통계 정보 저장
        self.category_stats = category_stats
        
        self.stats['total_products'] = len(products)
        logger.info(f"총 {len(products)}개 제품 발견")
        logger.info(f"카테고리 통계: {category_stats}")
        return products
    
    def load_meta_json(self, meta_file_path: Path) -> Optional[Dict[str, Any]]:
        """
        meta.json 파일을 로드합니다.
        
        Args:
            meta_file_path: meta.json 파일 경로
            
        Returns:
            Optional[Dict]: 메타 정보 (실패시 None)
        """
        try:
            with open(meta_file_path, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            return meta_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 실패 {meta_file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"메타 파일 로드 실패 {meta_file_path}: {e}")
            return None
    
    def get_files_to_upload(self, product_dir: Path) -> List[Dict[str, Any]]:
        """
        업로드할 파일 목록을 생성합니다.(이미지 파일 , 메타 데이터인 meta.json 파일 구분)
        
        Args:
            product_dir: 제품 디렉토리 경로
            
        Returns:
            List[Dict]: 업로드할 파일 정보 리스트
        """
        files_to_upload = []
        
        # 제품 디렉토리 하위의 모든 파일 순회
        for file_path in product_dir.rglob('*'):
            # 제품 디렉토리 내의 모든 파일과 폴더를 깊이 우선으로 순회합니다
            if file_path.is_file():
                # 숨김 파일 체크 (.DS_Store 등)
                if file_path.name.startswith('.'):
                    continue
                
                # 상대 경로 계산 (제품 디렉토리 기준)
                relative_path = file_path.relative_to(product_dir)
                
                # 파일 타입 결정
                file_type = 'unknown'
                if file_path.suffix.lower() in self.image_extensions:
                    file_type = 'image'
                elif file_path.name == 'meta.json':
                    file_type = 'meta'
                
                
                files_to_upload.append({
                    'local_path': file_path,
                    'relative_path': str(relative_path),
                    'file_type': file_type,
                    'size': file_path.stat().st_size
                })
        
        return files_to_upload
    
    def upload_product_files(self, main_category: str , sub_category: int, product_id: str, 
                           files_to_upload: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        제품의 모든 파일을 S3에 업로드합니다.
        
        Args:
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            files_to_upload: 업로드할 파일 목록
            
        Returns:
            Dict[str, int]: 업로드 결과 통계
        """
        upload_stats = {'success': 0, 'failed': 0}
        
        for file_info in files_to_upload:
            try:
                # S3 객체 키 생성 (main_category는 기본값 사용)
                s3_key = self.aws_manager._get_s3_object_key(
                    main_category, sub_category, product_id, file_info['relative_path']
                )
                
                # 메타데이터 준비
                metadata = {
                    'product_id': product_id,
                    'sub_category': str(sub_category),
                    'file_type': file_info['file_type'],
                    'original_path': str(file_info['relative_path'])
                }
                
                # 파일 업로드
                success = self.aws_manager.upload_file_to_s3(
                    str(file_info['local_path']),
                    s3_key,
                    metadata=metadata
                )
                
                if success:
                    upload_stats['success'] += 1
                    logger.debug(f"파일 업로드 성공: {s3_key}")
                else:
                    upload_stats['failed'] += 1
                    logger.error(f"파일 업로드 실패: {s3_key}")
                
            except Exception as e:
                upload_stats['failed'] += 1
                logger.error(f"파일 업로드 중 오류 {file_info['local_path']}: {e}")
        
        return upload_stats
    
    def create_dynamodb_item(self, main_category: str, sub_category: int, product_id: str) -> tuple[bool, bool]:
        """
        DynamoDB에 제품 아이템을 생성합니다.
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            
        Returns:
            tuple[bool, bool]: (처리 성공 여부, 새 제품 여부)
        """
        try:
            # DynamoDB 아이템 생성 (새 제품이면 True, 기존 제품이면 False 반환)
            is_new_product = self.aws_manager.create_product_item(
                main_category, sub_category, product_id
            )
            
            if is_new_product:
                logger.info(f"DynamoDB 새 아이템 생성 성공: {main_category}-{sub_category}-{product_id}")
            else:
                logger.info(f"DynamoDB 기존 아이템 업데이트 성공: {main_category}-{sub_category}-{product_id}")
            
            return True, is_new_product
            
        except Exception as e:
            logger.error(f"DynamoDB 아이템 처리 중 오류 {main_category}-{sub_category}-{product_id}: {e}")
            return False, False
    
    def process_meta_data(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        메타 데이터를 DynamoDB 저장용으로 전처리합니다.
        주요 작업:
        - meta.json 파일에서 읽은 원본 메타 데이터를 DynamoDB에서 안전하게 저장할 수 있는 형태로 변환
        - None 값은 제거하고, 기본 타입(str, int, float, bool)과 복합 타입(list, dict)은 그대로 유지
        - DynamoDB에서 지원하지 않는 타입은 문자열로 변환
        
        Args:
            meta_data: 원본 메타 데이터(meta.json 파일로 부터 읽은 python 딕셔너리)
            
        Returns:
            Dict: 전처리된 메타 데이터
        """
        processed = {}
        
        # 기본 정보 복사
        for key, value in meta_data.items():
            # DynamoDB에서 지원하지 않는 타입 처리
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                processed[key] = value
            elif isinstance(value, (list, dict)):
                processed[key] = value
            else:
                processed[key] = str(value)
        
        return processed
    
    def upload_single_product(self, product_info: Dict[str, Any]) -> bool:
        """
        단일 제품_id 폴더 안의 모든 파일을 s3에 업로드합니다.(이미지 , meta.json 파일) \n
        업로드 한 제품 id에서 대해서는 DynamoDB에 아이템을 생성(기본 제품_id , sub_category , main_category) \n
        업로드 성공 시 카테고리 메타데이터도 업데이트합니다.
        
        Args:
            product_info: 제품 정보
            
        Returns:
            bool: 업로드 성공 여부
        """
        main_category = product_info['main_category']
        sub_category = product_info['sub_category']
        product_id = product_info['product_id']
        product_dir = product_info['local_path']
        meta_file = product_info['meta_file']
        
        logger.info(f"제품 업로드 시작: {main_category}-{sub_category}-{product_id}")
        
        try:
            # 1. 메타 데이터 로드(meta.json 파일 로드)
            meta_data = self.load_meta_json(meta_file)
            if meta_data is None:
                logger.error(f"메타 데이터 로드 실패: {product_id}")
                return False
            
            # 2. 업로드할 파일 목록 생성
            files_to_upload = self.get_files_to_upload(product_dir)
            logger.info(f"업로드할 파일 개수: {len(files_to_upload)}")
            
            # 3. S3에 파일 업로드
            upload_stats = self.upload_product_files(main_category, sub_category, product_id, files_to_upload)
            
            # 4. DynamoDB에 아이템 생성
            db_success, is_new_product = self.create_dynamodb_item(main_category, sub_category, product_id)
            
            # 5. 결과 통계 업데이트
            self.stats['total_files'] += len(files_to_upload)
            self.stats['uploaded_files'] += upload_stats['success']
            self.stats['failed_files'] += upload_stats['failed']
            
            # 전체 성공 여부 판단
            success = (upload_stats['failed'] == 0 and db_success)
            
            if success:
                self.stats['uploaded_products'] += 1
                logger.info(f"제품 업로드 완료: {sub_category}-{product_id}")
                
                # 6. 새 제품인 경우에만 카테고리 메타데이터 업데이트
                if is_new_product:
                    metadata_success = self.aws_manager.increment_product_count(main_category, sub_category)
                    if not metadata_success:
                        logger.warning(f"카테고리 메타데이터 업데이트 실패: {main_category}-{sub_category}")
                    else:
                        logger.info(f"새 제품 추가로 카테고리 카운트 증가: {main_category}-{sub_category}")
                else:
                    logger.info(f"기존 제품 업데이트로 카테고리 카운트 유지: {main_category}-{sub_category}")
                
            else:
                self.stats['failed_products'] += 1
                logger.error(f"제품 업로드 실패: {sub_category}-{product_id}")
            
            return success
            
        except Exception as e:
            self.stats['failed_products'] += 1
            logger.error(f"제품 업로드 중 예상치 못한 오류 {sub_category}-{product_id}: {e}")
            return False
    
    def upload_all_products(self, max_products: Optional[int] = None) -> Dict[str, Any]:
        """
        모든 제품을 업로드합니다.
        
        Args:
            max_products: 최대 업로드할 제품 수 (None이면 제한 없음)
            
        Returns:
            Dict: 업로드 결과 통계
        """
        logger.info("전체 제품 업로드 시작")
        
        # 제품 목록 발견 (카테고리 통계도 수집됨)
        products = self.discover_products()
        
        if max_products:
            products = products[:max_products]
            logger.info(f"최대 {max_products}개 제품으로 제한")
        
        # 초기 카테고리 메타데이터 설정
        logger.info("카테고리 메타데이터 초기화 중...")
        initial_metadata_success = self.initialize_category_metadata()
        if not initial_metadata_success:
            logger.warning("카테고리 메타데이터 초기화 실패")
        
        # 각 제품 업로드
        for i, product_info in enumerate(products, 1):
            logger.info(f"진행률: {i}/{len(products)} ({i/len(products)*100:.1f}%)")
            
            success = self.upload_single_product(product_info)
            
            if not success:
                logger.warning(f"제품 업로드 실패: {product_info['product_id']}")
            
            # 진행률 로그 (매 10개마다)
            if i % 10 == 0:
                logger.info(f"중간 통계 - 성공: {self.stats['uploaded_products']}, 실패: {self.stats['failed_products']}")
        
        # 최종 통계
        self.stats['end_time'] = datetime.now()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("=" * 60)
        logger.info("업로드 완료!")
        logger.info(f"총 소요 시간: {duration}")
        logger.info(f"총 제품 수: {self.stats['total_products']}")
        logger.info(f"성공한 제품 수: {self.stats['uploaded_products']}")
        logger.info(f"실패한 제품 수: {self.stats['failed_products']}")
        logger.info(f"총 파일 수: {self.stats['total_files']}")
        logger.info(f"성공한 파일 수: {self.stats['uploaded_files']}")
        logger.info(f"실패한 파일 수: {self.stats['failed_files']}")
        
        # 최종 카테고리 메타데이터 상태 확인
        final_metadata = self.aws_manager.get_category_metadata()
        if final_metadata and 'categories_info' in final_metadata:
            categories_info = final_metadata['categories_info']
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            logger.info(f"최종 카테고리 메타데이터 - 총 제품 수: {categories_info.get('total_products', 0)}")
        
        logger.info("=" * 60)
        
        return self.stats
    
    def initialize_category_metadata(self) -> bool:
        """
        카테고리 메타데이터를 초기화합니다.
        기존 메타데이터가 있으면 그것을 유지하고, 없으면 빈 구조로 초기화합니다.
        
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            # 기존 메타데이터 조회
            existing_metadata = self.aws_manager.get_category_metadata()
            
            if existing_metadata is None:
                # 메타데이터가 없으면 빈 구조로 초기화
                logger.info("카테고리 메타데이터가 없습니다. 빈 구조로 초기화합니다.")
                empty_categories = {
                    "main_categories": [],
                    "sub_categories": {},
                    "product_counts": {},
                    "total_products": 0
                }
                success = self.aws_manager.update_category_metadata(empty_categories)
                logger.info("빈 카테고리 메타데이터 생성 완료")
                return success
            else:
                logger.info("기존 카테고리 메타데이터를 사용합니다")
                return True
                
        except Exception as e:
            logger.error(f"카테고리 메타데이터 초기화 실패: {e}")
            return False


def main():
    """메인 함수"""
    # parser = argparse.ArgumentParser(description='초기 데이터 업로드 스크립트')
    # parser.add_argument('--data-path', default='1005', help='데이터 디렉토리 경로 (기본값: 1005)')
    # parser.add_argument('--region', default='ap-northeast-2', help='AWS 리전 (기본값: ap-northeast-2)')
    # parser.add_argument('--profile', help='AWS 프로필명')
    # parser.add_argument('--max-products', type=int, help='최대 업로드할 제품 수 (테스트용)')
    # parser.add_argument('--dry-run', action='store_true', help='실제 업로드 없이 테스트만 실행')
    # parser.add_argument('--main-category', required=True, help='메인 카테고리 (기본값: TOP)')
    
    # args = parser.parse_args()
    from dataclasses import dataclass
    
    @dataclass
    class args:
        data_path: str = 'TOP'
        region: str = 'ap-northeast-2'
        profile: str = None
        max_products: int = 2
        dry_run: bool = False
        main_category: str = 'TOP'
        
    
    try:
        # 데이터 경로 확인
        HOME_DIR = os.getcwd()
        data_path = Path(HOME_DIR) / args.data_path
        if not data_path.exists():
            logger.error(f"데이터 경로가 존재하지 않습니다: {data_path}")
            return 1
        
        # AWS Manager 생성
        logger.info("AWS Manager 초기화 중...")
        aws_manager = create_aws_manager(
            region_name=args.region,
            profile_name=args.profile
        )
        
        # 연결 테스트
        logger.info("AWS 연결 테스트 중...")
        connection_results = aws_manager.test_connection()
        if not all(connection_results.values()):
            logger.error(f"AWS 연결 실패: {connection_results}")
            return 1
        
        logger.info("AWS 연결 성공!")
        
        if args.dry_run:
            logger.info("DRY RUN 모드: 실제 업로드는 하지 않습니다.")
            # 간단한 검증만 수행
            uploader = InitialUploader(str(data_path), aws_manager)
            products = uploader.discover_products()
            logger.info(f"발견된 제품 수: {len(products)}")
            return 0
        
        # 업로더 생성 및 실행
        uploader = InitialUploader(str(data_path), aws_manager)
        results = uploader.upload_all_products(max_products=args.max_products)
        
        # 결과에 따른 종료 코드
        if results['failed_products'] == 0:
            logger.info("모든 제품이 성공적으로 업로드되었습니다!")
            return 0
        else:
            logger.warning(f"{results['failed_products']}개 제품 업로드에 실패했습니다.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 업로드가 중단되었습니다.")
        return 1
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
        return 1


if __name__ == '__main__':
    main()