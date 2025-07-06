#!/usr/bin/env python3
"""
이미지 캐시 관리 (개선된 버전)
S3에서 로드한 이미지를 제품 ID 기반으로 로컬에 캐싱하여 성능을 향상시킵니다.
페이지 단위로 캐시를 관리하여 메모리와 저장 공간을 효율적으로 사용합니다.
"""

import os
import shutil
import requests
import json
from pathlib import Path
from typing import Optional, List, Dict, Callable
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
import logging

logger = logging.getLogger(__name__)


class PageImageDownloadThread(QThread):
    """페이지별 이미지 배치 다운로드 스레드"""
    
    progress_updated = Signal(int, int)  # current, total
    image_downloaded = Signal(str, str, str)  # product_id, folder, filename
    download_completed = Signal()
    download_failed = Signal(str)  # error_message
    
    def __init__(self, download_tasks: List[Dict], cache_dir: Path):
        super().__init__()
        self.download_tasks = download_tasks  # [{'product_id': str, 'folder': str, 'filename': str, 'url': str}]
        self.cache_dir = cache_dir
        self._stop_requested = False
    
    def run(self):
        """스레드 실행"""
        try:
            total_tasks = len(self.download_tasks)
            logger.info(f"시작: 총 {total_tasks}개 이미지 다운로드")
            
            for i, task in enumerate(self.download_tasks):
                if self._stop_requested:
                    break
                
                try:
                    product_id = task['product_id']
                    folder = task['folder']
                    filename = task['filename']
                    url = task['url']
                    
                    logger.debug(f"다운로드 시도 [{i+1}/{total_tasks}]: {product_id}/{folder}/{filename}")
                    logger.debug(f"URL: {url}")
                    
                    # meta.json인 경우 특별 처리
                    if folder == 'meta' and filename == 'meta.json':
                        cache_path = self.cache_dir / product_id / filename
                    else:
                        # 캐시 경로 생성
                        cache_path = self.cache_dir / product_id / folder / filename
                    
                    # 이미 존재하면 건너뛰기
                    if cache_path.exists():
                        logger.debug(f"이미 캐시됨: {cache_path}")
                        self.image_downloaded.emit(product_id, folder, filename)
                        self.progress_updated.emit(i + 1, total_tasks)
                        continue
                    
                    # 디렉토리 생성
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"캐시 경로 생성: {cache_path}")
                    
                    # HTTP 요청으로 파일 다운로드
                    logger.debug(f"HTTP GET 요청 시작: {url}")
                    response = requests.get(url, timeout=30, stream=True)
                    response.raise_for_status()
                    logger.debug(f"HTTP 응답 성공: {response.status_code}")
                    
                    # 파일로 저장
                    with open(cache_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self._stop_requested:
                                break
                            f.write(chunk)
                    
                    logger.debug(f"파일 저장 완료: {cache_path}")
                    
                    if not self._stop_requested:
                        self.image_downloaded.emit(product_id, folder, filename)
                    
                    self.progress_updated.emit(i + 1, total_tasks)
                    
                except Exception as e:
                    logger.error(f"이미지 다운로드 실패 {task}: {e}")
                    continue
            
            if not self._stop_requested:
                logger.info("모든 이미지 다운로드 완료")
                self.download_completed.emit()
                
        except Exception as e:
            logger.error(f"배치 다운로드 중 오류: {e}")
            self.download_failed.emit(str(e))
    
    def stop(self):
        """다운로드 중지"""
        self._stop_requested = True


class ProductImageCache:
    """제품 기반 이미지 캐시 관리 클래스"""
    
    def __init__(self, cache_dir: str = None, max_cache_size_mb: int = 1000):
        """
        이미지 캐시 초기화
        
        Args:
            cache_dir: 캐시 디렉토리 경로 (None이면 홈 디렉토리 사용)
            max_cache_size_mb: 최대 캐시 크기 (MB)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.cache' / 'ai_dataset_curation' / 'product_images'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # MB to bytes
        self.memory_cache = {}  # (product_id, folder, filename) -> QPixmap
        self.current_page_products = set()  # 현재 페이지의 제품 ID들
        self.download_thread = None
        self.mutex = QMutex()
    
    def set_current_page_products(self, product_ids: List[str]):
        """현재 페이지의 제품 ID들 설정"""
        with QMutexLocker(self.mutex):
            self.current_page_products = set(product_ids)
    
    def download_page_images(self, download_tasks: List[Dict], 
                           progress_callback: Callable[[int, int], None] = None,
                           completed_callback: Callable[[], None] = None) -> bool:
        """
        페이지의 모든 이미지를 배치 다운로드(내부적으로 QThread 사용)
        
        Args:
            download_tasks: 다운로드 작업 목록
            progress_callback: 진행률 콜백 (current, total)
            completed_callback: 완료 콜백
            
        Returns:
            bool: 다운로드 시작 성공 여부
        """
        try:
            # 이전 다운로드 스레드가 실행 중이면 중지
            if self.download_thread and self.download_thread.isRunning():
                self.download_thread.stop()
                self.download_thread.wait(3000)
            
            # 새 다운로드 스레드 생성
            self.download_thread = PageImageDownloadThread(download_tasks, self.cache_dir)
            
            # 시그널 연결
            if progress_callback:
                self.download_thread.progress_updated.connect(progress_callback) # (current, total)
            
            if completed_callback:
                self.download_thread.download_completed.connect(completed_callback) # 다운로드 완료 시그널 연결
            
            self.download_thread.download_failed.connect(
                lambda error: logger.error(f"페이지 이미지 다운로드 실패: {error}")
            )
            
            # 다운로드 시작
            self.download_thread.start()
            return True
            
        except Exception as e:
            logger.error(f"페이지 이미지 다운로드 시작 실패: {e}")
            return False
    
    def get_product_image(self, product_id: str, folder: str, filename: str) -> Optional[QPixmap]:
        """
        제품 이미지를 캐시에서 가져오기
        
        Args:
            product_id: 제품 ID
            folder: 폴더명 (detail, segment, summary, text)
            filename: 파일명
            
        Returns:
            QPixmap: 캐시된 이미지 (없으면 None)
        """
        cache_key = (product_id, folder, filename)
        
        with QMutexLocker(self.mutex):
            # 1. 메모리 캐시 확인
            if cache_key in self.memory_cache:
                return self.memory_cache[cache_key]
        
        # 2. 파일 캐시 확인
        cache_path = self.cache_dir / product_id / folder / filename
        if cache_path.exists():
            try:
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    with QMutexLocker(self.mutex):
                        self.memory_cache[cache_key] = pixmap
                    return pixmap
            except Exception as e:
                logger.warning(f"캐시된 이미지 로드 실패 {cache_path}: {e}")
        
        return None
    
    def get_product_meta_json(self, product_id: str) -> Optional[Dict]:
        """
        제품의 meta.json 파일을 캐시에서 가져오기
        
        Args:
            product_id: 제품 ID
            
        Returns:
            Dict: meta.json 데이터 (없으면 None)
        """
        try:
            cache_path = self.cache_dir / product_id / 'meta.json'
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"meta.json 파일 로드 실패 {product_id}: {e}")
        
        return None
    
    def get_product_images(self, product_id: str) -> Dict[str, List[Dict[str, str]]]:
        """
        현재 product_id의 모든 폴더(detail , segment , summary , text) 내의 이미지 정보 반환
        
        Args:
            product_id: 제품 ID
            
        Returns:
            Dict: 폴더별 이미지 정보 {folder: [{'filename': str, 'path': str}]}
            example : 
            {
                'detail': [{'filename': '0.jpg', 'path': 'detail/0.jpg'}],
                'segment': [{'filename': '0.jpg', 'path': 'segment/0.jpg'}],
                'summary': [{'filename': '0.jpg', 'path': 'summary/0.jpg'}],
                'text': [{'filename': '0.jpg', 'path': 'text/0.jpg'}]
            }
        """
        result = {}
        product_cache_dir = self.cache_dir / product_id
        
        if not product_cache_dir.exists():
            return result
        
        for folder_path in product_cache_dir.iterdir():
            if folder_path.is_dir():
                folder_name = folder_path.name
                result[folder_name] = []
                
                for image_file in folder_path.iterdir():
                    if image_file.is_file() and image_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        result[folder_name].append({
                            'filename': image_file.name,
                            'path': str(image_file)
                        })
        
        return result
    
    def clear_non_current_page_cache(self):
        """현재 페이지가 아닌 제품들의 캐시 정리"""
        try:
            # 메모리 캐시에서 현재 페이지가 아닌 항목 제거
            with QMutexLocker(self.mutex):
                keys_to_remove = []
                for cache_key in self.memory_cache.keys():
                    product_id = cache_key[0]
                    if product_id not in self.current_page_products:
                        keys_to_remove.append(cache_key)
                
                for key in keys_to_remove:
                    del self.memory_cache[key]
            
            # 파일 캐시에서 현재 페이지가 아닌 제품 폴더 삭제
            for product_dir in self.cache_dir.iterdir():
                if product_dir.is_dir() and product_dir.name not in self.current_page_products:
                    try:
                        shutil.rmtree(product_dir)
                        logger.debug(f"제품 캐시 삭제: {product_dir.name}")
                    except Exception as e:
                        logger.warning(f"제품 캐시 삭제 실패 {product_dir.name}: {e}")
            
            logger.info(f"페이지 캐시 정리 완료. 현재 페이지 제품 수: {len(self.current_page_products)}")
            
        except Exception as e:
            logger.error(f"페이지 캐시 정리 중 오류: {e}")
    
    def clear_all_cache(self):
        """모든 캐시 정리"""
        try:
            # 다운로드 스레드 중지
            if self.download_thread and self.download_thread.isRunning():
                self.download_thread.stop()
                self.download_thread.wait(3000)
            
            # 메모리 캐시 정리
            with QMutexLocker(self.mutex):
                self.memory_cache.clear()
                self.current_page_products.clear()
            
            # 파일 캐시 정리
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("모든 이미지 캐시가 정리되었습니다.")
            
        except Exception as e:
            logger.error(f"캐시 정리 중 오류: {e}")
    
    def get_cache_info(self) -> Dict:
        """캐시 정보 반환"""
        try:
            total_size = 0
            file_count = 0
            product_count = 0
            
            if self.cache_dir.exists():
                for product_dir in self.cache_dir.iterdir():
                    if product_dir.is_dir():
                        product_count += 1
                        for file_path in product_dir.rglob('*'):
                            if file_path.is_file():
                                file_count += 1
                                total_size += file_path.stat().st_size
            
            memory_count = len(self.memory_cache)
            
            return {
                'cache_dir': str(self.cache_dir),
                'product_count': product_count,
                'file_count': file_count,
                'total_size_mb': total_size / 1024 / 1024,
                'memory_cache_count': memory_count,
                'max_size_mb': self.max_cache_size / 1024 / 1024,
                'current_page_products': len(self.current_page_products)
            }
            
        except Exception as e:
            logger.error(f"캐시 정보 조회 중 오류: {e}")
            return {}
    
    def cleanup(self):
        """정리 작업"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(3000)

    def get_image(self, url: str, callback=None) -> Optional[QPixmap]:
        """
        기존 ImageCache와의 호환성을 위한 래퍼 메서드
        
        Args:
            url: 이미지 URL (HTTP/HTTPS 또는 file://)
            callback: 다운로드 완료 시 호출할 콜백 함수 (url, pixmap)
            
        Returns:
            QPixmap: 캐시된 이미지 (즉시 사용 가능한 경우)
        """
        try:
            # file:// URL 처리
            if url.startswith('file://'):
                return self._load_local_file(url, callback)
            
            # HTTP/HTTPS URL의 경우 원래 방식 사용 (폴백)
            # URL에서 제품 정보 추출 시도
            if '/detail/' in url or '/segment/' in url or '/summary/' in url or '/text/' in url:
                # S3 URL 패턴 분석 시도
                try:
                    # URL에서 파일명 추출
                    filename = url.split('/')[-1].split('?')[0]  # 쿼리 파라미터 제거
                    
                    # 폴더 추출
                    if '/detail/' in url:
                        folder = 'detail'
                    elif '/segment/' in url:
                        folder = 'segment'
                    elif '/summary/' in url:
                        folder = 'summary'
                    elif '/text/' in url:
                        folder = 'text'
                    else:
                        folder = 'unknown'
                    
                    # 제품 ID 추출 시도 (현재 페이지 제품들에서 찾기)
                    for product_id in self.current_page_products:
                        pixmap = self.get_product_image(product_id, folder, filename)
                        if pixmap:
                            if callback:
                                callback(url, pixmap)
                            return pixmap
                    
                except Exception as e:
                    logger.debug(f"URL 파싱 실패, 폴백 모드 사용: {e}")
            
            # 캐시에서 찾을 수 없는 경우 None 반환
            if callback:
                callback(url, None)
            return None
            
        except Exception as e:
            logger.error(f"get_image 호환성 메서드 오류: {e}")
            if callback:
                callback(url, None)
            return None
    
    def _load_local_file(self, file_url: str, callback=None) -> Optional[QPixmap]:
        """로컬 파일 URL (file://) 처리"""
        try:
            # file:// 제거하고 로컬 경로 추출
            local_path = file_url.replace('file://', '')
            
            # 메모리 캐시 확인 (file URL을 키로 사용)
            cache_key = ('file', local_path, '')
            with QMutexLocker(self.mutex):
                if cache_key in self.memory_cache:
                    pixmap = self.memory_cache[cache_key]
                    if callback:
                        callback(file_url, pixmap)
                    return pixmap
            
            # 파일 존재 확인
            if not os.path.exists(local_path):
                logger.warning(f"로컬 파일이 존재하지 않습니다: {local_path}")
                if callback:
                    callback(file_url, None)
                return None
            
            # 픽스맵 로드
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                # 메모리 캐시에 저장
                with QMutexLocker(self.mutex):
                    self.memory_cache[cache_key] = pixmap
                
                # 콜백 호출
                if callback:
                    callback(file_url, pixmap)
                
                return pixmap
            else:
                logger.warning(f"로컬 이미지 로드 실패: {local_path}")
                if callback:
                    callback(file_url, None)
                return None
                
        except Exception as e:
            logger.error(f"로컬 파일 로드 오류 {file_url}: {str(e)}")
            if callback:
                callback(file_url, None)
            return None


# 하위 호환성을 위한 별칭
ImageCache = ProductImageCache 