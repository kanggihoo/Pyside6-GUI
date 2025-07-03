#!/usr/bin/env python3
"""
이미지 관련 위젯 클래스들을 모아놓은 모듈
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPen
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class PlaceholderImageWidget(QWidget):
    """선택되지 않은 대표 이미지를 위한 플레이스홀더 위젯"""
    
    def __init__(self, image_type: str):
        super().__init__()
        self.image_type = image_type
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # 타입 레이블
        type_frame = QFrame()
        type_frame.setStyleSheet("background-color: #e9ecef; color: #6c757d; border-radius: 3px; border: 2px dashed #ced4da;")
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(5, 2, 5, 2)
        
        # 타입 표시
        display_text = self.get_type_display_name()
        type_label = QLabel(display_text)
        type_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 10px; background-color: transparent;")
        type_layout.addWidget(type_label)
        
        # 선택 필요 표시
        need_label = QLabel("선택 필요")
        need_label.setStyleSheet("color: #dc3545; font-size: 9px; background-color: transparent;")
        type_layout.addWidget(need_label)
        
        layout.addWidget(type_frame)
        
        # 플레이스홀더 이미지
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(120, 120)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ced4da;
                border-radius: 5px;
                background-color: #f8f9fa;
                color: #6c757d;
            }
        """)
        
        # 플레이스홀더 이미지 생성
        self.create_placeholder_image()
        layout.addWidget(self.image_label)
        
        # 안내 텍스트
        guide_label = QLabel("이미지를 선택해주세요")
        guide_label.setAlignment(Qt.AlignCenter)
        guide_label.setWordWrap(True)
        guide_label.setStyleSheet("font-size: 9px; color: #6c757d; background-color: transparent; padding: 2px;")
        layout.addWidget(guide_label)
    
    def get_type_display_name(self) -> str:
        """타입 표시명 반환"""
        type_names = {
            'model_wearing': '모델 착용',
            'front_cutout': '정면 누끼',
            'back_cutout': '후면 누끼'
        }
        return type_names.get(self.image_type, self.image_type)
    
    def create_placeholder_image(self):
        """플레이스홀더 이미지 생성"""
        placeholder = QPixmap(120, 120)
        placeholder.fill(QColor(248, 249, 250))  # 연한 회색 배경
        
        painter = QPainter(placeholder)
        painter.setPen(QPen(QColor(108, 117, 125), 2, Qt.DashLine))
        
        # 테두리 그리기
        painter.drawRect(10, 10, 100, 100)
        
        # + 기호 그리기
        painter.setPen(QPen(QColor(108, 117, 125), 3))
        painter.drawLine(60, 40, 60, 80)  # 세로선
        painter.drawLine(40, 60, 80, 60)  # 가로선
        
        painter.end()
        
        self.image_label.setPixmap(placeholder)


class RepresentativeImageWidget(QWidget):
    """대표 이미지 위젯 \n
    - remove_requested : Signal(str) 이미지 제거 요청 시그널 \n
    - image_data : 이미지 데이터(딕셔너리) \n
    - image_key : 이미지 키(문자열) \n
    - image_cache : 이미지 캐시(객체) 
    - is_main_representative : 대표 이미지 여부(불린)
    """
    
    remove_requested = Signal(str)  # 이미지 키
    
    def __init__(self, image_data: Dict[str, Any], image_key: str, is_main_representative: bool = True, image_cache=None):
        super().__init__()
        self.image_data = image_data
        self.image_key = image_key
        self.is_main_representative = is_main_representative
        self.image_cache = image_cache
        self._is_destroyed = False  # 위젯 파괴 상태 추적
        
        self.setup_ui()
        self.load_image()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # 타입 레이블
        type_frame = QFrame()
        type_frame.setStyleSheet("background-color: #e9ecef; color: #6c757d; border-radius: 3px; border: 2px solid #ced4da;")
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(5, 2, 5, 2)
        
        # 타입 표시
        display_text = self.get_type_display_name()
        type_label = QLabel(display_text)
        type_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 10px; background-color: transparent;")
        type_layout.addWidget(type_label)
        
        type_layout.addStretch()
        
        # 제거 버튼
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        remove_btn.clicked.connect(self.on_remove_clicked)
        type_layout.addWidget(remove_btn)
        
        layout.addWidget(type_frame)
        
        # 이미지 표시 프레임
        self.image_frame = QFrame()
        self.image_frame.setFrameStyle(QFrame.Box)
        self.image_frame.setLineWidth(2)
        self.image_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #dee2e6;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
        
        frame_layout = QVBoxLayout(self.image_frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        
        # 이미지 레이블
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: white; 
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        
        frame_layout.addWidget(self.image_label)
        layout.addWidget(self.image_frame)
        
        # 파일명 레이블
        filename = self.image_data.get('filename', self.image_data.get('url', '').split('/')[-1])
        
        # Segment 이미지인 경우 친숙한 표시명 사용
        if self.image_data.get('is_local_segment', False):
            display_name = self.image_data.get('display_name', filename)
            # 표시명이 너무 길면 줄임
            if len(display_name) > 20:
                filename = display_name[:17] + "..."
            else:
                filename = display_name
        else:
            # 일반 이미지는 기존 방식
            if len(filename) > 15:
                filename = filename[:12] + "..."
        
        self.filename_label = QLabel(filename)
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("font-size: 8px; color: #333; background-color: white; max-height: 25px; padding: 2px;")
        layout.addWidget(self.filename_label)
    
    def closeEvent(self, event):
        """위젯 닫힐 때 호출"""
        self._is_destroyed = True
        self.schedule_cleanup()
        super().closeEvent(event)

    def deleteLater(self):
        """위젯 삭제 예정 시 호출"""
        self._is_destroyed = True
        self.schedule_cleanup()
        super().deleteLater()
    
    def schedule_cleanup(self):
        """정리 작업을 지연 실행"""
        if not hasattr(self, '_cleanup_timer') or self._cleanup_timer is None:
            self._cleanup_timer = QTimer()
            self._cleanup_timer.setSingleShot(True)
            self._cleanup_timer.timeout.connect(self.perform_cleanup)
            self._cleanup_timer.start(100)  # 100ms 후 정리 실행
    
    def perform_cleanup(self):
        """실제 정리 작업 수행"""
        try:
            self._is_destroyed = True
            
            # 시그널 연결 해제 - 더 안전한 방식
            if hasattr(self, 'remove_requested'):
                try:
                    self.remove_requested.disconnect()
                except (RuntimeError, TypeError):
                    pass  # 이미 연결 해제된 경우
            
            # 이미지 레이블 정리
            if hasattr(self, 'image_label') and self.image_label:
                try:
                    self.image_label.clear()
                    self.image_label.setPixmap(QPixmap())
                except RuntimeError:
                    pass  # Qt 객체가 이미 삭제된 경우
            
            # 타이머 정리
            if hasattr(self, '_cleanup_timer') and self._cleanup_timer:
                self._cleanup_timer.stop()
                self._cleanup_timer.deleteLater()
                self._cleanup_timer = None
            
        except Exception as e:
            logger.warning(f"RepresentativeImageWidget 정리 중 오류: {str(e)}")
    
    def cleanup(self):
        """위젯 정리 - 메모리 누수 방지 (deprecated - perform_cleanup 사용)"""
        self.perform_cleanup()
    
    def get_type_display_name(self) -> str:
        """타입별 표시명 반환"""
        type_names = {
            'model_wearing': '모델 착용',
            'front_cutout': '정면 누끼',
            'back_cutout': '후면 누끼',
            'color_variant': '제품 색상'
        }
        return type_names.get(self.image_key, self.image_key)
    
    def load_image(self):
        """이미지 로드"""
        if self._is_destroyed:
            return
            
        url = self.image_data.get('url')
        if not url:
            self.set_placeholder_image("URL 없음")
            return
        
        # 로컬 segment 이미지인 경우 직접 로드
        if self.image_data.get('is_local_segment', False):
            self.load_local_segment_image()
            return
        
        if not self.image_cache:
            filename = self.image_data.get('filename', 'unknown')
            logger.error(f"이미지 캐시 없음: {filename}")
            self.set_placeholder_image("캐시 없음")
            return
        
        # 로딩 플레이스홀더 표시
        self.set_placeholder_image("로딩 중...")
        
        # 캐시에서 이미지 가져오기 - 안전한 콜백 사용
        try:
            cached_pixmap = self.image_cache.get_image(url, self.safe_on_image_loaded)
            
            if cached_pixmap:
                self.set_image(cached_pixmap)
            else:
                # 5초 후에도 로딩 중이면 문제가 있다고 가정
                filename = self.image_data.get('filename', 'unknown')
                QTimer.singleShot(5000, lambda: self.check_loading_timeout(filename))
                
        except Exception as e:
            filename = self.image_data.get('filename', 'unknown')
            logger.error(f"이미지 캐시 get_image 호출 오류 {filename}: {str(e)}")
            self.set_placeholder_image("캐시 오류")
    
    def check_loading_timeout(self, filename):
        """로딩 타임아웃 체크"""
        try:
            if not self._is_destroyed and hasattr(self, 'image_label') and self.image_label:
                current_pixmap = self.image_label.pixmap()
                if not current_pixmap or current_pixmap.isNull():
                    self.set_placeholder_image("타임아웃")
        except Exception as e:
            logger.error(f"타임아웃 체크 오류: {str(e)}")
    
    def load_local_segment_image(self):
        """로컬 segment 이미지 직접 로드"""
        try:
            if self._is_destroyed:
                return
            
            local_path = self.image_data.get('local_path')
            if not local_path:
                self.set_placeholder_image("경로 없음")
                return
            
            # 파일 존재 확인
            if not os.path.exists(local_path):
                self.set_placeholder_image("파일 없음")
                return
            
            # QPixmap으로 직접 로드
            pixmap = QPixmap(local_path)
            
            if pixmap.isNull():
                self.set_placeholder_image("로드 실패")
            else:
                self.set_image(pixmap)
                
        except Exception as e:
            logger.error(f"로컬 segment 이미지 로드 오류: {str(e)}")
            self.set_placeholder_image("오류 발생")
    
    def safe_on_image_loaded(self, url: str, pixmap: Optional[QPixmap]):
        """안전한 이미지 로드 완료 콜백 - 위젯 상태 확인"""
        # 위젯이 파괴되었거나 Qt 객체가 삭제된 경우 무시
        if self._is_destroyed:
            return
            
        try:
            # 부모 위젯이 여전히 유효한지 먼저 확인 (빠른 체크)
            if not self.parent():
                return
                
            # Qt 객체가 여전히 유효한지 확인
            if not self.image_label or not hasattr(self, 'image_label'):
                return
            
            # URL이 일치하지 않으면 무시
            widget_url = self.image_data.get('url', '')
            if url != widget_url:
                return
                
            # 이미지 설정
            if pixmap:
                self.set_image(pixmap)
            else:
                logger.error(f"이미지 로드 실패 - pixmap이 None: {self.image_data.get('filename', 'unknown')}")
                self.set_placeholder_image("로드 실패")
                
        except RuntimeError as e:
            # Qt 객체가 이미 삭제된 경우
            logger.warning(f"이미지 위젯이 이미 삭제됨: {str(e)}")
            self._is_destroyed = True
        except Exception as e:
            logger.error(f"이미지 로드 콜백 오류: {str(e)}")
            self.set_placeholder_image("콜백 오류")
    
    def on_image_loaded(self, url: str, pixmap: Optional[QPixmap]):
        """이미지 로드 완료 콜백 (deprecated - safe_on_image_loaded 사용)"""
        self.safe_on_image_loaded(url, pixmap)
    
    def set_placeholder_image(self, text: str):
        """플레이스홀더 이미지 생성 및 설정"""
        if self._is_destroyed:
            return
            
        try:
            # 기존 image_viewer.py의 플레이스홀더 로직 참조
            placeholder = QPixmap(140, 140)
            placeholder.fill(QColor(245, 245, 245))  # 연한 회색 배경
            
            # 텍스트 그리기
            painter = QPainter(placeholder)
            painter.setPen(QPen(QColor(150, 150, 150)))
            
            # 폰트 설정
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            
            # 텍스트를 중앙에 그리기
            painter.drawText(placeholder.rect(), Qt.AlignCenter | Qt.TextWordWrap, text)
            painter.end()
            
            if self.image_label and not self._is_destroyed:
                self.image_label.setPixmap(placeholder)
                
        except RuntimeError as e:
            logger.warning(f"플레이스홀더 설정 중 Qt 객체 삭제됨: {str(e)}")
            self._is_destroyed = True
        except Exception as e:
            logger.error(f"플레이스홀더 설정 오류: {str(e)}")
    
    def set_image(self, pixmap: QPixmap):
        """이미지 설정 - 기존 image_viewer.py의 로직 참조"""
        if self._is_destroyed:
            return
            
        try:
            if pixmap.isNull():
                self.set_placeholder_image("잘못된 이미지")
                return
            
            # 목표 크기 (여백 고려)
            target_size = QSize(140, 140)  # 150x150 라벨에서 여백 10px 고려
            original_size = pixmap.size()
            
            # 원본 이미지가 너무 작은 경우 원본 크기 유지
            if original_size.width() <= target_size.width() and original_size.height() <= target_size.height():
                if self.image_label and not self._is_destroyed:
                    self.image_label.setPixmap(pixmap)
                return
            
            # 비율을 유지하면서 목표 크기에 맞게 스케일링
            scale_x = target_size.width() / original_size.width()
            scale_y = target_size.height() / original_size.height()
            scale_factor = min(scale_x, scale_y)
            
            # 최종 크기 계산
            new_width = int(original_size.width() * scale_factor)
            new_height = int(original_size.height() * scale_factor)
            
            # 고품질 스케일링 적용
            scaled_pixmap = pixmap.scaled(
                new_width, new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            if self.image_label and not self._is_destroyed:
                self.image_label.setPixmap(scaled_pixmap)
                
        except RuntimeError as e:
            logger.warning(f"이미지 설정 중 Qt 객체 삭제됨: {str(e)}")
            self._is_destroyed = True
        except Exception as e:
            logger.error(f"이미지 설정 오류: {str(e)}")
    
    def on_remove_clicked(self):
        """제거 버튼 클릭 처리"""
        if self._is_destroyed:
            return
            
        try:
            self.remove_requested.emit(self.image_key)
        except RuntimeError:
            # 위젯이 파괴된 상태에서 시그널 발생 시도 시 무시
            self._is_destroyed = True
        except Exception as e:
            logger.error(f"제거 버튼 클릭 처리 오류: {str(e)}") 