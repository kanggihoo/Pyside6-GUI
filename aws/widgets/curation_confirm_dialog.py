#!/usr/bin/env python3
"""
큐레이션 완료 확인 다이얼로그 (키보드 단축키 지원)
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional


class CurationConfirmDialog(QDialog):
    """큐레이션 완료 확인 다이얼로그 (키보드 단축키 지원)"""
    
    def __init__(self, product_id, model_count, product_only_count, color_variant_count, total_count, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.model_count = model_count
        self.product_only_count = product_only_count
        self.color_variant_count = color_variant_count
        self.total_count = total_count
        self.result = False
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        self.setWindowTitle("큐레이션 완료 확인")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        # 키보드 포커스 활성화
        self.setFocusPolicy(Qt.StrongFocus)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("큐레이션 완료 확인")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #007bff; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 상품 ID
        product_label = QLabel(f"상품 ID: {self.product_id}")
        product_label.setStyleSheet("font-size: 14px; color: #007bff; margin-bottom: 15px; font-weight: bold;")
        layout.addWidget(product_label)
        
        # 선택된 이미지 정보
        info_label = QLabel("선택된 대표 이미지:")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #007bff;")
        layout.addWidget(info_label)
        
        details_text = f"""• 모델 착용: {self.model_count}개
• 제품 단독 (누끼+색상): {self.product_only_count}개
• 색상 변형: {self.color_variant_count}개

총 {self.total_count}개 이미지로 큐레이션을 완료하시겠습니까?"""
        
        details_label = QLabel(details_text)
        details_label.setStyleSheet("font-size: 12px; color: #2c3e50; background-color: #e8f4fd; padding: 15px; border-radius: 8px; border: 2px solid #007bff; font-weight: 500;")
        details_label.setWordWrap(True)
        layout.addWidget(details_label)
        
        # 키보드 단축키 안내
        shortcut_label = QLabel("💡 키보드 단축키: Space(확인), Esc(취소)")
        shortcut_label.setStyleSheet("font-size: 11px; color: #007bff; font-style: italic; margin-top: 10px; font-weight: bold;")
        layout.addWidget(shortcut_label)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 취소 버튼
        self.cancel_btn = QPushButton("취소 (Esc)")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # 확인 버튼
        self.confirm_btn = QPushButton("확인 (Space)")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)  # 기본 버튼으로 설정
        button_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 포커스를 확인 버튼에 설정
        self.confirm_btn.setFocus()
    
    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        if event.key() == Qt.Key_Space:
            self.accept()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def accept(self):
        """확인 버튼 클릭 또는 Space 키"""
        self.result = True
        super().accept()
    
    def reject(self):
        """취소 버튼 클릭 또는 Esc 키"""
        self.result = False
        super().reject() 