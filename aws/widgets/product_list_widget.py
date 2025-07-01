#!/usr/bin/env python3
"""
상품 목록 위젯
DynamoDB에서 상품 데이터를 페이지네이션으로 로드하고 표시합니다.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QListWidgetItem, QLabel, QPushButton, QComboBox,
                               QProgressBar, QMessageBox, QFrame, QSpacerItem,
                               QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QPalette
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ProductLoadThread(QThread):
    """상품 로드 스레드"""
    
    products_loaded = Signal(list, dict)  # products, last_evaluated_key
    error_occurred = Signal(str)
    
    def __init__(self, aws_manager, sub_category: int = None, status_filter: str = None,
                 exclusive_start_key: Dict[str, Any] = None, limit: int = 20):
        super().__init__()
        self.aws_manager = aws_manager
        self.sub_category = sub_category
        self.status_filter = status_filter
        self.exclusive_start_key = exclusive_start_key
        self.limit = limit
    
    def run(self):
        """스레드 실행"""
        #TODO : 여기서 좀더 케이스 별로 나눠서 처리하는게 좋을듯
        try:
            #TODO : 여기서 GSI로 필터링 + 카테고리별 조회 하면 좋을듯 
            #TODO : 맨 처음에 사용자가 작업할 영역 선택 한 뒤에 자동으로 status 필터링을 걸어서 바로 작업 진행 할 수 있도록 ? 
            # dynamoDB에서 GSI를 통해 상품 목록 조회()
            '''
            products : dynamoDB에서 case 별로 쿼리 날려서 조회 한 뒤에 Items key 값만 추출한뒤 python 딕셔너리로 변환한 데이터 리스트
            '''
            if self.status_filter and self.status_filter != "ALL":
                # 상태별 필터링
                products, last_key = self.aws_manager.get_product_by_status(
                    status=self.status_filter,
                    limit=self.limit,
                    exclusive_start_key=self.exclusive_start_key
                )
            # dynamoDB에서 카테고리별 조회(맨 처음 사용자가 작업할 서브 카테고리 선정했을때 사용)
            elif self.sub_category:
                # 서브 카테고리별 조회
                products, last_key = self.aws_manager.get_product_list(
                    sub_category=self.sub_category,
                    limit=self.limit,
                    exclusive_start_key=self.exclusive_start_key
                )
            else:
                # 전체 조회 (기본값: 1005 카테고리)
                products, last_key = self.aws_manager.get_product_list(
                    sub_category=1005,
                    limit=self.limit,
                    exclusive_start_key=self.exclusive_start_key
                )
            
            # dynamoDB에서 조회한 데이터를 Signal로 방출 => self.on_products_loaded() 함수에게 전달 
            self.products_loaded.emit(products, last_key or {})
            
        except Exception as e:
            logger.error(f"상품 로드 중 오류: {e}")
            self.error_occurred.emit(str(e))


class ProductItem(QWidget):
    """상품 아이템 위젯(각 제품 id에 대한 정보를 표시 클래스)"""
    
    def __init__(self, product_data: Dict[str, Any]):
        super().__init__()
        self.product_data = product_data
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        # 전체 위젯에 카드 스타일 적용
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 4px;
            }
            QWidget:hover {
                border-color: #007bff;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # 상품 ID
        product_id = self.product_data.get('product_id', 'Unknown')
        id_label = QLabel(f"ID: {product_id}")
        id_font = QFont()
        id_font.setBold(True)
        id_font.setPointSize(10)
        id_label.setFont(id_font)
        id_label.setStyleSheet("color: #212529; background-color: transparent; padding: 2px;")
        layout.addWidget(id_label)
        
        # 상품 정보(dynamoDB의 product_info 필드에 있는 데이터를 표시)
        product_info = self.product_data.get('product_info', {})
        if isinstance(product_info, dict):
            brand = product_info.get('brand', 'Unknown')
            product_name = product_info.get('product_name', 'Unknown')
            info_text = f"{brand} - {product_name}"
        else:
            info_text = "상품 정보 없음"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #495057; background-color: #f8f9fa; padding: 6px; border-radius: 4px; border: 1px solid #e9ecef;")
        layout.addWidget(info_label)
        
        # 상태 정보
        status_layout = QHBoxLayout()
        
        # 현재 상태
        current_status = self.product_data.get('current_status', 'PENDING')
        status_label = QLabel(f"상태: {current_status}")
        
        if current_status == 'COMPLETED':
            status_label.setStyleSheet("color: #155724; background-color: #d4edda; font-weight: bold; padding: 4px 8px; border-radius: 4px; border: 1px solid #c3e6cb;")
        elif current_status == 'IN_PROGRESS':
            status_label.setStyleSheet("color: #856404; background-color: #fff3cd; font-weight: bold; padding: 4px 8px; border-radius: 4px; border: 1px solid #ffeaa7;")
        else:
            status_label.setStyleSheet("color: #721c24; background-color: #f8d7da; font-weight: bold; padding: 4px 8px; border-radius: 4px; border: 1px solid #f5c6cb;")
        
        status_layout.addWidget(status_label)
        
        # 색상 개수
        available_colors = self.product_data.get('available_colors', [])
        if available_colors:
            color_count = len(available_colors)
            color_label = QLabel(f"색상: {color_count}개")
            color_label.setStyleSheet("color: #0056b3; background-color: #e7f1ff; padding: 3px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #b3d7ff;")
            status_layout.addWidget(color_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 마지막 업데이트 시간
        last_updated = self.product_data.get('last_updated_at', '')
        if last_updated:
            time_label = QLabel(f"업데이트: {last_updated[:10]}")  # 날짜만 표시
            time_label.setStyleSheet("color: #6c757d; background-color: #f8f9fa; font-size: 9px; padding: 3px 6px; border-radius: 3px; border: 1px solid #e9ecef;")
            layout.addWidget(time_label)
    
    def get_product_id(self) -> str:
        """상품 ID 반환"""
        return self.product_data.get('product_id', '')
    
    def get_product_data(self) -> Dict[str, Any]:
        """상품 데이터 반환"""
        return self.product_data
    
    def update_status(self, new_status: str):
        """상태 업데이트"""
        self.product_data['current_status'] = new_status
        # UI 다시 구성
        self.setup_ui()


class ProductListWidget(QWidget):
    """
    상품 목록 위젯(ProductItem 클래스를 사용하여 상품 목록을 표시)
    - product_selected : dynamoDB에서 조회한 상품 데이터정보가 QListWidgetItem에 저장된 상태에서 특정 제품 클릭시 해당 data가 딕셔너리로 형태로 방출 
                         => MainWindow 클래스에서 정의한 (self.on_product_selected) 함수에게 딕셔너리로 전달
    - page_changed : 페이지 변경 시 상품 목록 로드
    """
    
    product_selected = Signal(dict)  #
    page_changed = Signal(int)  # 페이지 변경
    
    def __init__(self):
        super().__init__()
        self.aws_manager = None
        self.current_products = []
        self.current_page = 0
        self.last_evaluated_key = None
        self.total_pages = 0
        self.load_thread = None
        self.background_color = "#bcbcbc"
        self.current_sub_category = None  # 현재 선택된 서브 카테고리
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: #e9ecef; color: #212529; border-bottom: 1px solid #dee2e6;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # 제목
        title_label = QLabel("상품 목록")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # 필터 컨트롤("ALL", "PENDING", "IN_PROGRESS", "COMPLETED") 에 따른 상품 목록 조회
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("상태:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["ALL", "PENDING", "IN_PROGRESS", "COMPLETED"])
        self.status_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addStretch()
        
        # 새로고침 버튼
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.refresh_products)
        filter_layout.addWidget(self.refresh_btn)
        
        header_layout.addLayout(filter_layout)
        layout.addWidget(header_frame)
        
        # 상품 목록
        self.product_list = QListWidget()
        self.product_list.setSelectionMode(QListWidget.SingleSelection)
        # 특정 상품 선택 시 해당 상품의 widget에 저장되어 있는 데이터를 방출 => (시그널-슬롯 연결)
        self.product_list.itemClicked.connect(self.on_item_clicked)
        
        # 리스트 위젯 스타일 개선
        self.product_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: none;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                border: none;
                padding: 4px;
                margin: 2px 0px;
                background-color: transparent;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
                border-radius: 10px;
            }
            QListWidget::item:hover {
                background-color: #f0f8ff;
                border-radius: 8px;
            }
        """)
        
        layout.addWidget(self.product_list)
        
        #RECHECK : 로딩 프로그레스바 어디있지?? 
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        layout.addWidget(self.loading_progress)
        
        # 페이지네이션 컨트롤(하단에 1,2,3,4,5 페이지 버튼 존재)
        pagination_frame = QFrame()
        pagination_frame.setStyleSheet(f"background-color: #e9ecef; color: #212529; border-top: 1px solid #dee2e6;")
        pagination_layout = QHBoxLayout(pagination_frame)
        pagination_layout.setContentsMargins(15, 10, 15, 10)
        
        self.prev_btn = QPushButton("이전")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.go_previous_page)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("페이지 1")
        pagination_layout.addWidget(self.page_label)
        
        pagination_layout.addStretch()
        
        self.next_btn = QPushButton("다음")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.go_next_page)
        pagination_layout.addWidget(self.next_btn)
        
        layout.addWidget(pagination_frame)
    
    def set_aws_manager(self, aws_manager):
        """AWS 매니저 설정"""
        self.aws_manager = aws_manager
    
    def on_filter_changed(self):
        """필터 변경 시"""
        self.refresh_products()
    
    def refresh_products(self):
        """상품 목록 새로고침"""
        self.current_page = 0
        self.last_evaluated_key = None
        self.load_products_async(sub_category=self.current_sub_category)

    #CHECK : 중요 함수(스레드 사용 하여 dynamoDB에서 데이터 조회 후 데이터 방출) 
    def load_products_async(self, sub_category: int = None, exclusive_start_key: Dict[str, Any] = None):
        """비동기로 상품 로드"""
        if not self.aws_manager:
            return
        
        # sub_category가 없으면 기본값 사용
        if sub_category is None:
            sub_category = self.current_sub_category or 1005  # 현재 카테고리 또는 기본 카테고리
        
        # 현재 서브 카테고리 업데이트
        self.current_sub_category = sub_category
        
        # 이전 스레드 정리
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.quit()
            self.load_thread.wait()
        
        # 로딩 UI 표시
        self.loading_progress.setVisible(True)
        self.loading_progress.setRange(0, 0)
        self.refresh_btn.setEnabled(False)
        
        # 스레드 생성 및 실행
        status_filter = self.status_combo.currentText()
        self.load_thread = ProductLoadThread(
            self.aws_manager,
            sub_category=sub_category,
            status_filter=status_filter,
            exclusive_start_key=exclusive_start_key,
            limit=20
        )
        
        # products_loaded 시그널이 발생하면 on_products_loaded 함수 호출
        # error_occurred 시그널이 발생하면 on_load_error 함수 호출
        self.load_thread.products_loaded.connect(self.on_products_loaded)
        self.load_thread.error_occurred.connect(self.on_load_error)
        # 스레드 실행 (.start() 메서드 호출시 run() 메서드 실행)
        self.load_thread.start()
    
    def on_products_loaded(self, products: List[Dict[str, Any]], last_evaluated_key: Dict[str, Any]):
        """
        ProductLoadThread 클래스에서 방출한 시그널을 받아서 처리하는 함수
        - products : dynamoDB에서 조회한 데이터를 딕셔너리로 변환한 데이터 리스트
        - last_evaluated_key : 다음 페이지 키(페이지네이션 처리를 위한 키)
        """
        self.current_products = products
        self.last_evaluated_key = last_evaluated_key
        
        # UI 업데이트
        self.update_product_list()
        self.update_pagination_controls()
        
        # 로딩 UI 숨김
        self.loading_progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
    
    def on_load_error(self, error_message: str):
        """로드 오류 처리"""
        self.loading_progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        
        QMessageBox.warning(self, "로드 오류", f"상품 목록을 불러오는 중 오류가 발생했습니다:\n{error_message}")
    
    def update_product_list(self):
        """
        상품 목록 UI 업데이트
        - self.current_products : dynamoDB에서 조회한 데이터를 딕셔너리로 변환한 데이터 리스트
        """
        self.product_list.clear()
        
        for product in self.current_products:
            # 아이템 위젯 생성
            item_widget = ProductItem(product)
            
            # 리스트 아이템 생성
            list_item = QListWidgetItem()
            
            # 아이템 크기 설정 (여백 포함)
            widget_size = item_widget.sizeHint()
            list_item.setSizeHint(QSize(widget_size.width(), widget_size.height() + 8))  # 상하 여백 추가
            
            # 아이템에 데이터 저장
            list_item.setData(Qt.UserRole, product)
            
            # 리스트에 추가
            self.product_list.addItem(list_item)
            self.product_list.setItemWidget(list_item, item_widget)
    
    def update_pagination_controls(self):
        """페이지네이션 컨트롤 업데이트"""
        self.page_label.setText(f"페이지 {self.current_page + 1}")
        
        # 이전 버튼
        self.prev_btn.setEnabled(self.current_page > 0)
        
        # 다음 버튼 (마지막 키가 있으면 다음 페이지 존재)
        self.next_btn.setEnabled(bool(self.last_evaluated_key))
    
    def go_previous_page(self):
        """이전 페이지로 이동"""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_changed.emit(self.current_page)
    
    def go_next_page(self):
        """다음 페이지로 이동"""
        if self.last_evaluated_key:
            self.current_page += 1
            self.load_products_async(sub_category=self.current_sub_category, exclusive_start_key=self.last_evaluated_key)
    
    def on_item_clicked(self, item: QListWidgetItem):
        """
        아이템 클릭 시
        - item : 클릭한 아이템(QListWidgetItem)
        - item.data(Qt.UserRole) : 클릭한 아이템에 저장되어 있는 데이터(ProductItem 클래스에서 정의한 데이터) 
        - Qt.UserRole은 QListWidgetItem에 저장된 사용자 정의 데이터를 가져오는 역할
        - 코드에서 item.setData(Qt.UserRole, product)로 상품 데이터를 저장할 때, product는 DynamoDB에서 조회한 상품 정보를 딕셔너리 형태로 변환한 데이터
        - 따라서 item.data(Qt.UserRole)은 해당 상품의 모든 정보가 담긴 딕셔너리를 반환합니다
        """
        product_data = item.data(Qt.UserRole)
        if product_data:
            self.product_selected.emit(product_data) # => MainWindow 클래스에서 정의한 (self.on_product_selected) 함수에게 딕셔너리로 전달
    
    def update_product_status(self, product_id: str, new_status: str):
        """특정 상품의 상태 업데이트"""
        for i in range(self.product_list.count()):
            item = self.product_list.item(i)
            product_data = item.data(Qt.UserRole)
            
            if product_data and product_data.get('product_id') == product_id:
                # 데이터 업데이트
                product_data['current_status'] = new_status
                item.setData(Qt.UserRole, product_data)
                
                # 위젯 업데이트
                item_widget = self.product_list.itemWidget(item)
                if isinstance(item_widget, ProductItem):
                    item_widget.update_status(new_status)
                break
    
    def cleanup(self):
        """정리 작업"""
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.quit()
            self.load_thread.wait()
    
    def keyPressEvent(self, event):
        """키보드 이벤트를 부모로 전달하여 전역 단축키가 작동하도록 함"""
        # 키보드 이벤트를 부모(MainWindow)로 전달
        if self.parent():
            self.parent().keyPressEvent(event)
        
        # 이벤트가 처리되지 않은 경우에만 기본 동작 수행
        if not event.isAccepted():
            super().keyPressEvent(event) 