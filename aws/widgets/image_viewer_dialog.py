#!/usr/bin/env python3
"""
이미지 뷰어 다이얼로그 모듈
URL 기반 고급 이미지 뷰어 기능을 제공합니다.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QDialog, QDialogButtonBox,
                               QSlider, QSpinBox, QGroupBox, QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QPointF, QRectF, QRect
from PySide6.QtGui import (QPixmap, QFont, QColor, QPainter, QPen, QIcon, QTransform, 
                          QWheelEvent, QMouseEvent, QKeyEvent, QCursor, QPaintEvent)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from typing import Dict, Any, Optional
import logging
import os
from pathlib import Path
from PIL import Image
import uuid
import hashlib

logger = logging.getLogger(__name__)


class DraggableImageLabel(QLabel):
    """드래그 가능한 이미지 라벨 - URL 이미지 지원"""
    
    # 영역 선택 완료 시그널
    region_selected = Signal(QRectF)  # 원본 이미지 좌표계에서의 선택 영역
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #ddd;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 드래그 관련 변수
        self.dragging = False
        self.last_pan_point = QPointF()
        self.image_offset = QPointF(0, 0)
        
        # 이미지 변환 관련
        self.scale_factor = 1.0
        self.original_pixmap = None
        self.transformed_pixmap = None
        
        # 네트워크 관련
        self.network_manager = QNetworkAccessManager()
        self.current_reply = None
        
        # 영역 선택 관련
        self.selection_mode = False
        self.selecting = False
        self.selection_start = QPointF()
        self.selection_end = QPointF()
        self.selection_rect = QRectF()
        
        self.setMinimumSize(400, 300)

    def set_selection_mode(self, enabled: bool):
        """영역 선택 모드 설정"""
        self.selection_mode = enabled
        if enabled:
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.selecting = False
            self.selection_rect = QRectF()
            self.update()

    def set_pixmap_from_url(self, url: str, image_cache=None):
        """URL에서 픽스맵 로드"""
        if image_cache:
            # 캐시에서 이미지 가져오기
            cached_pixmap = image_cache.get_image(url, self._on_image_loaded_from_cache)
            if cached_pixmap:
                self.set_pixmap(cached_pixmap)
                return
        
        # 캐시에 없으면 직접 다운로드
        self._download_image(url)
    
    def _on_image_loaded_from_cache(self, url: str, pixmap: Optional[QPixmap]):
        """캐시에서 이미지 로드 완료"""
        if pixmap:
            self.set_pixmap(pixmap)
        else:
            self._download_image(url)
    
    def _download_image(self, url: str):
        """이미지 직접 다운로드"""
        self.setText("이미지 로딩 중...")
        
        request = QNetworkRequest(url)
        self.current_reply = self.network_manager.get(request)
        self.current_reply.finished.connect(self._on_download_finished)
    
    def _on_download_finished(self):
        """다운로드 완료 처리"""
        if self.current_reply.error() == QNetworkReply.NoError:
            image_data = self.current_reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.set_pixmap(pixmap)
            else:
                self.setText("이미지 로드 실패")
        else:
            self.setText("이미지 다운로드 실패")
        
        self.current_reply.deleteLater()
        self.current_reply = None

    def set_pixmap(self, pixmap):
        """픽스맵 설정 및 초기화"""
        self.original_pixmap = pixmap.copy()
        self.scale_factor = 1.0
        self.image_offset = QPointF(0, 0)
        self.update_display()

    def update_display(self):
        """현재 변환 상태에 따라 이미지를 업데이트"""
        if not self.original_pixmap:
            return
            
        # 변환 적용
        transform = QTransform()
        transform.scale(self.scale_factor, self.scale_factor)
        
        self.transformed_pixmap = self.original_pixmap.transformed(
            transform, Qt.SmoothTransformation
        )
        
        self.setPixmap(self.transformed_pixmap)
        
        # 이미지 크기가 변경되었으므로 위젯 크기 업데이트
        self.setFixedSize(self.transformed_pixmap.size())
        self.updateGeometry()

    def zoom_in(self, factor=1.2):
        """확대"""
        self.scale_factor *= factor
        self.update_display()

    def zoom_out(self, factor=1.2):
        """축소"""
        self.scale_factor /= factor
        self.update_display()

    def set_zoom(self, zoom_percent):
        """특정 확대 비율로 설정"""
        self.scale_factor = zoom_percent / 100.0
        self.update_display()

    def fit_to_window(self):
        """창 크기에 맞춤"""
        if not self.original_pixmap:
            return
            
        # 스크롤 영역의 viewport 크기 사용
        if hasattr(self, 'scroll_area') and self.scroll_area:
            viewport_size = self.scroll_area.viewport().size()
        else:
            viewport_size = self.size()
            
        pixmap_size = self.original_pixmap.size()
        
        scale_x = viewport_size.width() / pixmap_size.width()
        scale_y = viewport_size.height() / pixmap_size.height()
        
        self.scale_factor = min(scale_x, scale_y) * 0.9  # 여백 고려
        self.update_display()

    def reset_to_original(self):
        """원본 크기로 리셋"""
        self.scale_factor = 1.0
        self.image_offset = QPointF(0, 0)
        self.update_display()

    def _widget_to_original_coords(self, widget_point: QPointF) -> QPointF:
        """위젯 좌표를 원본 이미지 좌표로 변환"""
        if not self.original_pixmap or not self.transformed_pixmap:
            return widget_point
            
        # 위젯에서 표시된 이미지의 실제 위치 계산
        label_rect = self.rect()
        pixmap_rect = self.transformed_pixmap.rect()
        
        # 이미지가 라벨 중앙에 표시되므로 오프셋 계산
        x_offset = (label_rect.width() - pixmap_rect.width()) // 2
        y_offset = (label_rect.height() - pixmap_rect.height()) // 2
        
        # 위젯 좌표에서 이미지 내 좌표로 변환
        image_x = widget_point.x() - x_offset
        image_y = widget_point.y() - y_offset
        
        # 스케일 팩터를 고려해 원본 좌표로 변환
        original_x = image_x / self.scale_factor
        original_y = image_y / self.scale_factor
        
        return QPointF(original_x, original_y)

    def get_selected_region_pixmap(self) -> Optional[QPixmap]:
        """선택된 영역의 픽스맵 반환"""
        if not self.original_pixmap or self.selection_rect.isEmpty():
            return None
            
        # 원본 이미지 좌표계에서의 선택 영역
        start_original = self._widget_to_original_coords(self.selection_start)
        end_original = self._widget_to_original_coords(self.selection_end)
        
        # 선택 영역 정규화 (좌상단, 우하단 좌표 정리)
        left = min(start_original.x(), end_original.x())
        top = min(start_original.y(), end_original.y())
        right = max(start_original.x(), end_original.x())
        bottom = max(start_original.y(), end_original.y())
        
        # 원본 이미지 경계 내로 제한
        left = max(0, int(left))
        top = max(0, int(top))
        right = min(self.original_pixmap.width(), int(right))
        bottom = min(self.original_pixmap.height(), int(bottom))
        
        # 유효한 영역인지 확인
        if right <= left or bottom <= top:
            return None
            
        # 선택된 영역 추출
        selection_rect = QRect(left, top, right - left, bottom - top)
        return self.original_pixmap.copy(selection_rect)

    def paintEvent(self, event: QPaintEvent):
        """페인트 이벤트 - 선택 영역 그리기"""
        super().paintEvent(event)
        
        if self.selection_mode and not self.selection_rect.isEmpty():
            painter = QPainter(self)
            
            # 선택 영역 테두리
            pen = QPen(QColor(0, 120, 215), 2, Qt.SolidLine)
            painter.setPen(pen)
            
            # 선택 영역 배경 (반투명)
            brush_color = QColor(0, 120, 215, 50)
            painter.setBrush(brush_color)
            
            painter.drawRect(self.selection_rect)
            painter.end()

    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠로 확대/축소"""
        if self.selection_mode:
            # 선택 모드에서는 휠 이벤트 무시
            return
            
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            # Ctrl + 휠: 확대/축소
            angle_delta = event.angleDelta().y()
            if angle_delta > 0:
                self.zoom_in(1.15)
                if hasattr(self, 'viewer_dialog'):
                    self.viewer_dialog._update_zoom_controls()
            else:
                self.zoom_out(1.15)
                if hasattr(self, 'viewer_dialog'):
                    self.viewer_dialog._update_zoom_controls()
            event.accept()
        else:
            # 일반 휠은 부모에게 전달 (스크롤)
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """마우스 클릭 시작"""
        if event.button() == Qt.LeftButton:
            if self.selection_mode:
                # 영역 선택 모드
                self.selecting = True
                self.selection_start = event.position()
                self.selection_end = event.position()
                self.selection_rect = QRectF(self.selection_start, self.selection_end)
                self.update()
            else:
                # 일반 드래그 모드
                self.dragging = True
                self.last_pan_point = event.position()
                self.setCursor(QCursor(Qt.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 드래그"""
        if self.selection_mode and self.selecting:
            # 영역 선택 업데이트
            self.selection_end = event.position()
            self.selection_rect = QRectF(self.selection_start, self.selection_end).normalized()
            self.update()
        elif self.dragging and hasattr(self, 'scroll_area') and self.scroll_area:
            # 일반 드래그 (이미지 이동)
            delta = event.position() - self.last_pan_point
            self.last_pan_point = event.position()
            
            # 스크롤 영역의 스크롤바를 직접 제어
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            
            # 델타 반대 방향으로 스크롤 (자연스러운 드래그 느낌)
            h_scroll.setValue(h_scroll.value() - int(delta.x()))
            v_scroll.setValue(v_scroll.value() - int(delta.y()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """마우스 클릭 해제"""
        if event.button() == Qt.LeftButton:
            if self.selection_mode and self.selecting:
                # 영역 선택 완료
                self.selecting = False
                if not self.selection_rect.isEmpty():
                    # 최소 크기 확인 (10x10 픽셀 이상)
                    if (self.selection_rect.width() > 10 and 
                        self.selection_rect.height() > 10):
                        # 선택 완료 시그널 발생
                        start_original = self._widget_to_original_coords(self.selection_start)
                        end_original = self._widget_to_original_coords(self.selection_end)
                        original_rect = QRectF(start_original, end_original).normalized()
                        self.region_selected.emit(original_rect)
                    else:
                        # 너무 작은 영역은 무시
                        self.selection_rect = QRectF()
                        self.update()
            else:
                # 일반 드래그 해제
                self.dragging = False
                if not self.selection_mode:
                    self.setCursor(QCursor(Qt.ArrowCursor))
        super().mouseReleaseEvent(event)


class UrlImageViewerDialog(QDialog):
    """URL 기반 고급 이미지 뷰어 다이얼로그"""
    
    # 새로운 segment 이미지 생성 시그널
    segment_image_created = Signal(dict)  # 새로 생성된 이미지 정보
    
    def __init__(self, image_data: Dict[str, Any], image_cache=None, current_product=None, aws_manager=None, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.image_cache = image_cache
        self.current_product = current_product
        self.aws_manager = aws_manager
        
        # 이미지 정보 추출
        self.image_url = image_data.get('url', '')
        self.filename = image_data.get('filename', self.image_url.split('/')[-1] if self.image_url else 'Unknown')
        
        self.setWindowTitle(f"이미지 뷰어 - {self.filename}")
        self.setMinimumSize(800, 600)
        
        # 화면 크기의 85%로 창 크기 설정
        if parent:
            parent_geometry = parent.geometry()
            width = int(parent_geometry.width() * 0.85)
            height = int(parent_geometry.height() * 0.85)
            self.resize(width, height)
        else:
            self.resize(1000, 700)
        
        self._setup_ui()
        self._setup_shortcuts()
        
        # 이미지 로드
        if self.image_url:
            self.image_label.set_pixmap_from_url(self.image_url, self.image_cache)
            # 로드 완료 후 창에 맞춤
            QTimer.singleShot(500, self.fit_to_window)

    def _get_cache_segments_dir(self) -> Path:
        """Segment 이미지들을 저장할 캐시 디렉토리 경로 반환"""
        if self.image_cache and hasattr(self.image_cache, 'cache_dir'):
            base_dir = Path(self.image_cache.cache_dir)
        else:
            base_dir = Path.home() / '.cache' / 'ai_dataset_curation' / 'images'
        
        segments_dir = base_dir / 'segments'
        segments_dir.mkdir(parents=True, exist_ok=True)
        return segments_dir

    def _save_as_thumbnail(self, pixmap: QPixmap, save_path: Path) -> bool:
        """픽스맵을 512px 썸네일로 저장"""
        try:
            # QPixmap을 임시 바이트 배열로 변환
            from PySide6.QtCore import QBuffer, QIODevice
            
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, 'PNG')
            
            # PIL Image로 변환
            from io import BytesIO
            buffer_bytes = BytesIO(buffer.data().data())
            pil_image = Image.open(buffer_bytes)
            
            # RGBA 모드로 변환 (투명도 지원)
            if pil_image.mode != 'RGB':
                # 투명도가 있는 경우 흰색 배경과 합성
                if pil_image.mode == 'RGBA':
                    background = Image.new('RGB', pil_image.size, (255, 255, 255))
                    background.paste(pil_image, mask=pil_image.split()[-1])
                    pil_image = background
                else:
                    pil_image = pil_image.convert('RGB')
            
            # 썸네일 생성 (가장 긴 변을 512로 고정, 비율 유지)
            pil_image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            # JPEG로 저장 (고품질)
            pil_image.save(save_path, 'JPEG', quality=95, optimize=True)
            
            buffer.close()
            logger.info(f"썸네일 저장 완료: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"썸네일 저장 실패: {str(e)}")
            return False

    def _generate_segment_filename(self) -> str:
        """Segment 이미지 파일명 생성 - 효율적이고 짧은 이름"""
        try:
            # 제품 ID 기반 접두사 생성
            product_id = ""
            if self.current_product:
                product_id = self.current_product.get('product_id', '')
                # 제품 ID가 너무 길면 축약
                if len(product_id) > 8:
                    product_id = product_id[:8]
            
            if not product_id:
                # 제품 ID가 없으면 원본 파일명에서 짧은 접두사 생성
                base_name = os.path.splitext(self.filename)[0]
                # 파일명이 길면 처음 6자만 사용
                product_id = base_name[:6] if len(base_name) > 6 else base_name
                # 특수문자 제거
                product_id = ''.join(c for c in product_id if c.isalnum())
            
            # 기존 segment 파일들 스캔하여 다음 번호 찾기
            segments_dir = self._get_cache_segments_dir()
            next_number = self._get_next_segment_number(segments_dir, product_id)
            
            # 짧고 깔끔한 파일명 생성: PROD_seg_001.jpg
            return f"{product_id}_seg_{next_number:03d}.jpg"
            
        except Exception as e:
            logger.error(f"파일명 생성 오류: {str(e)}")
            # 폴백: 간단한 타임스탬프 기반
            import time
            timestamp = int(time.time()) % 100000  # 마지막 5자리만 사용
            return f"seg_{timestamp}.jpg"

    def _get_next_segment_number(self, segments_dir: Path, product_prefix: str) -> int:
        """해당 제품의 다음 segment 번호 찾기"""
        try:
            if not segments_dir.exists():
                return 1
            
            # 해당 제품의 기존 segment 파일들 찾기
            pattern = f"{product_prefix}_seg_*.jpg"
            existing_files = list(segments_dir.glob(pattern))
            
            if not existing_files:
                return 1
            
            # 기존 번호들 추출
            numbers = []
            for file_path in existing_files:
                try:
                    # 파일명에서 번호 추출: PROD_seg_001.jpg -> 001
                    name_parts = file_path.stem.split('_')
                    if len(name_parts) >= 3 and name_parts[-2] == 'seg':
                        number_str = name_parts[-1]
                        if number_str.isdigit():
                            numbers.append(int(number_str))
                except Exception:
                    continue
            
            # 다음 번호 반환
            if numbers:
                return max(numbers) + 1
            else:
                return 1
                
        except Exception as e:
            logger.error(f"다음 번호 찾기 오류: {str(e)}")
            return 1

    def _create_segment_image_data(self, file_path: Path) -> Dict[str, Any]:
        """새로운 segment 이미지 데이터 생성"""
        # 파일 크기 확인
        file_size = file_path.stat().st_size
        
        # 이미지 크기 확인
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = 512, 512  # 기본값
        
        # 가상의 URL 생성 (로컬 파일이므로 file:// 프로토콜 사용)
        file_url = f"file://{file_path.absolute()}"
        
        # 생성 시간 정보
        import time
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 원본 이미지 정보
        original_info = {
            'original_filename': self.filename,
            'original_url': self.image_url,
            'created_time': created_time
        }
        
        return {
            'key': f"segments/{file_path.name}",
            'url': file_url,
            'folder': 'segment',
            'filename': file_path.name,
            'local_path': str(file_path),
            'is_local_segment': True,
            'created_from': self.filename,
            'original_url': self.image_url,
            'file_size': file_size,
            'dimensions': f"{width}x{height}",
            'product_id': self.current_product.get('product_id') if self.current_product else None,
            'segment_info': original_info,  # 추가 메타데이터
            'display_name': self._generate_display_name(file_path.name)  # 표시용 이름
        }

    def _generate_display_name(self, filename: str) -> str:
        """사용자에게 표시할 친숙한 이름 생성"""
        try:
            # seg_001.jpg -> "Segment #1"
            # PROD123_seg_002.jpg -> "PROD123 Segment #2"
            name_without_ext = os.path.splitext(filename)[0]
            parts = name_without_ext.split('_')
            
            if len(parts) >= 3 and parts[-2] == 'seg':
                product_part = '_'.join(parts[:-2]) if len(parts) > 3 else ""
                number_part = parts[-1]
                
                if number_part.isdigit():
                    number = int(number_part)
                    if product_part:
                        return f"{product_part} Segment #{number}"
                    else:
                        return f"Segment #{number}"
            
            # 폴백: 원본 파일명 사용
            return filename
            
        except Exception:
            return filename

    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 상단: 도구 모음
        toolbar_layout = QHBoxLayout()
        
        # 확대/축소 그룹
        zoom_group = QGroupBox("확대/축소")
        zoom_layout = QHBoxLayout(zoom_group)
        
        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.setToolTip("축소 (Ctrl + -)")
        self.zoom_out_btn.clicked.connect(self._on_zoom_out_clicked)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)  # 10% ~ 500%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setToolTip("확대 비율")
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setRange(10, 500)
        self.zoom_spinbox.setValue(100)
        self.zoom_spinbox.setSuffix("%")
        self.zoom_spinbox.setToolTip("확대 비율")
        self.zoom_spinbox.valueChanged.connect(self._on_zoom_spinbox_changed)
        
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setToolTip("확대 (Ctrl + +)")
        self.zoom_in_btn.clicked.connect(self._on_zoom_in_clicked)
        
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_spinbox)
        zoom_layout.addWidget(self.zoom_in_btn)
        
        # 보기 그룹
        view_group = QGroupBox("보기")
        view_layout = QHBoxLayout(view_group)
        
        self.fit_window_btn = QPushButton("창에 맞춤")
        self.fit_window_btn.setToolTip("창 크기에 맞춤 (F)")
        self.fit_window_btn.clicked.connect(self.fit_to_window)
        
        self.original_size_btn = QPushButton("원본 크기")
        self.original_size_btn.setToolTip("100% 크기로 보기 (O)")
        self.original_size_btn.clicked.connect(self.reset_to_original)
        
        view_layout.addWidget(self.fit_window_btn)
        view_layout.addWidget(self.original_size_btn)
        
        # 편집 그룹
        edit_group = QGroupBox("Segment 생성")
        edit_layout = QHBoxLayout(edit_group)
        
        self.select_region_btn = QPushButton("✂️ 영역 선택")
        self.select_region_btn.setToolTip("드래그로 영역을 선택하여 Segment 이미지 생성 (S)")
        self.select_region_btn.setCheckable(True)
        self.select_region_btn.clicked.connect(self._on_select_region_clicked)
        
        edit_layout.addWidget(self.select_region_btn)
        
        toolbar_layout.addWidget(zoom_group)
        toolbar_layout.addWidget(view_group)
        toolbar_layout.addWidget(edit_group)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # 단축키 정보 표시
        shortcuts_info = QLabel()
        shortcuts_info.setText(
            "📋 단축키: "
            "Ctrl + 휠(확대/축소)   |   "
            "마우스드래그(이동)   |   "
            "S(영역선택)   |   "
            "ESC(선택취소/닫기)"
        )
        shortcuts_info.setStyleSheet("""
            QLabel {
                background-color: #3498db;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #2980b9;
            }
        """)
        shortcuts_info.setWordWrap(True)
        shortcuts_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(shortcuts_info)
        
        # 중앙: 이미지 표시 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # 이미지 크기에 맞게 스크롤바 표시
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: 2px solid #ccc; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.image_label = DraggableImageLabel()
        # 부모 참조를 위해 scroll_area와 viewer_dialog를 설정
        self.image_label.scroll_area = self.scroll_area
        self.image_label.viewer_dialog = self
        
        # 영역 선택 완료 시그널 연결
        self.image_label.region_selected.connect(self._on_region_selected)
        
        self.scroll_area.setWidget(self.image_label)
        
        # 스크롤 영역에 휠 이벤트 필터 설치
        self.scroll_area.wheelEvent = self._scroll_area_wheel_event
        
        layout.addWidget(self.scroll_area)
        
        # 하단: 정보 표시
        info_layout = QHBoxLayout()
        
        # 파일 정보
        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                padding: 8px; 
                background-color: #2c3e50; 
                color: #ffffff;
                border-radius: 4px;
                border: 1px solid #34495e;
            }
        """)
        self.file_info_label.setWordWrap(True)
        
        # 이미지 정보
        self.image_info_label = QLabel()
        self.image_info_label.setStyleSheet("""
            QLabel {
                padding: 8px; 
                background-color: #34495e; 
                color: #ecf0f1;
                border-radius: 4px;
                border: 1px solid #2c3e50;
            }
        """)
        
        info_layout.addWidget(self.file_info_label, 2)
        info_layout.addWidget(self.image_info_label, 1)
        
        layout.addLayout(info_layout)
        
        # 닫기 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 초기 정보 표시
        self._update_info_display()

    def _setup_shortcuts(self):
        """키보드 단축키 설정"""
        # 확대/축소 연결
        self.zoom_in_btn.clicked.connect(self._update_zoom_controls)
        self.zoom_out_btn.clicked.connect(self._update_zoom_controls)

    def _on_select_region_clicked(self, checked: bool):
        """영역 선택 버튼 클릭"""
        self.image_label.set_selection_mode(checked)
        
        if checked:
            self.select_region_btn.setText("❌ 선택 취소")
            self.select_region_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
        else:
            self.select_region_btn.setText("✂️ 영역 선택")
            self.select_region_btn.setStyleSheet("")

    def _on_region_selected(self, region_rect: QRectF):
        """영역 선택 완료 - Segment 이미지 생성"""
        # 선택된 영역의 픽스맵 가져오기
        selected_pixmap = self.image_label.get_selected_region_pixmap()
        
        if selected_pixmap:
            try:
                # 캐시 segments 디렉토리 확인
                segments_dir = self._get_cache_segments_dir()
                
                # 효율적인 파일명 생성
                filename = self._generate_segment_filename()
                file_path = segments_dir / filename
                
                # 파일명 중복 체크 (추가 안전장치)
                counter = 1
                original_filename = filename
                while file_path.exists():
                    # 만약 파일이 이미 존재하면 번호 증가
                    name_parts = os.path.splitext(original_filename)
                    filename = f"{name_parts[0]}_{counter:02d}{name_parts[1]}"
                    file_path = segments_dir / filename
                    counter += 1
                    
                    # 무한 루프 방지
                    if counter > 999:
                        break
                
                # 썸네일로 저장
                if self._save_as_thumbnail(selected_pixmap, file_path):
                    # 새로운 이미지 데이터 생성
                    new_image_data = self._create_segment_image_data(file_path)
                    
                    # 성공 메시지 - 더 친숙한 정보 표시
                    display_name = new_image_data.get('display_name', filename)
                    QMessageBox.information(
                        self,
                        "✂️ Segment 생성 완료",
                        f"새로운 Segment 이미지가 생성되었습니다!\n\n"
                        f"🏷️ 이름: {display_name}\n"
                        f"📐 크기: {new_image_data['dimensions']}\n"
                        f"📁 파일: {filename}\n"
                        f"📍 경로: segments 폴더\n\n"
                        f"💡 이제 Segment 폴더에서 대표 이미지로 선택할 수 있습니다."
                    )
                    
                    # 메인 뷰어에 새 이미지 추가 시그널 발생
                    self.segment_image_created.emit(new_image_data)
                    
                    logger.info(f"Segment 이미지 생성 완료: {filename} (display: {display_name})")
                    
                else:
                    QMessageBox.warning(self, "저장 실패", "Segment 이미지 저장에 실패했습니다.")
                    
            except Exception as e:
                logger.error(f"Segment 이미지 생성 오류: {str(e)}")
                QMessageBox.critical(self, "오류", f"Segment 이미지 생성 중 오류가 발생했습니다:\n{str(e)}")
        
        # 선택 모드 해제
        self.select_region_btn.setChecked(False)
        self._on_select_region_clicked(False)

    def _on_zoom_slider_changed(self, value):
        """줌 슬라이더 변경"""
        self.zoom_spinbox.blockSignals(True)
        self.zoom_spinbox.setValue(value)
        self.zoom_spinbox.blockSignals(False)
        self.image_label.set_zoom(value)
        self._update_info_display()

    def _on_zoom_spinbox_changed(self, value):
        """줌 스핀박스 변경"""
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(value)
        self.zoom_slider.blockSignals(False)
        self.image_label.set_zoom(value)
        self._update_info_display()

    def _scroll_area_wheel_event(self, event: QWheelEvent):
        """스크롤 영역의 휠 이벤트를 이미지 라벨로 전달"""
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            # Ctrl + 휠: 확대/축소를 이미지 라벨에서 처리
            angle_delta = event.angleDelta().y()
            if angle_delta > 0:
                self.image_label.zoom_in(1.15)
            else:
                self.image_label.zoom_out(1.15)
            self._update_zoom_controls()
            event.accept()
        else:
            # 일반 휠: 기본 스크롤 동작
            QScrollArea.wheelEvent(self.scroll_area, event)

    def _on_zoom_in_clicked(self):
        """확대 버튼 클릭"""
        self.image_label.zoom_in()
        self._update_zoom_controls()

    def _on_zoom_out_clicked(self):
        """축소 버튼 클릭"""
        self.image_label.zoom_out()
        self._update_zoom_controls()

    def _update_zoom_controls(self):
        """줌 컨트롤 UI 업데이트"""
        current_zoom = int(self.image_label.scale_factor * 100)
        
        self.zoom_slider.blockSignals(True)
        self.zoom_spinbox.blockSignals(True)
        
        self.zoom_slider.setValue(current_zoom)
        self.zoom_spinbox.setValue(current_zoom)
        
        self.zoom_slider.blockSignals(False)
        self.zoom_spinbox.blockSignals(False)
        
        self._update_info_display()

    def fit_to_window(self):
        """창에 맞춤"""
        self.image_label.fit_to_window()
        self._update_zoom_controls()

    def reset_to_original(self):
        """원본 크기로 리셋"""
        self.image_label.reset_to_original()
        self._update_zoom_controls()

    def _update_info_display(self):
        """정보 표시 업데이트"""
        # 파일 정보
        file_info = f"파일: {self.filename}"
        folder = self.image_data.get('folder', 'Unknown')
        file_info += f" | 폴더: {folder}"
        
        # 로컬 캐시 경로 표시
        if self.image_cache and hasattr(self.image_cache, '_get_cache_path'):
            try:
                cache_path = self.image_cache._get_cache_path(self.image_url)
                if cache_path.exists():
                    file_info += f" | 캐시: {cache_path}"
            except Exception:
                pass
        
        self.file_info_label.setText(file_info)
        
        # 이미지 정보
        if self.image_label.original_pixmap:
            width = self.image_label.original_pixmap.width()
            height = self.image_label.original_pixmap.height()
            zoom = int(self.image_label.scale_factor * 100)
            
            image_info = f"해상도: {width} × {height} | 확대: {zoom}%"
            self.image_info_label.setText(image_info)
        else:
            self.image_info_label.setText("이미지 로딩 중...")

    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트 처리"""
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Escape:
            if self.image_label.selection_mode:
                # 선택 모드 해제
                self.select_region_btn.setChecked(False)
                self._on_select_region_clicked(False)
                event.accept()
            else:
                # 다이얼로그 닫기
                self.reject()
                event.accept()
        elif key == Qt.Key_S and not modifiers:
            # S 키로 영역 선택 토글
            current_state = self.select_region_btn.isChecked()
            self.select_region_btn.setChecked(not current_state)
            self._on_select_region_clicked(not current_state)
            event.accept()
        elif modifiers & Qt.ControlModifier:
            if key == Qt.Key_Plus or key == Qt.Key_Equal:
                self.image_label.zoom_in()
                self._update_zoom_controls()
                event.accept()
            elif key == Qt.Key_Minus:
                self.image_label.zoom_out()
                self._update_zoom_controls()
                event.accept()
        elif key == Qt.Key_F:
            self.fit_to_window()
            event.accept()
        elif key == Qt.Key_O:
            self.reset_to_original()
            event.accept()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """창 크기 변경 이벤트"""
        super().resizeEvent(event)
        # 창 크기 변경 시 정보 업데이트
        QTimer.singleShot(100, self._update_info_display) 