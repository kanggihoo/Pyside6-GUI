#!/usr/bin/env python3
"""
초기 데이터 업로드 스크립트
로컬 데이터 디렉토리의 모든 파일을 AWS S3와 DynamoDB로 업로드합니다.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# 현재 스크립트 경로 기준으로 aws_manager 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent))
from aws_manager import create_aws_manager , AWSManager


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
    
    def __init__(self, data_root_path: str, aws_manager:AWSManager):
        """
        초기화
        
        Args:
            data_root_path: 로컬 데이터 루트 경로 (1005 디렉토리 포함)
            aws_manager: AWS Manager 인스턴스
        """
        self.data_root_path = Path(data_root_path)
        self.aws_manager:AWSManager = aws_manager
        
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

        # 새로운 제품 카운트 관리 (메타데이터 업데이트용)
        self.new_product_counts = {}  # {f"{main_category}_{sub_category}": count}
        
        # 지원하는 이미지 확장자
        self.image_extensions = {'.jpg', '.jpeg', '.png'}
        
        logger.info(f"초기 업로더 초기화 완료 - 데이터 경로: {self.data_root_path}")
    
    def _update_new_product_count(self, main_category: str, sub_category: int):
        """새로운 제품 카운트를 증가시킵니다."""
        key = f"{main_category}_{sub_category}"
        self.new_product_counts[key] = self.new_product_counts.get(key, 0) + 1

    def _update_all_category_stats(self):
        """모든 카테고리의 상태 통계를 한 번에 업데이트합니다."""
        for key, count in self.new_product_counts.items():
            if count > 0:
                main_category, sub_category = key.split('_')
                sub_category = int(sub_category)
                
                # 카테고리 상태 통계가 없으면 초기화
                if not self.aws_manager.get_category_status_stats(main_category, sub_category):
                    self.aws_manager.initialize_category_status_stats(main_category, sub_category)
                    logger.info(f"카테고리 상태 통계 초기화: {main_category}-{sub_category}")
                
                # PENDING 상태로 한 번에 추가
                self.aws_manager.update_category_status_stats_atomic(
                    main_category, sub_category, {'PENDING': count}
                )
                logger.info(f"카테고리 {main_category}-{sub_category}에 {count}개 제품 추가됨")

    def discover_products(self) -> List[Dict[str, Any]]:
        """
        로컬 데이터 디렉토리에서 제품 정보를 발견합니다. \n
        서브카테고리 Id , 서브 카테고리 안의 제품 Id , 제품 디렉토리 경로, meta.json 파일 담은 리스트 반환 및 메인/서브 카테고리별 제품 수 통계 정보 반환
        
        Returns:
            List[Dict]: 발견된 제품 정보 리스트
        example : 
            [
                {
                    "main_category": "TOP",
                    "sub_category": 1005,
                    "product_id": "674732",
                    "local_path": "TOP/1005/674732",
                    "meta_file": "TOP/1005/674732/meta.json"
                }
            ]
        
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
    
    def validate_meta_file(self, meta_file_path: Path) -> bool:
        """
        meta.json 파일의 유효성을 검사합니다.
        
        Args:
            meta_file_path: meta.json 파일 경로
            
        Returns:
            bool: 파일이 유효한 JSON인지 여부
        """
        try:
            with open(meta_file_path, 'r', encoding='utf-8') as f:
                json.load(f)  # JSON 유효성만 확인
            return True
        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 실패 {meta_file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"메타 파일 검증 실패 {meta_file_path}: {e}")
            return False
    
    def get_files_to_upload(self, product_dir: Path) -> List[Dict[str, Any]]:
        """
        업로드할 파일 목록을 생성합니다.(이미지 파일 , 메타 데이터인 meta.json 파일 구분)
        
        Args:
            product_dir: 제품 디렉토리 경로
            example : 
                Path('TOP/1005/674732')
        Returns:
            List[Dict]: 업로드할 파일 정보 리스트
            example : 
                [
                    {
                        "local_path": "~/.../TOP/1005/674732/detail/1.jpg",
                        "relative_path": "detail/1.jpg",
                        "file_type": "image",
                        "size": 1024
                    },
                    {
                        "local_path": "~/.../TOP/1005/674732/meta.json",
                        "relative_path": "meta.json",
                        "file_type": "meta",
                        "size": 1024
                    }
                ]
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
                    'local_path': file_path, # 로컬 데이터 루트 경로 기준(절대 경로)
                    'relative_path': str(relative_path), # 상대경로(text/파일명 , segment/파일명 , meta.json))
                    'file_type': file_type, # 파일 타입
                    'size': file_path.stat().st_size # 파일 크기
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
                example : 
                    [
                        {
                            "local_path": "~/.../TOP/1005/674732/detail/1.jpg",
                            "relative_path": "detail/1.jpg",
                            "file_type": "image",
                            "size": 1024
                        },
                        {
                            "local_path": "~/.../TOP/1005/674732/meta.json",
                            "relative_path": "meta.json",
                            "file_type": "meta",
                            "size": 1024
                        }
                    ]
        Returns:
            Dict[str, int]: 업로드 결과 통계
            example : 
                {
                    "success": 10,
                    "failed": 2
                }
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
    
    def create_dynamodb_item(self, main_category: str, sub_category: int, product_id: str, 
                           image_file_lists: Dict[str, List[str]] = None) -> tuple[bool, bool]:
        """
        DynamoDB에 제품 아이템을 생성합니다. (파일 리스트 포함)
        
        Args:
            main_category: 메인 카테고리
            sub_category: 서브 카테고리 ID
            product_id: 제품 ID
            image_file_lists: 폴더별 이미지 파일명 리스트
                example : 
                    {
                        "text" : ["1.jpg", "2.jpg"],
                        "summary" : ["1.jpg", "2.jpg"],
                        "segment" : ["1.jpg", "2.jpg"],
                        "detail" : ["1.jpg", "2.jpg"]
                    }
            
        Returns:
            tuple[bool, bool]: (처리 성공 여부, 새 제품 여부)
        """
        try:
            # DynamoDB 아이템 생성 (파일 리스트 포함)
            success, is_new_product = self.aws_manager.create_product_item(
                main_category, sub_category, product_id, image_file_lists
            )
            
            if success:
                if is_new_product:
                    logger.info(f"DynamoDB 새 아이템 생성 성공: {main_category}-{sub_category}-{product_id}")
                else:
                    logger.info(f"DynamoDB 기존 아이템 업데이트 성공: {main_category}-{sub_category}-{product_id}")
                
                total_images = sum(len(files) for files in image_file_lists.values())
                non_empty_folders = [folder for folder, files in image_file_lists.items() if files]
                empty_folders = [folder for folder, files in image_file_lists.items() if not files]
                
                logger.info(f"파일 리스트 포함 저장 완료: {total_images}개 이미지")
                if non_empty_folders:
                    logger.debug(f"이미지가 있는 폴더: {non_empty_folders}")
                if empty_folders:
                    logger.debug(f"빈 폴더: {empty_folders}")
            
            return success, is_new_product
            
        except Exception as e:
            logger.error(f"DynamoDB 아이템 처리 중 오류 {main_category}-{sub_category}-{product_id}: {e}")
            return False, False
    

    
    def upload_single_product(self, product_info: Dict[str, Any]) -> bool:
        """
        단일 제품_id 폴더 안의 모든 파일을 s3에 업로드합니다.(이미지 , meta.json 파일) \n
        업로드 한 제품 id에서 대해서는 DynamoDB에 아이템을 생성(기본 제품_id , sub_category , main_category) \n
        업로드 성공 시 카테고리 메타데이터도 업데이트합니다.
        
        Args:
            product_info: 제품 정보 \n
            example :
                {
                    "main_category": "TOP",
                    "sub_category": 1005,
                    "product_id": "674732",
                    "local_path": "TOP/1005/674732",
                    "meta_file": "TOP/1005/674732/meta.json"
                } 
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
            # 1. 업로드할 파일 목록 생성
            files_to_upload = self.get_files_to_upload(product_dir)
            logger.info(f"업로드할 파일 개수: {len(files_to_upload)}")
            
            # 2. 이미지 파일들을 폴더별로 분류 (DynamoDB 저장용)
            image_file_lists = self.classify_image_files_by_folder(files_to_upload)
            
            # 3. DynamoDB에 아이템 생성 (파일 리스트 포함)
            db_success, is_new_product = self.aws_manager.create_product_item(
                main_category, sub_category, product_id, image_file_lists
            )

            if not is_new_product:
                logger.info(f"이미 존재하는 제품으로 S3에 업로드 하지 않음: {main_category}-{sub_category}-{product_id}")
                return True
            else:
                # 새 제품인 경우 카운트 증가
                self._update_new_product_count(main_category, sub_category)
            
            # 4. 메타 데이터 파일 유효성 검사(meta.json 파일)
            if not self.validate_meta_file(meta_file):
                logger.error(f"메타 데이터 파일 유효성 검사 실패: {product_id}")
                return False
            
            # 5. 새 제품인 경우 S3에 파일 업로드
            upload_stats = self.upload_product_files(main_category, sub_category, product_id, files_to_upload)
            
            # 6. 결과 통계 업데이트
            self.stats['total_files'] += len(files_to_upload)
            self.stats['uploaded_files'] += upload_stats['success']
            self.stats['failed_files'] += upload_stats['failed']
            
            # 전체 성공 여부 판단
            success = (upload_stats['failed'] == 0 and db_success)
            
            if success:
                self.stats['uploaded_products'] += 1
                logger.info(f"새 제품 업로드 완료: {sub_category}-{product_id}")
            else:
                self.stats['failed_products'] += 1
                logger.error(f"제품 업로드 실패: {sub_category}-{product_id}")
            
            return success
            
        except Exception as e:
            self.stats['failed_products'] += 1
            logger.error(f"제품 업로드 중 예상치 못한 오류 {sub_category}-{product_id}: {e}")
            return False
    
    def classify_image_files_by_folder(self, files_to_upload: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        업로드할 파일들 중 이미지 파일만 폴더별로 분류합니다.
        모든 지원 폴더에 대해 빈 리스트라도 포함하여 일관된 스키마를 유지합니다.
        
        Args:
            files_to_upload: 업로드할 파일 정보 리스트
            example : 
                [
                    {
                        "local_path": "~/.../TOP/1005/674732/detail/1.jpg",
                        "relative_path": "detail/1.jpg",
                        "file_type": "image",
                        "size": 1024
                    }
                ]
                
        Returns:
            Dict[str, List[str]]: 폴더별 이미지 파일명 리스트 (빈 폴더 포함)
            example : 
                {
                    "detail": ["1.jpg", "2.jpg"],
                    "summary": ["1.jpg", "2.jpg"],
                    "segment": ["1.jpg", "2.jpg"],
                    "text": ["1.jpg", "2.jpg"]
                }
        """
        supported_folders = ['detail', 'summary', 'segment', 'text']
        # 모든 지원 폴더를 빈 리스트로 초기화
        image_file_lists = {folder: [] for folder in supported_folders}
        
        for file_info in files_to_upload:
            if file_info['file_type'] != 'image':
                continue
            
            relative_path = file_info['relative_path']
            path_parts = relative_path.split('/')
            
            # 폴더 구조 분석: folder/filename 또는 filename
            if len(path_parts) == 2:  # folder/filename
                folder = path_parts[0]
                filename = path_parts[1]
                
                # 지원하는 폴더이고 이미지 파일인 경우에만 추가
                if (folder in supported_folders and 
                    any(filename.lower().endswith(ext) for ext in self.image_extensions)):
                    
                    image_file_lists[folder].append(filename)
                    logger.debug(f"이미지 파일 분류: {folder}/{filename}")

        # 빈 폴더도 포함하여 반환
        return image_file_lists
    
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
        
        # 각 제품 업로드
        for i, product_info in enumerate(products, 1):
            logger.info(f"진행률: {i}/{len(products)} ({i/len(products)*100:.1f}%)")
            
            success = self.upload_single_product(product_info)
            
            if not success:
                logger.warning(f"제품 업로드 실패: {product_info['product_id']}")
            
            # 진행률 로그 (매 10개마다)
            if i % 10 == 0:
                logger.info(f"중간 통계 - 성공: {self.stats['uploaded_products']}, 실패: {self.stats['failed_products']}")
        
        # 모든 제품 업로드 완료 후 카테고리 상태 통계 한 번에 업데이트
        self._update_all_category_stats()
        
        # 최종 통계
        self.stats['end_time'] = datetime.now()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("=" * 60)
        logger.info("전체 제품 업로드 완료!")
        logger.info(f"총 소요 시간: {duration}")
        logger.info(f"총 제품 수: {self.stats['total_products']}")
        logger.info(f"성공한 제품 수: {self.stats['uploaded_products']}")
        logger.info(f"실패한 제품 수: {self.stats['failed_products']}")
        logger.info(f"총 파일 수: {self.stats['total_files']}")
        logger.info(f"성공한 파일 수: {self.stats['uploaded_files']}")
        logger.info(f"실패한 파일 수: {self.stats['failed_files']}")
        
        # 최종 카테고리 상태 통계 확인
        try:
            # 업로드된 카테고리의 상태 통계 확인
            main_category = self.data_root_path.name
            all_stats = self.aws_manager.get_all_category_status_stats()
            
            if all_stats:
                total_products_in_stats = sum(stats.get('total', 0) for stats in all_stats.values())
                logger.info(f"최종 상태 통계 - 총 제품 수: {total_products_in_stats}")
                
                # 메인 카테고리별 통계 출력
                for category_key, stats in all_stats.items():
                    if category_key.startswith(main_category):
                        logger.info(f"카테고리 {category_key}: 전체 {stats['total']} | 미정 {stats['pending']} | 완료 {stats['completed']} | 보류 {stats['pass']}")
            else:
                logger.warning("상태 통계 데이터를 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"최종 상태 통계 확인 중 오류: {e}")
        
        logger.info("=" * 60)
        
        return self.stats
    



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
    
    try:
        # 데이터 경로 확인
        HOME_DIR = os.getcwd()
        data_path = Path(HOME_DIR) / args.data_path
        main_category = args.data_path
        if not data_path.exists():
            logger.error(f"데이터 경로가 존재하지 않습니다: {data_path}")
            return 1
        
        # AWS Manager 생성
        logger.info("AWS Manager 초기화 중...")
        aws_manager = create_aws_manager(
            region_name=args.region,

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