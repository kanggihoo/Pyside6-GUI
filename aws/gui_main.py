#!/usr/bin/env python3
"""
AI 데이터셋 큐레이션 GUI 메인 애플리케이션
"""

import sys
import os
import logging
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QSplitter, QStatusBar, QMenuBar, 
                               QProgressBar, QLabel, QMessageBox, QDialog,
                               QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QIcon, QKeyEvent

from aws_manager import AWSManager
from image_cache import ImageCache
from widgets.main_image_viewer import MainImageViewer
from widgets.representative_panel import RepresentativePanel
from widgets.product_list_widget import ProductListWidget
from widgets.category_selection_dialog import CategorySelectionDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        super().__init__()
        self.aws_manager = None
        self.image_cache = ImageCache()
        self.current_page = 0
        self.last_evaluated_key = None
        self.selected_main_category = None
        self.selected_sub_category = None
        self.setup_ui()
        self.setup_connections()
        self.initialize_aws()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("AI 데이터셋 큐레이션 도구")
        self.setGeometry(100, 100, 1600, 900)
        
        # 메뉴바 설정
        self.setup_menu_bar()
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 스플리터 생성
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 왼쪽 패널: 상품 목록(dynamoDB에서 조회한 상품 목록을 표시)
        self.product_list_widget = ProductListWidget()
        splitter.addWidget(self.product_list_widget)
        
        # 중앙 패널: 메인 이미지 뷰어
        self.main_image_viewer = MainImageViewer()
        splitter.addWidget(self.main_image_viewer)
        
        # 오른쪽 패널: 대표 이미지 선정 패널
        self.representative_panel = RepresentativePanel()
        splitter.addWidget(self.representative_panel)
        
        # 패널 간 참조 설정
        self.main_image_viewer.set_representative_panel(self.representative_panel)
        
        # 스플리터 비율 설정 - 중앙 패널 확대
        splitter.setSizes([350, 900, 350])
        
        # 상태바 설정
        self.setup_status_bar()
    
    def setup_menu_bar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일(&F)')
        
        # 카테고리 변경 액션
        change_category_action = QAction('카테고리 변경(&C)', self)
        change_category_action.setShortcut('Ctrl+C')
        change_category_action.triggered.connect(self.show_category_selection)
        file_menu.addAction(change_category_action)
        
        file_menu.addSeparator()
        
        # 새로고침 액션
        refresh_action = QAction('새로고침(&R)', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # 종료 액션
        exit_action = QAction('종료(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu('도구(&T)')
        
        # 통계 보기 액션
        stats_action = QAction('통계 보기(&S)', self)
        stats_action.triggered.connect(self.show_statistics)
        tools_menu.addAction(stats_action)
        
        # 캐시 정리 액션
        clear_cache_action = QAction('캐시 정리(&C)', self)
        clear_cache_action.triggered.connect(self.clear_cache)
        tools_menu.addAction(clear_cache_action)
    
    def setup_status_bar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 연결 상태 레이블
        self.connection_label = QLabel("연결 상태: 확인 중...")
        self.connection_label.setStyleSheet("color: #28a745; background-color: transparent; font-weight: bold;")
        self.status_bar.addWidget(self.connection_label)
        
        # 카테고리 정보 레이블
        self.category_label = QLabel("카테고리: 선택되지 않음")
        self.category_label.setStyleSheet("color: #495057; background-color: transparent; padding-left: 20px;")
        self.status_bar.addWidget(self.category_label)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 작업 정보 레이블
        self.work_info_label = QLabel("준비 완료")
        self.status_bar.addPermanentWidget(self.work_info_label)
    
    #CHECK : 중요 함수(시그널-슬롯 연결 설정) 
    def setup_connections(self):
        """
        시그널-슬롯 연결 설정
        self.product_list_widget : ProductListWidget 클래스 인스턴스 
           - product_selected(시그널): ProductListWidget 에 정의된 커스텀 Signal(dynamoDB에서 조회한 상품 정보가 딕셔너리 형태로 저장)  
        - representative_selected : 메인 이미지 뷰어에서 대표 이미지 선정 시
        - curation_completed : 큐레이션 완료 시 상품 목록 업데이트
        - page_changed : 페이지 변경 시 상품 목록 로드
        """
        # 상품 선택 시 해당 상품의 데이터 방출 및 전달하는(시그널-슬롯 연결)
        self.product_list_widget.product_selected.connect(
            self.on_product_selected
        )
        
        #TODO : 여기 부터 다시 코드 확인 하기 
        # 메인 이미지 뷰어의 Signal(representative_selected) 시그널이 방출되면 우측 패널의 메서드(add_representative_image) 동작 , (대표이미지(dict) , 타입(str)) 전달 
        self.main_image_viewer.representative_selected.connect(
            self.representative_panel.add_representative_image
        )
        
        # 큐레이션 완료 시 상품 목록 업데이트
        self.representative_panel.curation_completed.connect(
            self.on_curation_completed
        )
        
        # 페이지 변경 시
        self.product_list_widget.page_changed.connect(
            self.load_products_page
        )
    
    def on_product_selected(self, product_data:dict):
        """
        args:
            product_data(dict) : dynamoDB에서 조회한 상품 개별 딕셔너리 정보(좌측 패널 위젯에서 특정 상품 클릭시 데이터 전달받음) \n
                                 ProductListWidget 클래스에서 정의한 커스텀 Signal이 전송하는 데이터 
        return:
            None
        """
        if self.selected_main_category: # 처음 사용자가 선택한 카테고리 정보 추가 
            # product_data에 main_category 정보 추가
            product_data['main_category'] = self.selected_main_category
        
        # 대표 이미지 패널에 상품 정보 로드
        self.representative_panel.load_product(product_data)
        
        # s3로 부터 이미지를 로드하고 메인 이미지 뷰어에 전달
        self.load_product_images(product_data)
    
    def load_product_images(self, product_data):
        """
        dynamoDB에서 조회한 정보를 바탕으로 폴더 정보 확인 후 s3에서 다운가능한 url 정보 생성 후 메인 이미지 뷰어의 .load_product_images 함수에게 전달
        args:
            product_data(dict) : dynamoDB에서 조회한 상품 개별 딕셔너리 정보(좌측 패널 위젯에서 특정 상품 클릭시 데이터 전달받음) \n
                                 ProductListWidget 클래스에서 정의한 커스텀 Signal이 전송하는 데이터 
        return:
            None
        """
        if not self.aws_manager:
            return
        
        try:
            main_category = product_data.get('main_category', self.selected_main_category)
            sub_category = self.selected_sub_category
            product_id = product_data.get('product_id')
            
            if not all([main_category, sub_category, product_id]):
                return
            
            # 모든 폴더의 이미지 URL 가져오기
            folders = ['detail', 'segment', 'summary', 'text']
            all_images = []
            
            for folder in folders:
                images = self.aws_manager.get_s3_urls(
                    main_category, sub_category, product_id, folder
                )
                all_images.extend(images)
            
            # 메인 이미지 뷰어에 이미지 로드
            # logger.info(f"s3에서 다운받을 수 있는 url 정보:")
            # for img in all_images:
            #     logger.info(f"url: {img['url']}, folder: {img['folder']}, filename: {img['filename']}")
            self.main_image_viewer.load_product_images(all_images, product_data)
            
        except Exception as e:
            logger.error(f"상품 이미지 로드 중 오류: {e}")
            QMessageBox.warning(self, "이미지 로드 오류", f"이미지를 로드하는 중 오류가 발생했습니다:\n{str(e)}")
    
    def initialize_aws(self):
        """AWS 연결 초기화"""
        try:
            self.aws_manager = AWSManager()
            
            # AWS 연결 테스트
            connection_test = self.aws_manager.test_connection()
            
            if connection_test.get('s3', False) and connection_test.get('dynamodb', False):
                self.connection_label.setText("연결 상태: 정상")
                self.connection_label.setStyleSheet("color: #28a745; background-color: transparent; font-weight: bold;")
                
                # AWS 매니저를 위젯들에 설정
                self.product_list_widget.set_aws_manager(self.aws_manager)
                self.main_image_viewer.set_image_cache(self.image_cache)
                self.main_image_viewer.set_aws_manager(self.aws_manager)  # AWS Manager 설정 추가
                self.representative_panel.set_aws_manager(self.aws_manager)
                self.representative_panel.set_image_cache(self.image_cache)
                
                # 카테고리 선택 다이얼로그 표시
                self.show_category_selection()
                
            else:
                self.connection_label.setText("연결 상태: 오류")
                self.connection_label.setStyleSheet("color: #dc3545; background-color: transparent; font-weight: bold;")
                QMessageBox.critical(self, "연결 오류", 
                                   "AWS 연결에 실패했습니다. 설정을 확인해주세요.")
                
        except Exception as e:
            self.connection_label.setText("연결 상태: 오류")
            self.connection_label.setStyleSheet("color: #dc3545; background-color: transparent; font-weight: bold;")
            QMessageBox.critical(self, "초기화 오류", f"AWS 초기화 중 오류가 발생했습니다:\n{str(e)}")
    
    def show_category_selection(self):
        """카테고리 선택 다이얼로그 표시"""
        if not self.aws_manager:
            QMessageBox.warning(self, "AWS 연결 필요", "먼저 AWS 연결을 설정해주세요.")
            return
        
        dialog = CategorySelectionDialog(self.aws_manager, self)
        dialog.category_selected.connect(self.on_category_selected)
        
        if dialog.exec() == QDialog.Accepted:
            category_info = dialog.get_selected_category()
            if category_info:
                self.selected_main_category, self.selected_sub_category = category_info
                self.update_category_display()
                self.load_initial_data()
        else:
            # 카테고리 선택이 취소된 경우 종료하거나 기본 동작 설정
            if self.selected_main_category is None:
                # 처음 실행 시 카테고리를 선택하지 않으면 앱 종료
                QMessageBox.information(self, "카테고리 선택", "카테고리를 선택해야 앱을 사용할 수 있습니다.")
                self.close()
    
    def on_category_selected(self, main_category: str, sub_category: int):
        """카테고리 선택 완료 처리"""
        self.selected_main_category = main_category
        self.selected_sub_category = sub_category
        self.update_category_display()
    
    def update_category_display(self):
        """선택된 카테고리 정보 업데이트"""
        if self.selected_main_category and self.selected_sub_category:
            self.category_label.setText(f"카테고리: {self.selected_main_category}-{self.selected_sub_category}")
            self.category_label.setStyleSheet("color: #198754; background-color: transparent; padding-left: 20px; font-weight: bold;")
            
            # 윈도우 제목에도 카테고리 정보 추가
            self.setWindowTitle(f"AI 데이터셋 큐레이션 도구 - {self.selected_main_category}/{self.selected_sub_category}")
        else:
            self.category_label.setText("카테고리: 선택되지 않음")
            self.category_label.setStyleSheet("color: #495057; background-color: transparent; padding-left: 20px;")
            self.setWindowTitle("AI 데이터셋 큐레이션 도구")
    
    def load_initial_data(self):
        """초기 데이터 로드"""
        if not self.selected_sub_category:
            QMessageBox.warning(self, "카테고리 필요", "먼저 카테고리를 선택해주세요.")
            return
        
        self.work_info_label.setText("데이터 로딩 중...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 무한 진행바
        
        # 첫 페이지 로드
        self.load_products_page(0)
    
    def load_products_page(self, page: int):
        """상품 페이지 로드"""
        if not self.selected_sub_category:
            QMessageBox.warning(self, "카테고리 필요", "먼저 카테고리를 선택해주세요.")
            return
        
        self.current_page = page
        self.work_info_label.setText(f"페이지 {page + 1} 로딩 중...")
        
        # 비동기로 상품 목록 로드 (선택된 카테고리 기반)
        self.product_list_widget.load_products_async(
            sub_category=self.selected_sub_category,
            exclusive_start_key=self.last_evaluated_key if page > 0 else None
        )
    
    def refresh_data(self):
        """데이터 새로고침"""
        if not self.selected_sub_category:
            QMessageBox.warning(self, "카테고리 필요", "먼저 카테고리를 선택해주세요.")
            return
        
        self.current_page = 0
        self.last_evaluated_key = None
        self.load_initial_data()
        self.main_image_viewer.clear()
        self.representative_panel.clear()
    
    def on_curation_completed(self, product_id: str):
        """큐레이션 완료 처리"""
        self.work_info_label.setText(f"상품 {product_id} 큐레이션 완료")
        
        # 상품 목록에서 상태 업데이트
        self.product_list_widget.update_product_status(product_id, "COMPLETED")
        
        # 3초 후 상태 메시지 리셋
        QTimer.singleShot(3000, lambda: self.work_info_label.setText("준비 완료"))
    
    def show_statistics(self):
        """통계 정보 표시"""
        if not self.aws_manager:
            return
        
        try:
            # 카테고리 메타데이터 조회
            metadata = self.aws_manager.get_category_metadata()
            
            stats_text = "작업 통계:\n\n"
            
            if metadata and 'categories_info' in metadata:
                import json
                categories_info = metadata['categories_info']
                if isinstance(categories_info, str):
                    categories_info = json.loads(categories_info)
                
                # 전체 통계
                total_products = categories_info.get('total_products', 0)
                stats_text += f"전체 제품 수: {total_products:,}개\n\n"
                
                # 선택된 카테고리 통계
                if self.selected_main_category and self.selected_sub_category:
                    category_count = categories_info.get('product_counts', {}).get(
                        self.selected_main_category, {}
                    ).get(str(self.selected_sub_category), 0)
                    
                    stats_text += f"현재 선택된 카테고리:\n"
                    stats_text += f"- {self.selected_main_category}-{self.selected_sub_category}: {category_count:,}개\n\n"
                
                # 카테고리별 통계
                product_counts = categories_info.get('product_counts', {})
                for main_cat, sub_cats in product_counts.items():
                    stats_text += f"{main_cat} 카테고리:\n"
                    for sub_cat, count in sub_cats.items():
                        stats_text += f"  - {sub_cat}: {count:,}개\n"
                    stats_text += "\n"
            else:
                stats_text += "카테고리 메타데이터를 찾을 수 없습니다.\n"
            
            QMessageBox.information(self, "작업 통계", stats_text)
            
        except Exception as e:
            QMessageBox.warning(self, "통계 오류", f"통계를 가져오는 중 오류가 발생했습니다:\n{str(e)}")
    
    def clear_cache(self):
        """이미지 캐시 정리"""
        self.image_cache.clear_cache()
        self.work_info_label.setText("캐시가 정리되었습니다.")
        QTimer.singleShot(3000, lambda: self.work_info_label.setText("준비 완료"))
    
    def keyPressEvent(self, event: QKeyEvent):
        """전역 키보드 단축키 처리"""
        key = event.key()
        
        # 현재 포커스된 위젯이 텍스트 입력 위젯인 경우 단축키 무시
        focused_widget = QApplication.focusWidget()
        if focused_widget and isinstance(focused_widget, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox)):
            super().keyPressEvent(event)
            return
        
        # 메인 이미지 뷰어가 있고, 대표 이미지 기능이 활성화된 경우에만 처리
        if hasattr(self, 'main_image_viewer') and self.main_image_viewer:
            # 1,2,3,4: 대표 이미지 모드 선택
            if key == Qt.Key_1:
                self.main_image_viewer.activate_mode_button('model_wearing')
                event.accept()
                return
            elif key == Qt.Key_2:
                self.main_image_viewer.activate_mode_button('front_cutout')
                event.accept()
                return
            elif key == Qt.Key_3:
                self.main_image_viewer.activate_mode_button('back_cutout')
                event.accept()
                return
            elif key == Qt.Key_4:
                self.main_image_viewer.activate_mode_button('color_variant')
                event.accept()
                return
            elif key == Qt.Key_Escape:
                self.main_image_viewer.activate_mode_button('clear_mode')
                event.accept()
                return
            elif key == Qt.Key_V:
                self.main_image_viewer.activate_mode_button('image_viewer')
                event.accept()
                return
        
        # 처리되지 않은 키는 부모 클래스로 전달
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 정리 작업"""
        # 캐시 정리
        if hasattr(self, 'image_cache'):
            self.image_cache.clear_cache()
        
        # 스레드 정리
        if hasattr(self, 'product_list_widget'):
            self.product_list_widget.cleanup()
        
        if hasattr(self, 'main_image_viewer'):
            # 메인 이미지 뷰어는 cleanup 메서드가 없으므로 제외
            pass
        
        if hasattr(self, 'representative_panel'):
            self.representative_panel.cleanup()
        
        event.accept()


def main():
    """메인 함수"""
    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("AI 데이터셋 큐레이션 도구")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AI Data Team")
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec())


if __name__ == '__main__':
    main()


