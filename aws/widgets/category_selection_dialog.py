#!/usr/bin/env python3
"""
카테고리 선택 다이얼로그
사용자가 main 카테고리와 sub 카테고리를 선택할 수 있는 다이얼로그
"""

import json
from typing import Optional, Tuple
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QGroupBox, QMessageBox,
                               QTextEdit, QSplitter)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class CategorySelectionDialog(QDialog):
    """카테고리 선택 다이얼로그"""
    
    category_selected = Signal(str, int)  # main_category, sub_category
    
    def __init__(self, aws_manager, parent=None):
        super().__init__(parent)
        self.aws_manager = aws_manager
        self.selected_main_category = None
        self.selected_sub_category = None
        self.categories_info = None
        
        self.setup_ui()
        self.load_categories()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("카테고리 선택")
        self.setModal(True)
        self.resize(600, 500)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        
        # 제목
        title_label = QLabel("큐레이션할 카테고리를 선택해주세요")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 스플리터로 좌우 분할
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 왼쪽: 카테고리 선택
        self.setup_selection_panel(splitter)
        
        # 오른쪽: 정보 표시
        self.setup_info_panel(splitter)
        
        # 스플리터 비율 설정
        splitter.setSizes([300, 300])
        
        # 버튼 영역
        self.setup_button_area(main_layout)
    
    def setup_selection_panel(self, parent):
        """카테고리 선택 패널 설정"""
        selection_group = QGroupBox("카테고리 선택")
        selection_layout = QVBoxLayout(selection_group)
        
        # 메인 카테고리 선택
        main_category_layout = QHBoxLayout()
        main_category_layout.addWidget(QLabel("메인 카테고리:"))
        
        self.main_category_combo = QComboBox()
        self.main_category_combo.currentTextChanged.connect(self.on_main_category_changed)
        main_category_layout.addWidget(self.main_category_combo)
        
        selection_layout.addLayout(main_category_layout)
        
        # 서브 카테고리 선택
        sub_category_layout = QHBoxLayout()
        sub_category_layout.addWidget(QLabel("서브 카테고리:"))
        
        self.sub_category_combo = QComboBox()
        self.sub_category_combo.currentTextChanged.connect(self.on_sub_category_changed)
        sub_category_layout.addWidget(self.sub_category_combo)
        
        selection_layout.addLayout(sub_category_layout)
        
        # 선택된 카테고리 정보
        self.selection_info_label = QLabel("카테고리를 선택하세요")
        self.selection_info_label.setWordWrap(True)
        self.selection_info_label.setStyleSheet("padding: 10px; background-color: #f8f9fa; color: #495057; border: 1px solid #dee2e6; border-radius: 5px;")
        selection_layout.addWidget(self.selection_info_label)
        
        selection_layout.addStretch()
        parent.addWidget(selection_group)
    
    def setup_info_panel(self, parent):
        """정보 표시 패널 설정"""
        info_group = QGroupBox("카테고리 정보")
        info_layout = QVBoxLayout(info_group)
        
        # 전체 통계 정보
        self.stats_label = QLabel("통계 정보를 로딩 중...")
        self.stats_label.setWordWrap(True)
        info_layout.addWidget(self.stats_label)
        
        # 상세 정보 (JSON 형태)
        detail_label = QLabel("상세 정보:")
        info_layout.addWidget(detail_label)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        info_layout.addWidget(self.detail_text)
        
        parent.addWidget(info_group)
    
    def setup_button_area(self, parent_layout):
        """버튼 영역 설정"""
        button_layout = QHBoxLayout()
        
        # 새로고침 버튼
        refresh_button = QPushButton("새로고침")
        refresh_button.clicked.connect(self.load_categories)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # 확인 버튼
        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.accept_selection)
        self.ok_button.setEnabled(False)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        parent_layout.addLayout(button_layout)
    
    def load_categories(self):
        """카테고리 정보 로드"""
        try:
            # DynamoDB에서 카테고리 메타데이터 조회
            metadata = self.aws_manager.get_category_metadata()
            
            if metadata is None:
                QMessageBox.warning(self, "카테고리 정보 없음", 
                                  "카테고리 메타데이터가 없습니다.\n초기 데이터 업로드를 먼저 실행해주세요.")
                return
            
            # categories_info 파싱
            categories_info = metadata.get('categories_info')
            if isinstance(categories_info, str):
                categories_info = json.loads(categories_info)
            
            self.categories_info = categories_info
            
            # 메인 카테고리 콤보박스 업데이트
            self.main_category_combo.clear()
            self.main_category_combo.addItem("-- 선택하세요 --", None)
            
            main_categories = categories_info.get('main_categories', [])
            for main_category in main_categories:
                self.main_category_combo.addItem(main_category, main_category)
            
            # 통계 정보 업데이트
            self.update_stats_info()
            
            # 상세 정보 업데이트
            self.update_detail_info()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"카테고리 정보 로드 중 오류가 발생했습니다:\n{str(e)}")
    
    def on_main_category_changed(self, main_category_text):
        """메인 카테고리 변경 시 처리"""
        self.sub_category_combo.clear()
        self.sub_category_combo.addItem("-- 선택하세요 --", None)
        
        main_category = self.main_category_combo.currentData()
        if main_category and self.categories_info:
            # 서브 카테고리 목록 업데이트
            sub_categories = self.categories_info.get('sub_categories', {}).get(main_category, [])
            
            for sub_category in sub_categories:
                # 제품 수 정보도 함께 표시
                product_count = self.categories_info.get('product_counts', {}).get(main_category, {}).get(str(sub_category), 0)
                display_text = f"{sub_category} ({product_count}개 제품)"
                self.sub_category_combo.addItem(display_text, sub_category)
        
        self.selected_main_category = main_category
        self.update_selection_info()
        self.check_selection_complete()
    
    def on_sub_category_changed(self, sub_category_text):
        """서브 카테고리 변경 시 처리"""
        self.selected_sub_category = self.sub_category_combo.currentData()
        self.update_selection_info()
        self.check_selection_complete()
    
    def update_selection_info(self):
        """선택 정보 업데이트"""
        if self.selected_main_category and self.selected_sub_category:
            # 선택된 카테고리의 제품 수 정보
            product_count = 0
            if self.categories_info:
                product_count = self.categories_info.get('product_counts', {}).get(
                    self.selected_main_category, {}
                ).get(str(self.selected_sub_category), 0)
            
            info_text = f"""
선택된 카테고리:
• 메인 카테고리: {self.selected_main_category}
• 서브 카테고리: {self.selected_sub_category}
• 제품 수: {product_count:,}개

이 카테고리로 큐레이션 작업을 시작하겠습니다.
            """.strip()
            
            self.selection_info_label.setText(info_text)
            self.selection_info_label.setStyleSheet("padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; color: #155724;")
        
        elif self.selected_main_category:
            self.selection_info_label.setText(f"메인 카테고리 '{self.selected_main_category}'가 선택되었습니다.\n서브 카테고리를 선택해주세요.")
            self.selection_info_label.setStyleSheet("padding: 10px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; color: #856404;")
        
        else:
            self.selection_info_label.setText("카테고리를 선택해주세요")
            self.selection_info_label.setStyleSheet("padding: 10px; background-color: #f8f9fa; color: #495057; border: 1px solid #dee2e6; border-radius: 5px;")
    
    def update_stats_info(self):
        """통계 정보 업데이트"""
        if not self.categories_info:
            self.stats_label.setText("카테고리 정보가 없습니다.")
            return
        
        total_products = self.categories_info.get('total_products', 0)
        main_categories = self.categories_info.get('main_categories', [])
        product_counts = self.categories_info.get('product_counts', {})
        
        stats_text = f"전체 통계:\n"
        stats_text += f"• 총 제품 수: {total_products:,}개\n"
        stats_text += f"• 메인 카테고리 수: {len(main_categories)}개\n\n"
        
        stats_text += "카테고리별 제품 수:\n"
        for main_cat in main_categories:
            cat_total = sum(product_counts.get(main_cat, {}).values())
            stats_text += f"• {main_cat}: {cat_total:,}개\n"
        
        self.stats_label.setText(stats_text)
    
    def update_detail_info(self):
        """상세 정보 업데이트"""
        if self.categories_info:
            detail_json = json.dumps(self.categories_info, indent=2, ensure_ascii=False)
            self.detail_text.setPlainText(detail_json)
        else:
            self.detail_text.setPlainText("카테고리 정보가 없습니다.")
    
    def check_selection_complete(self):
        """선택 완료 여부 확인"""
        is_complete = bool(self.selected_main_category and self.selected_sub_category)
        self.ok_button.setEnabled(is_complete)
    
    def accept_selection(self):
        """선택 확인"""
        if self.selected_main_category and self.selected_sub_category:
            # 선택 완료 시그널 발생
            self.category_selected.emit(self.selected_main_category, self.selected_sub_category)
            self.accept()
        else:
            QMessageBox.warning(self, "선택 필요", "메인 카테고리와 서브 카테고리를 모두 선택해주세요.")
    
    def get_selected_category(self) -> Optional[Tuple[str, int]]:
        """선택된 카테고리 반환"""
        if self.selected_main_category and self.selected_sub_category:
            return (self.selected_main_category, self.selected_sub_category)
        return None 