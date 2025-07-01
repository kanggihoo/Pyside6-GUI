#!/usr/bin/env python3
"""
이미지 캐시 관리
S3에서 로드한 썸네일 이미지를 로컬에 캐싱하여 성능을 향상시킵니다.
"""

import os
import hashlib
import requests
from pathlib import Path
from typing import Optional
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
import logging

logger = logging.getLogger(__name__)


class ImageDownloadThread(QThread):
    """이미지 다운로드 스레드"""
    
    image_downloaded = Signal(str, QPixmap)  # url, pixmap
    download_failed = Signal(str, str)  # url, error_message
    
    def __init__(self, url: str, cache_path: str):
        super().__init__()
        self.url = url
        self.cache_path = cache_path
    
    def run(self):
        """스레드 실행"""
        try:
            # HTTP 요청으로 이미지 다운로드
            response = requests.get(self.url, timeout=10, stream=True)
            response.raise_for_status()
            
            # 캐시 디렉토리 생성
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            # 파일로 저장
            with open(self.cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # QPixmap으로 로드
            pixmap = QPixmap(self.cache_path)
            if not pixmap.isNull():
                self.image_downloaded.emit(self.url, pixmap)
            else:
                logger.error(f"QPixmap 로드 실패 (null pixmap): {self.url[:100]}...")
                self.download_failed.emit(self.url, "이미지 형식 오류")
                
        except requests.RequestException as e:
            logger.error(f"HTTP 요청 실패: {self.url[:100]}... - {e}")
            self.download_failed.emit(self.url, str(e))
        except Exception as e:
            logger.error(f"예상치 못한 오류: {self.url[:100]}... - {e}")
            self.download_failed.emit(self.url, str(e))


class ImageCache:
    """이미지 캐시 관리 클래스"""
    
    def __init__(self, cache_dir: str = None, max_cache_size_mb: int = 500):
        """
        이미지 캐시 초기화
        
        Args:
            cache_dir: 캐시 디렉토리 경로 (None이면 임시 디렉토리 사용)
            max_cache_size_mb: 최대 캐시 크기 (MB)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.cache' / 'ai_dataset_curation' / 'images'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # MB to bytes
        self.memory_cache = {}  # URL -> QPixmap
        self.download_threads = {}  # URL -> QThread
        self.mutex = QMutex()
    
    def get_image(self, url: str, callback=None) -> Optional[QPixmap]:
        """
        이미지를 캐시에서 가져오거나 다운로드합니다.
        
        Args:
            url: 이미지 URL (HTTP/HTTPS 또는 file://)
            callback: 다운로드 완료 시 호출할 콜백 함수 (url, pixmap)
            
        Returns:
            QPixmap: 캐시된 이미지 (즉시 사용 가능한 경우)
        """
        with QMutexLocker(self.mutex):
            # 로컬 파일 URL 처리 (file://)
            if url.startswith('file://'):
                return self._load_local_file(url, callback)
            
            # 1. 메모리 캐시 확인
            if url in self.memory_cache:
                return self.memory_cache[url]
            
            # 2. 파일 캐시 확인
            cache_path = self._get_cache_path(url)
            if cache_path.exists():
                try:
                    pixmap = QPixmap(str(cache_path))
                    if not pixmap.isNull():
                        self.memory_cache[url] = pixmap
                        return pixmap
                except Exception as e:
                    logger.warning(f"캐시된 이미지 로드 실패 {url}: {e}")
                    cache_path.unlink(missing_ok=True)
            
            # 3. 다운로드 시작 (이미 진행 중이 아닌 경우)
            if url not in self.download_threads:
                self._start_download(url, cache_path, callback)
            
            return None
    
    def _get_cache_path(self, url: str) -> Path:
        """URL에 대한 캐시 파일 경로 생성"""
        # URL을 해시하여 파일명 생성
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 파일 확장자 추출
        if url.lower().endswith(('.jpg', '.jpeg')):
            ext = '.jpg'
        elif url.lower().endswith('.png'):
            ext = '.png'
        elif url.lower().endswith('.gif'):
            ext = '.gif'
        elif url.lower().endswith('.webp'):
            ext = '.webp'
        else:
            ext = '.jpg'  # 기본값
        
        return self.cache_dir / f"{url_hash}{ext}"
    
    def _start_download(self, url: str, cache_path: Path, callback=None):
        """이미지 다운로드 시작"""
        download_thread = ImageDownloadThread(url, str(cache_path))
        
        # 콜백 저장 (lambda 변수 캡처 문제 해결)
        def on_success(u, p):
            self._on_download_completed(u, p, callback)
        
        def on_failure(u, e):
            self._on_download_failed(u, e, callback)
        
        def on_finished():
            self._cleanup_thread(url)
        
        # 시그널 연결
        download_thread.image_downloaded.connect(on_success)
        download_thread.download_failed.connect(on_failure)
        download_thread.finished.connect(on_finished)
        
        self.download_threads[url] = download_thread
        download_thread.start()
    
    def _on_download_completed(self, url: str, pixmap: QPixmap, callback=None):
        """다운로드 완료 처리"""
        with QMutexLocker(self.mutex):
            self.memory_cache[url] = pixmap
        
        if callback:
            try:
                # 위젯이 삭제되었는지 확인
                if hasattr(callback, '__self__'):
                    widget = callback.__self__
                    if hasattr(widget, '_is_destroyed') and widget._is_destroyed:
                        logger.warning(f"위젯이 이미 삭제됨, 콜백 건너뜀: {url[:100]}...")
                        return
                
                callback(url, pixmap)
                
            except RuntimeError as e:
                if "already deleted" in str(e) or "Internal C++ object" in str(e):
                    logger.warning(f"위젯 삭제로 인한 콜백 건너뜀: {url[:100]}...")
                else:
                    logger.error(f"콜백 호출 런타임 오류: {url[:100]}... - {str(e)}")
            except Exception as e:
                logger.error(f"콜백 호출 오류: {url[:100]}... - {str(e)}")
        
        # 캐시 크기 관리
        self._manage_cache_size()
    
    def _on_download_failed(self, url: str, error_message: str, callback=None):
        """다운로드 실패 처리"""
        logger.error(f"이미지 다운로드 실패: {url[:100]}... - {error_message}")
        
        if callback:
            try:
                callback(url, None)
            except Exception as e:
                logger.error(f"실패 콜백 호출 오류: {url[:100]}... - {str(e)}")
    
    def _cleanup_thread(self, url: str):
        """다운로드 스레드 정리"""
        with QMutexLocker(self.mutex):
            if url in self.download_threads:
                thread = self.download_threads.pop(url)
                if thread:
                    thread.deleteLater()
    
    def _manage_cache_size(self):
        """캐시 크기 관리"""
        try:
            # 캐시 디렉토리의 총 크기 계산
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            
            if total_size > self.max_cache_size:
                # 파일들을 수정 시간 순으로 정렬 (오래된 것부터)
                files = [(f, f.stat().st_mtime) for f in self.cache_dir.rglob('*') if f.is_file()]
                files.sort(key=lambda x: x[1])
                
                # 캐시 크기가 제한 이하가 될 때까지 오래된 파일 삭제
                for file_path, _ in files:
                    if total_size <= self.max_cache_size * 0.8:  # 20% 여유 확보
                        break
                    
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        total_size -= file_size
                        
                        # 메모리 캐시에서도 제거
                        url_to_remove = None
                        for url, pixmap in self.memory_cache.items():
                            if self._get_cache_path(url) == file_path:
                                url_to_remove = url
                                break
                        
                        if url_to_remove:
                            del self.memory_cache[url_to_remove]
                            
                    except Exception as e:
                        logger.warning(f"캐시 파일 삭제 실패 {file_path}: {e}")
                
                logger.info(f"캐시 정리 완료. 현재 크기: {total_size / 1024 / 1024:.1f}MB")
                
        except Exception as e:
            logger.error(f"캐시 크기 관리 중 오류: {e}")
    
    def preload_images(self, urls: list):
        """이미지 목록을 미리 로드"""
        for url in urls:
            self.get_image(url)
    
    def clear_cache(self):
        """캐시 정리"""
        # 메모리 캐시 정리
        with QMutexLocker(self.mutex):
            self.memory_cache.clear()
        
        # 다운로드 스레드 정리
        for url, thread in list(self.download_threads.items()):
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(1000)  # 1초 대기
            self._cleanup_thread(url)
        
        # 파일 캐시 정리
        try:
            for file_path in self.cache_dir.rglob('*'):
                if file_path.is_file():
                    file_path.unlink()
            
            logger.info("이미지 캐시가 정리되었습니다.")
            
        except Exception as e:
            logger.error(f"캐시 정리 중 오류: {e}")
    
    def get_cache_info(self) -> dict:
        """캐시 정보 반환"""
        try:
            file_count = len(list(self.cache_dir.rglob('*')))
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            memory_count = len(self.memory_cache)
            
            return {
                'cache_dir': str(self.cache_dir),
                'file_count': file_count,
                'total_size_mb': total_size / 1024 / 1024,
                'memory_cache_count': memory_count,
                'max_size_mb': self.max_cache_size / 1024 / 1024
            }
            
        except Exception as e:
            logger.error(f"캐시 정보 조회 중 오류: {e}")
            return {}
    
    def _load_local_file(self, file_url: str, callback=None) -> Optional[QPixmap]:
        """로컬 파일 URL (file://) 처리"""
        try:
            # file:// 제거하고 로컬 경로 추출
            local_path = file_url.replace('file://', '')
            
            # 메모리 캐시 확인
            if file_url in self.memory_cache:
                return self.memory_cache[file_url]
            
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
                self.memory_cache[file_url] = pixmap
                
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