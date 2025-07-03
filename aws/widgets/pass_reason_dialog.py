#!/usr/bin/env python3
"""
상품 보류(Pass) 이유를 입력받는 다이얼로그
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QButtonGroup, QRadioButton, QTextEdit,
                               QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional


class PassReasonDialog(QDialog):
    """상품 보류(Pass) 이유를 입력받는 다이얼로그"""
    
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.selected_reason = None
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        self.setWindowTitle("상품 보류 이유 선택")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        # 상품 ID 표시
        id_label = QLabel(f"상품 ID: {self.product_id}")
        layout.addWidget(id_label)
        
        # 안내 메시지
        guide_label = QLabel("보류 처리 이유를 선택하거나 직접 입력해주세요.")
        guide_label.setWordWrap(True)
        layout.addWidget(guide_label)
        
        # 라디오 버튼 그룹
        self.button_group = QButtonGroup(self)
        
        # 미리 정의된 이유들
        predefined_reasons = [
            "이미지 품질 불량",
            "상품 정보 부족",
            "이미지 누락",
            "잘못된 카테고리",
            "기타 (직접 입력)"
        ]
        
        # 라디오 버튼들 생성
        for i, reason in enumerate(predefined_reasons):
            radio = QRadioButton(reason)
            layout.addWidget(radio)
            self.button_group.addButton(radio, i)
            if i == len(predefined_reasons) - 1:  # "기타" 옵션
                radio.toggled.connect(self.on_other_option_toggled)
        
        # 직접 입력 텍스트 영역
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("보류 이유를 직접 입력해주세요.")
        self.text_edit.setMaximumHeight(100)
        self.text_edit.setEnabled(False)  # 초기에는 비활성화
        layout.addWidget(self.text_edit)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("확인")
        self.ok_btn.clicked.connect(self.accept_reason)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def on_other_option_toggled(self, checked):
        """'기타' 옵션 선택 시 텍스트 입력 활성화/비활성화"""
        self.text_edit.setEnabled(checked)
        if not checked:
            self.text_edit.clear()
    
    def accept_reason(self):
        """선택된 이유 저장 및 다이얼로그 종료"""
        selected_button = self.button_group.checkedButton()
        if not selected_button:
            QMessageBox.warning(self, "입력 필요", "보류 이유를 선택하거나 입력해주세요.")
            return
            
        if selected_button.text() == "기타 (직접 입력)":
            reason_text = self.text_edit.toPlainText().strip()
            if not reason_text:
                QMessageBox.warning(self, "입력 필요", "보류 이유를 입력해주세요.")
                return
            self.selected_reason = reason_text
        else:
            self.selected_reason = selected_button.text()
            
        self.accept() 