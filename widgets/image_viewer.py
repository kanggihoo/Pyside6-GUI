import os
import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QPushButton, QSlider, QSpinBox, QGroupBox, QDialogButtonBox,
    QSizePolicy, QFrame, QToolButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QTransform, QPainter, QWheelEvent, QMouseEvent, 
    QKeyEvent, QIcon, QFont, QFontMetrics
)


class DraggableImageLabel(QLabel):
    """드래그 가능한 이미지 라벨"""
    
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
        self.rotation_angle = 0
        self.original_pixmap = None
        self.transformed_pixmap = None
        
        self.setMinimumSize(400, 300)

    def set_pixmap(self, pixmap):
        """픽스맵 설정 및 초기화"""
        self.original_pixmap = pixmap.copy()
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.image_offset = QPointF(0, 0)
        self.update_display()

    def update_display(self):
        """현재 변환 상태에 따라 이미지를 업데이트"""
        if not self.original_pixmap:
            return
            
        # 변환 적용
        transform = QTransform()
        transform.scale(self.scale_factor, self.scale_factor)
        transform.rotate(self.rotation_angle)
        
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

    def rotate_left(self):
        """좌측으로 90도 회전"""
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.update_display()

    def rotate_right(self):
        """우측으로 90도 회전"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
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
        self.rotation_angle = 0
        self.image_offset = QPointF(0, 0)
        self.update_display()

    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠로 확대/축소"""
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
            self.dragging = True
            self.last_pan_point = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 드래그"""
        if self.dragging and hasattr(self, 'scroll_area') and self.scroll_area:
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
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)


class ImageViewerDialog(QDialog):
    """고급 이미지 뷰어 다이얼로그"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle(f"이미지 뷰어 - {os.path.basename(image_path)}")
        self.setMinimumSize(800, 600)
        
        # 화면 크기의 85%로 창 크기 설정
        if parent:
            parent_geometry = parent.geometry()
            width = int(parent_geometry.width() * 0.85)
            height = int(parent_geometry.height() * 0.85)
            self.resize(width, height)
        else:
            self.resize(1000, 700)
        
        # 원본 픽스맵 로드
        self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull():
            self.original_pixmap = None
        
        self._setup_ui()
        self._setup_shortcuts()
        
        # 초기 이미지 설정
        if self.original_pixmap:
            self.image_label.set_pixmap(self.original_pixmap)
            self.fit_to_window()
            self._update_info_display()

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
        
        # 회전 그룹
        rotate_group = QGroupBox("회전")
        rotate_layout = QHBoxLayout(rotate_group)
        
        self.rotate_left_btn = QPushButton("↻")
        self.rotate_left_btn.setToolTip("좌측 90° 회전")
        
        self.rotate_right_btn = QPushButton("↺")
        self.rotate_right_btn.setToolTip("우측 90° 회전")
        
        rotate_layout.addWidget(self.rotate_left_btn)
        rotate_layout.addWidget(self.rotate_right_btn)
        
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
        
        toolbar_layout.addWidget(zoom_group)
        toolbar_layout.addWidget(rotate_group)
        toolbar_layout.addWidget(view_group)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # 단축키 정보 표시
        shortcuts_info = QLabel()
        shortcuts_info.setText(
            "📋 단축키: "
            "Ctrl + 휠(확대/축소) | "
            "Ctrl + +/-(확대/축소) | "
            "F(창에맞춤) | "
            "O(원본크기) | "
            "←/→(회전) | "
            "마우스드래그(이동) | "
            "ESC(닫기)"
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
        self.scroll_area.setWidget(self.image_label)
        
        # 스크롤 영역에 휠 이벤트 필터 설치
        self.scroll_area.wheelEvent = self._scroll_area_wheel_event
        
        # 이미지 라벨이 생성된 후 회전 버튼 이벤트 연결
        self.rotate_left_btn.clicked.connect(self.image_label.rotate_left)
        self.rotate_right_btn.clicked.connect(self.image_label.rotate_right)
        
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

    def _setup_shortcuts(self):
        """키보드 단축키 설정"""
        # 확대/축소 연결
        self.zoom_in_btn.clicked.connect(self._update_zoom_controls)
        self.zoom_out_btn.clicked.connect(self._update_zoom_controls)

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
        file_info = f"파일: {self.image_path}"
        if os.path.exists(self.image_path):
            file_size = os.path.getsize(self.image_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            file_info += f" | 크기: {size_str}"
        
        self.file_info_label.setText(file_info)
        
        # 이미지 정보
        if self.original_pixmap:
            width = self.original_pixmap.width()
            height = self.original_pixmap.height()
            zoom = int(self.image_label.scale_factor * 100)
            rotation = self.image_label.rotation_angle
            
            image_info = f"해상도: {width} × {height} | 확대: {zoom}% | 회전: {rotation}°"
            self.image_info_label.setText(image_info)

    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트 처리"""
        key = event.key()
        modifiers = event.modifiers()
        
        if modifiers & Qt.ControlModifier:
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
        elif key == Qt.Key_Left:
            self.image_label.rotate_left()
            self._update_info_display()
            event.accept()
        elif key == Qt.Key_Right:
            self.image_label.rotate_right()
            self._update_info_display()
            event.accept()
        elif key == Qt.Key_Escape:
            self.reject()
            event.accept()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """창 크기 변경 이벤트"""
        super().resizeEvent(event)
        # 창 크기 변경 시 정보 업데이트
        QTimer.singleShot(100, self._update_info_display) 