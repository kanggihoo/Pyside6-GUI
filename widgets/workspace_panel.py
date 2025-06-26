import os
import json
import shutil
from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QPushButton,
    QLabel,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from .image_grid import ImageGridWidget
from .image_viewer import ImageViewerDialog


class MetaJsonViewerDialog(QDialog):
    """meta.json 파일 내용을 표시하는 다이얼로그"""
    
    def __init__(self, meta_data, product_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"meta.json 뷰어 - {os.path.basename(product_path)}")
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 경로 정보 라벨
        path_label = QLabel(f"파일 위치: {os.path.join(product_path, 'meta.json')}")
        path_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(path_label)
        
        # JSON 내용 표시용 텍스트 에디터
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(self.font())  # 기본 폰트 사용
        
        # JSON을 예쁘게 포맷팅해서 표시
        if meta_data:
            formatted_json = json.dumps(meta_data, ensure_ascii=False, indent=2)
            self.text_edit.setPlainText(formatted_json)
        else:
            self.text_edit.setPlainText("meta.json 파일을 읽을 수 없습니다.")
        
        layout.addWidget(self.text_edit)
        
        # 확인 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class GroupSelectionDialog(QDialog):
    """대표 이미지를 어떤 그룹(model/product_only)으로 분류할지 선택하는 다이얼로그"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("대표 이미지 그룹 선택")
        self.setMinimumSize(400, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 설명 라벨
        info_label = QLabel(f"다음 이미지를 어떤 그룹의 대표 이미지로 설정하시겠습니까?\n\n파일: {os.path.basename(image_path)}")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(info_label)
        
        # 라디오 버튼 그룹
        self.button_group = QButtonGroup()
        
        self.model_radio = QRadioButton("모델 착용 이미지 (model)")
        self.model_radio.setChecked(True)  # 기본 선택
        self.button_group.addButton(self.model_radio)
        
        self.product_only_radio = QRadioButton("제품 단독 이미지 (product_only)")
        self.button_group.addButton(self.product_only_radio)
        
        layout.addWidget(self.model_radio)
        layout.addWidget(self.product_only_radio)
        
        # 추가 설명
        note_label = QLabel("\n선택한 그룹의 폴더가 없으면 자동으로 생성되며,\n이미지 파일이 해당 폴더로 이동됩니다.")
        note_label.setStyleSheet("color: #666; font-size: 12px;")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        
        # 확인/취소 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_selected_group(self):
        """선택된 그룹명을 반환합니다."""
        if self.model_radio.isChecked():
            return "model"
        elif self.product_only_radio.isChecked():
            return "product_only"
        return None


class WorkspacePanel(QGroupBox):
    """
    이 WorkspacePanel 모듈은 중앙 작업 공간을 담당하는 패널 위젯입니다.
    
    주요 기능:
        폴더 네비게이션: 현재 폴더와 하위 폴더들을 버튼으로 표시하여 빠른 이동 가능
        이미지 그리드 표시: 선택된 폴더의 이미지들을 그리드 형태로 시각화
        대표 이미지 선택: 이미지 클릭으로 대표 이미지 선정 가능
        동적 콘텐츠 업데이트: 폴더 선택 시 자동으로 버튼과 이미지 그리드 갱신
        색상 정보 표시: meta.json의 색상 정보를 참고용으로 표시
        meta.json 뷰어: 전체 meta.json 내용을 볼 수 있는 다이얼로그 제공
    
    핵심 구성요소:
        QGroupBox를 상속받아 작업 공간 영역을 구분
        QScrollArea: 폴더 버튼과 이미지 그리드를 스크롤 가능하게 표시
        QHBoxLayout: 폴더 버튼들을 가로로 배치
        ImageGridWidget: 이미지들을 그리드 형태로 표시하는 커스텀 위젯 (별모양 라벨 포함)
        색상 정보 라벨: 제품의 색상 정보를 참고용으로 표시
        meta.json 뷰어 버튼: 전체 메타데이터를 확인할 수 있는 버튼
    
    사용처:
    메인 애플리케이션의 중앙 패널로 사용되며, 사용자가 프로젝트 내 특정 폴더를 선택하고
    해당 폴더의 이미지들을 탐색하며 대표 이미지를 선정할 수 있는 인터페이스를 제공합니다.
    """

    # 이미지 클릭 시 대표 이미지 선택을 위한 시그널
    image_selected_for_representative = Signal(object, str)  # ImageLabel, group_name

    def __init__(self, parent=None):
        """
        WorkspacePanel의 생성자입니다.
        폴더 네비게이션 버튼, 색상 정보 라벨, meta.json 뷰어 버튼, 이미지 그리드를 포함한 UI를 초기화합니다.
        """
        super().__init__("작업 공간", parent)
        self.parent_window = parent
        self.current_path = None
        self.current_product_root = None
        self.current_meta_data = None
        self.is_view_mode = False  # 이미지 보기 모드 상태
        layout = QVBoxLayout(self)

        # 상단 정보 영역 (색상 정보 + meta.json 뷰어 버튼 + 모드 전환 버튼)
        info_layout = QHBoxLayout()
        
        # 색상 정보 표시 라벨
        self.color_info_label = QLabel("색상 정보: 로딩 중...")
        self.color_info_label.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #4682b4;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        self.color_info_label.setWordWrap(True)
        self.color_info_label.setMinimumHeight(40)
        
        # 이미지 보기 모드 전환 버튼
        self.view_mode_button = QPushButton("이미지 보기 모드")
        self.view_mode_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.view_mode_button.setFixedSize(140, 40)
        self.view_mode_button.clicked.connect(self._toggle_view_mode)
        
        # meta.json 뷰어 버튼
        self.meta_viewer_button = QPushButton("meta.json 보기")
        self.meta_viewer_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.meta_viewer_button.setFixedSize(120, 40)
        self.meta_viewer_button.clicked.connect(self._show_meta_json_dialog)
        self.meta_viewer_button.setEnabled(False)  # 초기에는 비활성화
        
        info_layout.addWidget(self.color_info_label, 1)  # 확장 가능
        info_layout.addWidget(self.view_mode_button, 0)  # 고정 크기
        info_layout.addWidget(self.meta_viewer_button, 0)  # 고정 크기
        
        # 폴더 바로가기 버튼용 스크롤 영역
        self.folder_tabs_scroll_area = QScrollArea()
        self.folder_tabs_scroll_area.setWidgetResizable(True)
        self.folder_tabs_scroll_area.setFixedHeight(50)

        folder_tabs_widget = QWidget()
        self.folder_tabs_layout = QHBoxLayout(folder_tabs_widget)
        self.folder_tabs_layout.setAlignment(Qt.AlignLeft)
        self.folder_tabs_scroll_area.setWidget(folder_tabs_widget)

        # 이미지 그리드용 스크롤 영역
        self.image_pool_scroll_area = QScrollArea()
        self.image_pool_scroll_area.setWidgetResizable(True)

        # 레이아웃에 위젯들 추가
        layout.addLayout(info_layout)
        layout.addWidget(self.folder_tabs_scroll_area)
        layout.addWidget(self.image_pool_scroll_area)

        # 초기 이미지 그리드 위젯 설정 - 중앙 패널은 더 큰 이미지 사용하고 별모양 라벨 표시
        self.image_grid = ImageGridWidget(thumbnail_size=300, columns=5, show_star_label=True)
        self.image_grid.image_clicked.connect(self._on_image_clicked)
        self.image_pool_scroll_area.setWidget(self.image_grid)

    def _toggle_view_mode(self):
        """이미지 보기 모드와 대표 이미지 선택 모드 간 전환"""
        self.is_view_mode = not self.is_view_mode
        
        if self.is_view_mode:
            self.view_mode_button.setText("선택 모드")
            self.view_mode_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 12px;
                    font-weight: bold;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """)
            # 패널 제목 업데이트
            self.setTitle("작업 공간 (이미지 보기 모드)")
        else:
            self.view_mode_button.setText("이미지 보기 모드")
            self.view_mode_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 12px;
                    font-weight: bold;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)
            # 패널 제목 업데이트
            self.setTitle("작업 공간")

    def _show_meta_json_dialog(self):
        """meta.json 뷰어 다이얼로그를 표시합니다."""
        if self.current_product_root and self.current_meta_data is not None:
            dialog = MetaJsonViewerDialog(self.current_meta_data, self.current_product_root, self)
            dialog.exec()

    def _read_meta_json(self, product_path):
        """제품 폴더의 meta.json 파일을 읽어서 전체 데이터를 반환합니다."""
        try:
            meta_file_path = os.path.join(product_path, "meta.json")
            if os.path.exists(meta_file_path):
                with open(meta_file_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    return meta_data
        except Exception as e:
            pass  # 조용히 실패
        return None

    def _update_color_info_display(self, color_info):
        """색상 정보를 라벨에 표시합니다."""
        if not color_info:
            self.color_info_label.setText("색상 정보: 정보 없음")
            self.color_info_label.setStyleSheet("""
                QLabel {
                    background-color: #f5f5f5;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    padding: 8px;
                    font-weight: bold;
                    color: #666666;
                }
            """)
            return

        # 색상 정보가 문자열인지 리스트인지 확인
        if isinstance(color_info, str):
            if color_info == "one_color":
                display_text = "색상 정보: 단일 색상 (참고용)"
                bg_color = "#e8f5e8"
                border_color = "#4caf50"
                text_color = "#2e7d32"
            else:
                display_text = f"색상 정보: {color_info} (참고용)"
                bg_color = "#f0f8ff"
                border_color = "#4682b4"
                text_color = "#2c3e50"
        elif isinstance(color_info, list):
            color_count = len(color_info)
            colors_text = ", ".join(color_info)
            display_text = f"색상 정보: {color_count}개 색상 ({colors_text}) - 참고용"
            
            # 색상 개수에 따라 배경색 변경
            if color_count == 1:
                bg_color = "#e8f5e8"
                border_color = "#4caf50"
                text_color = "#2e7d32"
            elif color_count == 2:
                bg_color = "#fff3e0"
                border_color = "#ff9800"
                text_color = "#e65100"
            else:
                bg_color = "#ffebee"
                border_color = "#f44336"
                text_color = "#c62828"
        else:
            display_text = f"색상 정보: {str(color_info)} (참고용)"
            bg_color = "#f0f8ff"
            border_color = "#4682b4"
            text_color = "#2c3e50"

        self.color_info_label.setText(display_text)
        self.color_info_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                color: {text_color};
            }}
        """)

    def _find_product_root_for_path(self, path):
        """주어진 경로에서 제품 루트 경로를 찾습니다."""
        if not path:
            return None
            
        # 상위 경로를 따라 올라가면서 meta.json이 있는 폴더를 찾음
        current_path = path
        max_depth = 10  # 무한 루프 방지
        depth = 0
        
        while current_path and depth < max_depth:
            meta_file_path = os.path.join(current_path, "meta.json")
            if os.path.exists(meta_file_path):
                return current_path
            
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # 루트에 도달
                break
            current_path = parent_path
            depth += 1
        
        return None

    def _on_image_clicked(self, image_label):
        """
        이미지 클릭 시 모드에 따른 처리
        - 이미지 보기 모드: 팝업으로 이미지를 크게 표시
        - 선택 모드: 대표 이미지 선택 프로세스 진행
        """
        if not self.current_path:
            return
            
        image_path = image_label.path
        
        if self.is_view_mode:
            # 이미지 보기 모드: 팝업으로 이미지 크게 보기
            self._show_image_viewer(image_path)
        else:
            # 선택 모드: 기존 대표 이미지 선택 로직
            # 클릭된 이미지가 어떤 그룹(model/product_only)에 속하는지 판단
            group_name = self._determine_group_from_path(image_path)
            
            if group_name:
                # 기존 model/product_only 폴더의 이미지인 경우
                self.image_selected_for_representative.emit(image_label, group_name)
            else:
                # 다른 폴더의 이미지인 경우 - 그룹 선택 다이얼로그 표시
                self._handle_other_directory_selection(image_label)

    def _show_image_viewer(self, image_path):
        """이미지 뷰어 다이얼로그를 표시합니다."""
        dialog = ImageViewerDialog(image_path, self)
        dialog.exec()
    
    def _determine_group_from_path(self, image_path):
        """이미지 경로로부터 그룹명(model/product_only)을 판단합니다."""
        # 경로를 역순으로 탐색하여 model 또는 product_only 폴더를 찾음
        path_parts = os.path.normpath(image_path).split(os.sep)
        
        for part in reversed(path_parts):
            if part == 'model':
                return 'model'
            elif part == 'product_only':
                return 'product_only'
        
        return None
    
    def _handle_other_directory_selection(self, image_label):
        """다른 디렉토리의 이미지를 대표 이미지로 선택하는 처리"""
        if not self.parent_window or not self.parent_window.current_product_path:
            QMessageBox.warning(self, "알림", "제품이 선택되지 않았습니다.")
            return
            
        # 그룹 선택 다이얼로그 표시
        dialog = GroupSelectionDialog(image_label.path, self)
        if dialog.exec() == QDialog.Accepted:
            selected_group = dialog.get_selected_group()
            if selected_group:
                # 파일을 해당 그룹 폴더로 이동
                success, new_path = self._move_image_to_group_folder(image_label.path, selected_group)
                if success:
                    # 성공적으로 이동되면 대표 이미지로 설정
                    # 새로운 경로로 ImageLabel 객체를 생성
                    from widgets.image_label import ImageLabel
                    
                    # 새로운 경로의 이미지로 픽스맵 생성
                    pixmap = QPixmap(new_path)
                    if not pixmap.isNull():
                        # 적절한 크기로 스케일링 (썸네일 크기에 맞춤)
                        scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        new_label = ImageLabel(scaled_pixmap, new_path, parent=image_label.parent(), show_star_label=True)
                        
                        # 메인 윈도우에 이미지 선택 신호 전달
                        self.image_selected_for_representative.emit(new_label, selected_group)
                    else:
                        QMessageBox.warning(self, "오류", "이동된 이미지를 로드할 수 없습니다.")
                        return
                    
                    # UI 새로고침 - 현재 패널과 대표 이미지 패널 모두 업데이트
                    self._refresh_panels_after_file_move()
                    
                    # 상태바에 성공 메시지 표시 (3초 후 자동으로 원래 메시지로 복원)
                    self._show_success_message(f"✅ 이미지가 {selected_group} 폴더로 이동되고 대표 이미지로 설정되었습니다!")
                else:
                    # 오류는 여전히 팝업으로 표시 (중요한 정보이므로)
                    QMessageBox.warning(self, "오류", "파일 이동 중 오류가 발생했습니다.")
    
    def _move_image_to_group_folder(self, image_path, group_name):
        """이미지 파일을 지정된 그룹 폴더로 이동합니다."""
        try:
            if not self.parent_window or not self.parent_window.current_product_path:
                return False, None
                
            product_path = self.parent_window.current_product_path
            
            # 대상 폴더 경로 결정
            # 색상별 구조인지 확인
            current_dir = os.path.dirname(image_path)
            relative_to_product = os.path.relpath(current_dir, product_path)
            
            # 색상 폴더 구조인지 판단
            if os.sep in relative_to_product and relative_to_product != '.':
                # 색상 폴더 구조인 경우 (예: product/color/other_folder -> product/color/model)
                path_parts = relative_to_product.split(os.sep)
                color_folder = path_parts[0]
                target_dir = os.path.join(product_path, color_folder, group_name)
            else:
                # 직접 구조인 경우 (예: product/other_folder -> product/model)
                target_dir = os.path.join(product_path, group_name)
            
            # 대상 폴더가 없으면 생성
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # 파일명 중복 처리
            filename = os.path.basename(image_path)
            target_path = os.path.join(target_dir, filename)
            
            counter = 1
            original_name, ext = os.path.splitext(filename)
            while os.path.exists(target_path):
                new_filename = f"{original_name}_{counter}{ext}"
                target_path = os.path.join(target_dir, new_filename)
                counter += 1
            
            # 파일 이동
            shutil.move(image_path, target_path)
            return True, target_path
            
        except Exception as e:
            print(f"파일 이동 중 오류: {e}")
            return False, None
    
    def _refresh_panels_after_file_move(self):
        """파일 이동 후 패널들을 새로고침합니다."""
        try:
            # 현재 작업 패널 새로고침
            if self.current_path:
                self._update_image_grid(self.current_path)
            
            # 대표 이미지 패널 새로고침
            if (self.parent_window and 
                hasattr(self.parent_window, 'representative_panel') and
                self.parent_window.current_product_path):
                self.parent_window.representative_panel.setup_ui(self.parent_window.current_product_path)
                
                # 저장된 선택 상태 복원
                if hasattr(self.parent_window, '_load_current_product_selections'):
                    self.parent_window._load_current_product_selections()
                    
        except Exception as e:
            print(f"패널 새로고침 중 오류: {e}")
    
    def _show_success_message(self, message):
        """상태바에 성공 메시지를 일시적으로 표시합니다."""
        if self.parent_window and hasattr(self.parent_window, 'status_bar'):
            # 현재 상태바 메시지 백업
            current_message = self.parent_window.status_bar.currentMessage()
            
            # 성공 메시지 표시 (초록색 스타일 적용)
            self.parent_window.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                    font-weight: bold;
                }
            """)
            self.parent_window.status_bar.showMessage(message)
            
            # 3초 후 원래 메시지와 스타일로 복원
            def restore_original():
                self.parent_window.status_bar.setStyleSheet("")  # 기본 스타일로 복원
                if hasattr(self.parent_window, '_update_status_bar'):
                    self.parent_window._update_status_bar()  # 원래 상태바 업데이트 로직 호출
                else:
                    self.parent_window.status_bar.showMessage(current_message)
            
            QTimer.singleShot(3000, restore_original)  # 3초 후 실행
    
    def update_representative_selection(self, group_name, selected_image_path):
        """외부에서 대표 이미지 선택 상태가 변경되었을 때 UI를 업데이트합니다."""
        # 현재 그리드의 모든 이미지 라벨을 확인하여 선택 상태 업데이트
        for label in self.image_grid.get_labels():
            if hasattr(label, 'path'):
                # 같은 그룹에 속하는 이미지들 중에서 선택 상태 업데이트
                label_group = self._determine_group_from_path(label.path)
                if label_group == group_name:
                    if selected_image_path and label.path == selected_image_path:
                        # 대표로 선택된 이미지
                        label.select()
                    else:
                        # 선택 해제
                        label.deselect()

    def update_content(self, path):
        """
        선택된 경로에 따라 폴더 버튼, 색상 정보, 이미지 그리드를 업데이트합니다.
        현재 폴더와 모든 하위 폴더를 재귀적으로 탐색하여 버튼으로 표시합니다.
        
        Args:
            path (str): 업데이트할 폴더의 전체 경로
        """
        self.current_path = path
        self._clear_folder_tabs()

        # 색상 정보 업데이트
        product_root = self._find_product_root_for_path(path)
        if product_root:
            meta_data = self._read_meta_json(product_root)
            if meta_data:
                color_info = meta_data.get('color_info', None)
                self._update_color_info_display(color_info)
                self.current_product_root = product_root
                self.current_meta_data = meta_data
                self.meta_viewer_button.setEnabled(True)
            else:
                self._update_color_info_display(None)
                self.current_product_root = None
                self.current_meta_data = None
                self.meta_viewer_button.setEnabled(False)
        else:
            self._update_color_info_display(None)
            self.current_product_root = None
            self.current_meta_data = None
            self.meta_viewer_button.setEnabled(False)

        # 현재 폴더 버튼
        btn_current = QPushButton(f"'{os.path.basename(path)}' (최상위)")
        btn_current.setToolTip(f"{path} 와 모든 하위 폴더의 이미지를 다시 봅니다.")
        # `clicked` 시그널이 보내는 boolean 인자를 무시하고, 이미지 그리드만 업데이트합니다.
        btn_current.clicked.connect(lambda _, p=path: self._update_image_grid(p))
        self.folder_tabs_layout.addWidget(btn_current)

        # 하위 폴더들을 재귀적으로 찾아 버튼으로 추가
        sub_dirs = []
        try:
            for dirpath, dirnames, _ in os.walk(path):
                # 숨김 폴더 등 제외 로직을 여기에 추가할 수 있습니다 (예: if not dirname.startswith('.'))
                for dirname in dirnames:
                    sub_dirs.append(os.path.join(dirpath, dirname))
        except OSError:
            pass  # 경로가 존재하지 않는 등 오류 발생 시 무시

        # 경로 기준으로 정렬하여 일관된 순서를 보장합니다.
        sub_dirs.sort()

        for full_path in sub_dirs:
            # 버튼에 표시될 이름 (계층 구조 반영)
            relative_path = os.path.relpath(full_path, path)
            display_name = relative_path.replace(os.sep, " > ")
            
            button = QPushButton(display_name)
            # 전체 경로를 툴팁으로 제공합니다.
            button.setToolTip(f"{full_path} 폴더 및 하위 폴더의 이미지를 봅니다.")
            # 버튼 클릭 시 이미지 그리드만 업데이트하도록 변경합니다.
            button.clicked.connect(lambda _, p=full_path: self._update_image_grid(p))
            self.folder_tabs_layout.addWidget(button)

        # 패널이 처음 로드될 때, 최상위 경로의 이미지를 표시합니다.
        self._update_image_grid(path)

    def _update_image_grid(self, path):
        """
        이미지 그리드의 내용을 업데이트합니다.
        
        Args:
            path (str): 이미지를 표시할 폴더의 전체 경로
        """
        if not path or not os.path.isdir(path):
            # 경로가 유효하지 않으면 그리드 내용만 비웁니다.
            self.image_grid.clear_grid()
            return

        self.image_grid.populate(path)
        
        # 그리드 업데이트 후 현재 대표 이미지 선택 상태를 반영
        if self.parent_window and hasattr(self.parent_window, 'representative_selections'):
            if self.parent_window.current_product_path in self.parent_window.representative_selections:
                selections = self.parent_window.representative_selections[self.parent_window.current_product_path]
                for group_name, selected_path in selections.items():
                    self.update_representative_selection(group_name, selected_path)

    def _clear_folder_tabs(self):
        """폴더 바로가기 버튼들을 모두 제거합니다."""
        while self.folder_tabs_layout.count():
            child = self.folder_tabs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clear_content(self):
        """패널의 모든 내용을 초기화합니다."""
        self.current_path = None
        self.current_product_root = None
        self.current_meta_data = None
        self._clear_folder_tabs()
        self.image_grid.clear_grid()
        self.color_info_label.setText("색상 정보: 폴더를 선택해주세요")
        self.color_info_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
                color: #666666;
            }
        """)
        self.meta_viewer_button.setEnabled(False)