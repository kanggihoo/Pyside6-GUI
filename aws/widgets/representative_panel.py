#!/usr/bin/env python3
"""
대표 이미지 패널 위젯
선정된 대표 이미지들을 표시하고 관리합니다.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QGridLayout,
                               QButtonGroup, QCheckBox, QComboBox, QMessageBox,
                               QTextEdit, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPen, QKeyEvent
from typing import Dict, Any, List, Optional
import logging

# CurationWorker import 추가
from .main_image_viewer import CurationWorker

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
        
        self.setup_ui()
        self.load_image()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # 타입 레이블
        type_frame = QFrame()
        if self.is_main_representative:
            type_frame.setStyleSheet("background-color: #28a745; color: white; border-radius: 3px;")  # 대표 이미지는 녹색
        else:
            type_frame.setStyleSheet("background-color: #007bff; color: white; border-radius: 3px;")  # 색상 변형은 파란색
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(5, 2, 5, 2)
        
        # 타입 표시
        if self.is_main_representative:
            display_text = self.get_type_display_name()
        else:
            # 색상 변형 이미지인 경우
            color_num = self.image_key.replace('color_', '')
            display_text = f"색상 {color_num}"
        
        type_label = QLabel(display_text)
        type_label.setStyleSheet("color: white; font-weight: bold; font-size: 10px;")
        type_layout.addWidget(type_label)
        
        # 제거 버튼
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.image_key))
        type_layout.addWidget(remove_btn)
        
        layout.addWidget(type_frame)
        
        # 이미지 표시
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(120, 120)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #28a745;
                border-radius: 5px;
                background-color: white;
            }
        """)
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label)
        
        # 이미지 정보
        filename = self.image_data.get('filename', self.image_data.get('url', '').split('/')[-1])
        filename_label = QLabel(filename)
        filename_label.setAlignment(Qt.AlignCenter)
        filename_label.setWordWrap(True)
        filename_label.setStyleSheet("font-size: 9px; color: #333; background-color: white; padding: 2px; border-radius: 3px;")
        layout.addWidget(filename_label)
    
    def get_type_display_name(self) -> str:
        """타입 표시명 반환"""
        type_names = {
            'model_wearing': '모델 착용',
            'front_cutout': '정면 누끼',
            'back_cutout': '후면 누끼',
            # 기존 타입도 유지 (호환성)
            'main': '메인',
            'color_variant': '색상',
            'detail': '상세',
            'other': '기타'
        }
        return type_names.get(self.image_key, self.image_key)
    
    def load_image(self):
        """이미지 로드"""
        if not self.image_cache:
            self.image_label.setText("캐시 없음")
            return
        
        url = self.image_data.get('url')
        if not url:
            self.image_label.setText("URL 없음")
            return
        
        # 캐시에서 이미지 가져오기
        cached_pixmap = self.image_cache.get_image(url, self.on_image_loaded)
        
        if cached_pixmap:
            self.set_image(cached_pixmap)
        else:
            self.image_label.setText("로딩...")
    
    def on_image_loaded(self, url: str, pixmap: Optional[QPixmap]):
        """이미지 로드 완료 콜백"""
        if pixmap:
            self.set_image(pixmap)
        else:
            self.image_label.setText("로드 실패")
    
    def set_image(self, pixmap: QPixmap):
        """이미지 설정"""
        if pixmap.isNull():
            self.image_label.setText("잘못된 이미지")
            return
        
        # 썸네일 크기로 스케일링
        scaled_pixmap = pixmap.scaled(
            120, 120,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)


class RepresentativePanel(QWidget):
    """대표 이미지 패널 위젯 \n
    - curation_completed : Signal(str) 큐레이션 완료 시 상품 ID 전달
    """
    
    curation_completed = Signal(str)  # 완료된 상품 ID
    
    def __init__(self):
        super().__init__()
        self.aws_manager = None
        self.image_cache = None
        self.main_image_viewer = None  # MainImageViewer 참조 추가
        self.current_product = None
        self.representative_images = {}  # 대표 이미지 3개 (model_wearing, front_cutout, back_cutout)
        self.color_variant_images = {}  # 색상별 정면 누끼 이미지들
        self.curation_worker = None  # S3 업데이트 워커
        
        # 키보드 포커스 설정
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 헤더
        self.setup_header(layout)
        
        # 대표 이미지 영역 (모델, 정면 누끼, 후면 누끼)
        self.setup_main_representative_area(layout)
        
        # 제품 색상 영역 (여러 색상의 정면 누끼)
        self.setup_color_variants_area(layout)
        
        # 하단 컨트롤
        self.setup_bottom_controls(layout)
    
    def setup_header(self, parent_layout):
        """헤더 설정"""
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #f8f9fa; color: #212529; border-bottom: 1px solid #dee2e6; border-radius: 5px;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # 제목
        title_label = QLabel("대표 이미지")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # 상품 정보
        self.product_info_label = QLabel("상품을 선택해주세요")
        self.product_info_label.setStyleSheet("color: #495057; background-color: transparent; font-size: 11px;")
        header_layout.addWidget(self.product_info_label)
        
        parent_layout.addWidget(header_frame)
    
    def setup_main_representative_area(self, parent_layout):
        """대표 이미지 영역 설정 (모델, 정면 누끼, 후면 누끼)"""
        main_frame = QFrame()
        main_frame.setStyleSheet("background-color: #e8f5e8; color: #212529; border: 2px solid #28a745; border-radius: 5px;")
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 제목
        main_title = QLabel("대표 이미지 (대표 색상)")
        main_title.setStyleSheet("font-weight: bold; color: #155724; background-color: transparent; font-size: 14px; padding-bottom: 10px;")
        main_layout.addWidget(main_title)
        
        # 설명
        desc_label = QLabel("동일한 색상의 모델 착용, 정면 누끼, 후면 누끼 이미지를 선정해주세요.")
        desc_label.setStyleSheet("color: #495057; background-color: transparent; font-size: 11px; padding-bottom: 10px;")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # 대표 이미지 그리드
        self.main_rep_grid_widget = QWidget()
        self.main_rep_grid_layout = QHBoxLayout(self.main_rep_grid_widget)
        self.main_rep_grid_layout.setSpacing(10)
        self.main_rep_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        main_layout.addWidget(self.main_rep_grid_widget)
        
        # 상태 표시
        self.main_status_label = QLabel("대표 이미지 3개를 선정해주세요")
        self.main_status_label.setAlignment(Qt.AlignCenter)
        self.main_status_label.setStyleSheet("color: #155724; background-color: #d4edda; font-size: 11px; padding: 6px; border-radius: 3px;")
        main_layout.addWidget(self.main_status_label)
        
        parent_layout.addWidget(main_frame)
    
    def setup_color_variants_area(self, parent_layout):
        """제품 색상 영역 설정 (여러 색상의 정면 누끼)"""
        color_frame = QFrame()
        color_frame.setStyleSheet("background-color: #e3f2fd; color: #212529; border: 2px solid #007bff; border-radius: 5px;")
        color_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        color_layout = QVBoxLayout(color_frame)
        color_layout.setContentsMargins(10, 10, 10, 10)
        
        # 제목
        color_title = QLabel("제품 색상")
        color_title.setStyleSheet("font-weight: bold; color: #0c4a60; background-color: transparent; font-size: 14px; padding-bottom: 10px;")
        color_layout.addWidget(color_title)
        
        # 설명
        desc_label = QLabel("대표 이미지 3개 선정 완료 후, 다른 색상의 정면 누끼 이미지를 최소 1개 이상 추가해야 큐레이션을 완료할 수 있습니다.")
        desc_label.setStyleSheet("color: #495057; background-color: transparent; font-size: 11px; padding-bottom: 10px;")
        desc_label.setWordWrap(True)
        color_layout.addWidget(desc_label)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(150)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 색상별 이미지 그리드
        self.color_grid_widget = QWidget()
        self.color_grid_layout = QHBoxLayout(self.color_grid_widget)
        self.color_grid_layout.setSpacing(10)
        self.color_grid_layout.setContentsMargins(5, 5, 5, 5)
        self.color_grid_layout.addStretch()
        
        scroll_area.setWidget(self.color_grid_widget)
        color_layout.addWidget(scroll_area)
        
        # 상태 표시
        self.color_status_label = QLabel("대표 이미지 3개를 먼저 선정해주세요")
        self.color_status_label.setAlignment(Qt.AlignCenter)
        self.color_status_label.setStyleSheet("color: #0c4a60; background-color: #d1ecf1; font-size: 11px; padding: 6px; border-radius: 3px;")
        color_layout.addWidget(self.color_status_label)
        
        parent_layout.addWidget(color_frame)
    
    def setup_bottom_controls(self, parent_layout):
        """하단 컨트롤 설정"""
        controls_frame = QFrame()
        controls_frame.setStyleSheet("background-color: #f8f9fa; color: #212529; border-top: 1px solid #dee2e6; border-radius: 5px;")
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(15, 10, 15, 10)
        
        # 선택 요약
        self.selection_summary = QLabel("선택된 대표 이미지: 0개")
        self.selection_summary.setStyleSheet("font-weight: bold; color: #212529; background-color: transparent; padding-bottom: 10px;")
        controls_layout.addWidget(self.selection_summary)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        # 초기화 버튼
        clear_btn = QPushButton("초기화")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        clear_btn.clicked.connect(self.clear_representatives)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        # 완료 버튼
        self.complete_btn = QPushButton("큐레이션 완료 (Space)")
        self.complete_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.complete_btn.clicked.connect(self.complete_curation)
        self.complete_btn.setEnabled(False)
        button_layout.addWidget(self.complete_btn)
        
        controls_layout.addLayout(button_layout)
        
        parent_layout.addWidget(controls_frame)
    
    def set_aws_manager(self, aws_manager):
        """AWS 매니저 설정"""
        self.aws_manager = aws_manager
    
    def set_image_cache(self, image_cache):
        """이미지 캐시 설정"""
        self.image_cache = image_cache
    
    def set_main_image_viewer(self, main_image_viewer):
        """메인 이미지 뷰어 참조 설정"""
        self.main_image_viewer = main_image_viewer
    
    def load_product(self, product_data: Dict[str, Any]):
        """
        우측 패널 위젯에 상품 정보 로드(상품 id 정보, 기존 대표 이미지 삭제 및 새로운 대표 이미지 추가, 상태 업데이트)
        args:
            product_data(dict) : dynamoDB에서 조회한 상품 개별 딕셔너리 정보(좌측 패널 위젯에서 특정 상품 클릭시 데이터 전달받음) \n
                                 ProductListWidget 클래스에서 정의한 커스텀 Signal이 전송하는 데이터 
        return:
            None
        """
        self.current_product = product_data
        
        # 상품 정보 업데이트
        product_id = product_data.get('product_id', 'Unknown')
        self.product_info_label.setText(f"상품 ID: {product_id}")
        
        # 이전 선택 초기화
        self.representative_images = {}
        self.color_variant_images = {}
        
        self.update_display()
    
    def is_main_representative_complete(self) -> bool:
        """대표 이미지 3개가 모두 선택되었는지 확인"""
        required_types = {'model_wearing', 'front_cutout', 'back_cutout'}
        selected_types = set(self.representative_images.keys())
        return required_types == selected_types
    
    def get_missing_main_types(self) -> List[str]:
        """대표 이미지에서 누락된 타입들 반환"""
        required_types = {'model_wearing', 'front_cutout', 'back_cutout'}
        selected_types = set(self.representative_images.keys())
        missing_types = required_types - selected_types
        
        type_names = {
            'model_wearing': '모델 착용',
            'front_cutout': '정면 누끼',
            'back_cutout': '후면 누끼'
        }
        
        return [type_names.get(t, t) for t in missing_types]
    
    def add_representative_image(self, image_data: Dict[str, Any], image_type: str):
        """대표 이미지 추가(메인 이미지 뷰어에서 대표 이미지 선정 후 버튼 누른 경우 선택된 이미지 데이터 및 타입 전달)
        args:
            image_data(dict) : 대표 이미지 데이터(딕셔너리) \n
            image_type(str) : 대표 이미지 타입(문자열) \n
        return:
            None
        """
        if image_type in ['model_wearing', 'front_cutout', 'back_cutout']:
            # 대표 이미지 추가
            self.representative_images[image_type] = image_data
            type_name = self.get_type_display_name(image_type)
            self.main_status_label.setText(f"{type_name} 이미지가 대표 이미지로 선정되었습니다")
        elif image_type in ['color_variant', 'color_variant_front']:
            # 색상 변형 이미지 추가 (정면 누끼만)
            if not self.is_main_representative_complete():
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "경고", "대표 이미지 3개를 먼저 선정해주세요.")
                return
            
            # 색상 변형 이미지는 순서대로 저장 (color_1, color_2, ...)
            color_index = len(self.color_variant_images) + 1
            color_key = f"color_{color_index}"
            self.color_variant_images[color_key] = image_data
            self.color_status_label.setText(f"색상 변형 {color_index}번 이미지가 추가되었습니다")
        
        self.update_display()
    
    def remove_representative_image(self, image_key: str):
        """대표 이미지 제거"""
        # 대표 이미지에서 제거 시도
        if image_key in self.representative_images:
            del self.representative_images[image_key]
            type_name = self.get_type_display_name(image_key)
            self.main_status_label.setText(f"{type_name} 이미지가 제거되었습니다")
            self.update_display()
            return
        
        # 색상 변형 이미지에서 제거 시도
        if image_key in self.color_variant_images:
            del self.color_variant_images[image_key]
            # 색상 변형 이미지 키 재정렬
            self._reorder_color_variants()
            self.color_status_label.setText(f"색상 변형 이미지가 제거되었습니다")
            self.update_display()
            return
    
    def _reorder_color_variants(self):
        """색상 변형 이미지 키 재정렬"""
        variants = list(self.color_variant_images.values())
        self.color_variant_images = {}
        for i, image_data in enumerate(variants, 1):
            self.color_variant_images[f"color_{i}"] = image_data
    
    def get_type_display_name(self, image_type: str) -> str:
        """타입 표시명 반환"""
        type_names = {
            'model_wearing': '모델 착용',
            'front_cutout': '정면 누끼',
            'back_cutout': '후면 누끼',
            # 기존 타입도 유지 (호환성)
            'main': '메인',
            'color_variant': '색상',
            'detail': '상세',
            'other': '기타'
        }
        return type_names.get(image_type, image_type)
    
    def update_display(self):
        """
        이 update_display() 함수는 대표 이미지 패널의 화면을 새로고침하는 역할을 합니다.
        주요 동작: \n
            - 기존 위젯 제거: 모든 기존 대표 이미지 위젯들을 역순으로 순회하며 삭제 \n
            - 메모리 정리: deleteLater()를 사용해 위젯을 안전하게 제거 \n
            - 화면 갱신 준비: 새로운 대표 이미지들을 표시할 수 있도록 레이아웃을 초기화 \n
        사용 시점: \n
            - 새로운 대표 이미지가 추가될 때 \n
            - 대표 이미지가 제거될 때 \n
            - 상품이 변경될 때 \n
            - 초기화할 때 \n
        이 함수는 UI의 일관성을 유지하고 메모리 누수를 방지하는 중요한 역할을 합니다. \n
        return:
            None
        """
        # 대표 이미지 영역 업데이트 - 고정된 순서로 배치
        self.clear_layout(self.main_rep_grid_layout)
        
        # 고정된 순서 정의: 모델 -> 정면 -> 후면
        image_types_order = ['model_wearing', 'front_cutout', 'back_cutout']
        
        for image_type in image_types_order:
            if image_type in self.representative_images:
                # 선택된 이미지가 있는 경우
                image_data = self.representative_images[image_type]
                rep_widget = RepresentativeImageWidget(image_data, image_type, True, self.image_cache)
                rep_widget.remove_requested.connect(self.remove_representative_image)
                self.main_rep_grid_layout.addWidget(rep_widget)
            else:
                # 선택되지 않은 타입에 대해서는 플레이스홀더 표시
                placeholder_widget = PlaceholderImageWidget(image_type)
                self.main_rep_grid_layout.addWidget(placeholder_widget)
        
        # 색상 변형 영역 업데이트
        self.clear_layout(self.color_grid_layout)
        for image_key, image_data in self.color_variant_images.items():
            variant_widget = RepresentativeImageWidget(image_data, image_key, False, self.image_cache)
            variant_widget.remove_requested.connect(self.remove_representative_image)
            self.color_grid_layout.insertWidget(self.color_grid_layout.count() - 1, variant_widget)
        
        # 상태 업데이트
        self.update_status()
    
    def clear_layout(self, layout):
        """레이아웃 정리"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.spacerItem() and layout != self.color_grid_layout:
                # 색상 그리드 레이아웃의 마지막 스트레치는 유지
                pass
    
    def update_status(self):
        """상태 정보 업데이트"""
        main_count = len(self.representative_images)
        color_count = len(self.color_variant_images)
        total_count = main_count + color_count
        
        self.selection_summary.setText(f"선택된 이미지: 대표 {main_count}개, 색상 변형 {color_count}개")
        
        # 대표 이미지 3개 완성 여부 확인
        is_main_complete = self.is_main_representative_complete()
        
        # 완료 버튼 활성화 조건: 대표 이미지 3개 + 색상 변형 이미지 1개 이상
        is_complete = is_main_complete and color_count > 0
        self.complete_btn.setEnabled(is_complete)
        
        # 대표 이미지 영역 상태 업데이트
        if main_count == 0:
            self.main_status_label.setText("대표 이미지 3개를 선정해주세요")
        elif not is_main_complete:
            missing_types = self.get_missing_main_types()
            self.main_status_label.setText(f"{', '.join(missing_types)} 이미지를 선정해주세요")
        else:
            self.main_status_label.setText("대표 이미지 3개 선정 완료!")
        
        # 색상 변형 영역 상태 업데이트
        if not is_main_complete:
            self.color_status_label.setText("대표 이미지 3개를 먼저 선정해주세요")
        elif color_count == 0:
            self.color_status_label.setText("큐레이션 완료를 위해 색상 변형 이미지를 최소 1개 이상 선택해주세요")
        else:
            self.color_status_label.setText(f"{color_count}개의 색상 변형 이미지가 추가되었습니다 (큐레이션 완료 가능)")
    
    def clear_representatives(self):
        """대표 이미지 초기화"""
        reply = QMessageBox.question(
            self, 
            "초기화 확인",
            "선정된 모든 이미지를 초기화하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.representative_images = {}
            self.color_variant_images = {}
            self.update_display()
            self.main_status_label.setText("모든 이미지가 초기화되었습니다")
            self.color_status_label.setText("대표 이미지 3개를 먼저 선정해주세요")
    
    def auto_clear_representatives(self):
        """대표 이미지 자동 초기화 (확인 팝업 없음) - 큐레이션 완료 후 사용"""
        self.representative_images = {}
        self.color_variant_images = {}
        self.update_display()
        
        # 상태 메시지를 초기화 상태로 복원
        self.main_status_label.setText("큐레이션이 완료되어 자동으로 초기화되었습니다")
        self.main_status_label.setStyleSheet("color: #155724; background-color: #d4edda; font-size: 11px; padding: 6px; border-radius: 3px;")
        
        self.color_status_label.setText("대표 이미지 3개를 먼저 선정해주세요")
        self.color_status_label.setStyleSheet("color: #0c4a60; background-color: #d1ecf1; font-size: 11px; padding: 6px; border-radius: 3px;")
        
        # 선택 요약 초기화
        self.selection_summary.setText("선택된 대표 이미지: 0개")
        self.selection_summary.setStyleSheet("font-weight: bold; color: #212529; background-color: transparent; padding-bottom: 10px;")
        
        # 완료 버튼 원래 상태로 복원
        self.restore_complete_button()

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        try:
            # Space: 큐레이션 완료 (버튼이 활성화된 경우에만)
            if event.key() == Qt.Key_Space:
                if self.complete_btn.isEnabled():
                    self.complete_curation()
                    event.accept()
                    return
                else:
                    # 버튼이 비활성화된 경우 안내 메시지
                    self.show_status_message("❌ 대표 이미지 3개와 색상 변형 1개 이상을 선택해주세요")
                    event.accept()
                    return
            
        except Exception as e:
            logger.error(f"RepresentativePanel 키보드 이벤트 처리 오류: {str(e)}")
        
        # 처리되지 않은 키는 부모 클래스로 전달
        super().keyPressEvent(event)
    
    def show_status_message(self, message: str):
        """상태 메시지 표시 - 임시로 selection_summary에 표시"""
        try:
            original_text = self.selection_summary.text()
            self.selection_summary.setText(message)
            self.selection_summary.setStyleSheet("font-weight: bold; color: #dc3545; background-color: transparent; padding-bottom: 10px;")
            
            # 3초 후 원래 메시지로 복원
            def restore_message():
                self.selection_summary.setText(original_text)
                self.selection_summary.setStyleSheet("font-weight: bold; color: #212529; background-color: transparent; padding-bottom: 10px;")
            
            QTimer.singleShot(3000, restore_message)
            
        except Exception as e:
            logger.error(f"상태 메시지 표시 오류: {str(e)}")
    
    def show_success_status(self):
        """큐레이션 성공 상태를 패널 내에서 시각적으로 표시"""
        try:
            product_id = self.current_product.get('product_id', 'Unknown') if self.current_product else 'Unknown'
            
            # 메인 선택 요약에 성공 메시지 표시
            self.selection_summary.setText(f"✅ 큐레이션 완료! 상품 ID: {product_id}")
            self.selection_summary.setStyleSheet("font-weight: bold; color: #28a745; background-color: #d4edda; padding: 8px; border-radius: 4px; border: 1px solid #c3e6cb;")
            
            # 대표 이미지 영역 상태 업데이트
            self.main_status_label.setText("✅ 대표 이미지 3개 큐레이션 완료!")
            self.main_status_label.setStyleSheet("color: #155724; background-color: #d4edda; font-size: 11px; padding: 6px; border-radius: 3px; font-weight: bold;")
            
            # 색상 변형 영역 상태 업데이트
            color_count = len(self.color_variant_images)
            self.color_status_label.setText(f"✅ {color_count}개 색상 변형 이미지 큐레이션 완료!")
            self.color_status_label.setStyleSheet("color: #0c4a60; background-color: #d1ecf1; font-size: 11px; padding: 6px; border-radius: 3px; font-weight: bold;")
            
            # 완료 버튼을 성공 상태로 변경
            self.complete_btn.setText("✅ 큐레이션 완료됨")
            self.complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: 2px solid #20c997;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            self.complete_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"성공 상태 표시 오류: {str(e)}")

    #RECHECK : 큐레이션 버튼 클릭시 시 처리 구현 부 
    def complete_curation(self):
        """큐레이션 완료 처리"""
        if not self.current_product:
            QMessageBox.warning(self, "오류", "상품 정보가 없습니다.")
            return
        
        if not self.aws_manager:
            QMessageBox.warning(self, "오류", "AWS 연결이 설정되지 않았습니다.")
            return
        
        # 확인 팝업 추가 - 실수 방지
        class SpaceKeyMessageBox(QMessageBox):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.yes_button = None
                
            def set_yes_button(self, button):
                self.yes_button = button
                
            def keyPressEvent(self, event):
                if event.key() == Qt.Key_Space and self.yes_button:
                    self.yes_button.click()
                    event.accept()
                else:
                    super().keyPressEvent(event)
        
        msg_box = SpaceKeyMessageBox(self)
        msg_box.setWindowTitle("큐레이션 완료 확인")
        msg_box.setText(
            f"상품 ID: {self.current_product.get('product_id', 'Unknown')}\n\n"
            f"선택된 이미지:\n"
            f"• 대표 이미지: {len(self.representative_images)}개\n"
            f"• 색상 변형: {len(self.color_variant_images)}개\n\n"
            f"큐레이션을 완료하시겠습니까?\n\n"
            f"💡 Space: 확인, ESC: 취소"
        )
        msg_box.setIcon(QMessageBox.Question)
        
        # 버튼 추가
        yes_btn = msg_box.addButton("확인 (Space)", QMessageBox.YesRole)
        no_btn = msg_box.addButton("취소 (ESC)", QMessageBox.NoRole)
        
        # Space키 처리를 위해 yes 버튼 참조 설정
        msg_box.set_yes_button(yes_btn)
        
        # 키보드 단축키 설정  
        msg_box.setDefaultButton(yes_btn)  # 기본 버튼
        msg_box.setEscapeButton(no_btn)    # ESC 키는 취소 버튼
        
        # 팝업 실행
        reply = msg_box.exec()
        
        # 결과 확인 (Yes 버튼을 클릭했는지 확인)
        if msg_box.clickedButton() != yes_btn:
            return  # 취소된 경우 아무것도 하지 않음
        
        try:
            # 버튼 비활성화
            self.complete_btn.setEnabled(False)
            self.complete_btn.setText("🔄 처리 중...")
            
            # MainImageViewer에서 대기 중인 S3 이동 작업 가져오기
            pending_moves = []
            if self.main_image_viewer:
                pending_moves = self.main_image_viewer.get_pending_moves()
            
            # S3 업데이트가 필요한 경우 먼저 처리
            if pending_moves:
                self.complete_btn.setText("🔄 S3 업데이트 중...")
                
                # 워커 쓰레드로 S3 이동 작업 수행
                self.curation_worker = CurationWorker(self.aws_manager, pending_moves)
                self.curation_worker.progress_updated.connect(self.on_s3_progress)
                self.curation_worker.completed.connect(self.on_s3_completed)
                self.curation_worker.start()
            else:
                # S3 업데이트가 없으면 바로 큐레이션 저장
                self.save_curation_data()
                
        except Exception as e:
            logger.error(f"큐레이션 완료 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"큐레이션 완료 중 오류가 발생했습니다:\n{str(e)}")
            self.restore_complete_button()
    
    def on_s3_progress(self, message: str, progress: int):
        """S3 업데이트 진행 상황 업데이트"""
        try:
            self.complete_btn.setText(f"🔄 {message}")
        except Exception as e:
            logger.error(f"S3 진행 상황 업데이트 오류: {str(e)}")
    
    def on_s3_completed(self, success: bool, message: str):
        """S3 업데이트 완료 처리"""
        try:
            if success:
                # S3 업데이트 성공 시 MainImageViewer의 대기 목록 초기화
                if self.main_image_viewer:
                    self.main_image_viewer.clear_pending_moves()
                
                # 큐레이션 데이터 저장
                self.save_curation_data()
            else:
                # S3 업데이트 실패
                QMessageBox.warning(self, "S3 업데이트 실패", f"S3 업데이트에 실패했습니다:\n{message}")
                self.restore_complete_button()
                
        finally:
            # 워커 정리
            if self.curation_worker:
                self.curation_worker.quit()
                self.curation_worker.wait()
                self.curation_worker = None
    
    #TODO : 큐레이션 데이터 저장 로직 수정 필요
    def save_curation_data(self):
        """큐레이션 데이터 저장"""
        try:
            self.complete_btn.setText("🔄 큐레이션 저장 중...")
            
            # 큐레이션 데이터 구성
            curation_data = {
                'representative_images': self.representative_images,
                'color_variant_images': self.color_variant_images,
                'curation_status': 'COMPLETED',
                'timestamp': None  # AWS에서 자동 설정
            }
            
            # 상품 정보에서 필요한 데이터 추출
            sub_category = self.current_product.get('sub_category')
            product_id = self.current_product.get('product_id')
            
            # DynamoDB에 저장 - 올바른 메서드명과 파라미터 사용
            success = self.aws_manager.update_curation_result(
                sub_category=sub_category,
                product_id=product_id,
                curation_data=curation_data,
                completed_by=None  # 작업자 정보는 현재 없음
            )
            
            if success:
                # 성공 메시지를 패널 내에서 표시 (팝업 대신)
                self.show_success_status()
                self.curation_completed.emit(self.current_product.get('product_id', ''))  # 완료된 상품 id 전달
                
                
                self.restore_complete_button()
                # 3초 후 자동으로 초기화
                # QTimer.singleShot(3000, self.auto_clear_representatives)
            else:
                QMessageBox.warning(self, "오류", "큐레이션 저장에 실패했습니다.")
                self.restore_complete_button()
            
        except Exception as e:
            logger.error(f"큐레이션 데이터 저장 중 오류: {e}")
            QMessageBox.critical(self, "오류", f"큐레이션 데이터 저장 중 오류가 발생했습니다:\n{str(e)}")
            self.restore_complete_button()
    
    def restore_complete_button(self):
        """완료 버튼 원래 상태로 복원"""
        try:
            self.complete_btn.setText("큐레이션 완료 (Space)")
            
            # 원래 스타일로 복원
            self.complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """)
            
            # 완료 버튼 활성화 조건 재확인
            main_count = len(self.representative_images)
            color_count = len(self.color_variant_images)
            is_main_complete = self.is_main_representative_complete()
            is_complete = is_main_complete and color_count > 0
            self.complete_btn.setEnabled(is_complete)
            
        except Exception as e:
            logger.error(f"완료 버튼 복원 오류: {str(e)}")
    
    def clear(self):
        """패널 초기화"""
        self.current_product = None
        self.representative_images = {}
        self.color_variant_images = {}
        self.product_info_label.setText("상품을 선택해주세요")
        self.update_display()
    
    def cleanup(self):
        """정리 작업"""
        # 워커 쓰레드 정리
        if self.curation_worker:
            self.curation_worker.quit()
            self.curation_worker.wait()
            self.curation_worker = None
        # 필요한 경우 정리 작업 수행
        pass 