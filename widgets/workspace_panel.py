import os
from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal
from .image_grid import ImageGridWidget


class WorkspacePanel(QGroupBox):
    """
    이 WorkspacePanel 모듈은 중앙 작업 공간을 담당하는 패널 위젯입니다.
    
    주요 기능:
        폴더 네비게이션: 현재 폴더와 하위 폴더들을 버튼으로 표시하여 빠른 이동 가능
        이미지 그리드 표시: 선택된 폴더의 이미지들을 그리드 형태로 시각화
        대표 이미지 선택: 이미지 클릭으로 대표 이미지 선정 가능
        동적 콘텐츠 업데이트: 폴더 선택 시 자동으로 버튼과 이미지 그리드 갱신
    
    핵심 구성요소:
        QGroupBox를 상속받아 작업 공간 영역을 구분
        QScrollArea: 폴더 버튼과 이미지 그리드를 스크롤 가능하게 표시
        QHBoxLayout: 폴더 버튼들을 가로로 배치
        ImageGridWidget: 이미지들을 그리드 형태로 표시하는 커스텀 위젯 (별모양 라벨 포함)
    
    사용처:
    메인 애플리케이션의 중앙 패널로 사용되며, 사용자가 프로젝트 내 특정 폴더를 선택하고
    해당 폴더의 이미지들을 탐색하며 대표 이미지를 선정할 수 있는 인터페이스를 제공합니다.
    """

    # 이미지 클릭 시 대표 이미지 선택을 위한 시그널
    image_selected_for_representative = Signal(object, str)  # ImageLabel, group_name

    def __init__(self, parent=None):
        """
        WorkspacePanel의 생성자입니다.
        폴더 네비게이션 버튼과 이미지 그리드를 포함한 UI를 초기화합니다.
        """
        super().__init__("작업 공간", parent)
        self.parent_window = parent
        self.current_path = None
        layout = QVBoxLayout(self)

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

        layout.addWidget(self.folder_tabs_scroll_area)
        layout.addWidget(self.image_pool_scroll_area)

        # 초기 이미지 그리드 위젯 설정 - 중앙 패널은 더 큰 이미지 사용하고 별모양 라벨 표시
        self.image_grid = ImageGridWidget(thumbnail_size=300, columns=5, show_star_label=True)
        self.image_grid.image_clicked.connect(self._on_image_clicked)
        self.image_pool_scroll_area.setWidget(self.image_grid)

    def _on_image_clicked(self, image_label):
        """이미지 클릭 시 대표 이미지 선택을 위한 처리"""
        if not self.current_path:
            return
            
        # 클릭된 이미지가 어떤 그룹(model/product_only)에 속하는지 판단
        image_path = image_label.path
        group_name = self._determine_group_from_path(image_path)
        
        if group_name:
            # 메인 윈도우에 이미지 선택 신호 전달
            self.image_selected_for_representative.emit(image_label, group_name)
    
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
        선택된 경로에 따라 폴더 버튼과 이미지 그리드를 업데이트합니다.
        현재 폴더와 모든 하위 폴더를 재귀적으로 탐색하여 버튼으로 표시합니다.
        
        Args:
            path (str): 업데이트할 폴더의 전체 경로
        """
        self.current_path = path
        self._clear_folder_tabs()

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
        self._clear_folder_tabs()
        self.image_grid.clear_grid()