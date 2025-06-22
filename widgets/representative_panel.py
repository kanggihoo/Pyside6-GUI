import os
from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QTabWidget,
    QSplitter,
    QScrollArea,
    QSizePolicy,
    QLabel,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from .image_grid import ImageGridWidget


class RepresentativePanel(QGroupBox):
    """
    이 RepresentativePanel 모듈은 대표 이미지 선정을 위한 우측 패널 위젯입니다.
    이 모듈은 사용자가 제품의 대표 이미지를 색상별로 분류하여 선택할 수 있는 인터페이스를 제공합니다.
    주요 기능
        탭 기반 UI: 제품의 색상별로 탭을 생성하여 이미지들을 분류 관리
        이중 그리드 구조: 각 탭 내에서 "모델 착용"과 "제품 단독" 이미지를 세로로 분리 표시
        동적 폴더 분석: 제품 경로를 분석하여 색상 폴더 구조를 자동으로 감지하고 탭 생성
    핵심 구성요소
        QTabWidget: 색상별 탭 관리
        QSplitter: 모델/제품 단독 이미지 영역을 세로로 분할
        ImageGridWidget: 각 영역의 이미지들을 그리드로 표시
        QScrollArea: 이미지가 많을 때 스크롤 가능
    시그널
        image_selected: 이미지 클릭 시 해당 라벨과 그룹명 전달
        tab_changed: 탭 변경 시 인덱스 전달
    폴더 구조 지원
        색상별 구조: product/color/model/, product/color/product_only/
        단일 구조: product/model/, product/product_only/
    """

    image_selected = Signal(object, str)  # ImageLabel, group_name
    tab_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__("대표 이미지", parent)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # 탭 위젯의 크기 정책 설정
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.setMinimumSize(400, 300)
        
        layout.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self.tab_changed.emit)

    def setup_ui(self, product_path):
        """제품 폴더 구조를 분석하여 대표 이미지 탭들을 구성합니다."""
        # 기존 탭들을 안전하게 정리
        self.clear()
        
        try:
            if not os.path.isdir(product_path):
                return
                
            sub_items = os.listdir(product_path)
            sub_dirs = [d for d in sub_items if os.path.isdir(os.path.join(product_path, d))]

            # Case 1: product_path에 model/product_only가 직접 있는 경우
            if 'model' in sub_dirs or 'product_only' in sub_dirs:
                tab_content = self._create_tab_content(product_path)
                if tab_content:
                    self.tabs.addTab(tab_content, "Default")
                return

            # Case 2: 하위 폴더(색상)에 model/product_only가 있는 경우
            color_tabs_created = False
            for color_name in sorted(sub_dirs):
                color_path = os.path.join(product_path, color_name)
                # color_path 내에 model 이나 product_only 폴더가 있는지 확인
                try:
                    if not os.path.isdir(color_path):
                        continue
                    color_sub_dirs = [d for d in os.listdir(color_path) if os.path.isdir(os.path.join(color_path, d))]
                    if 'model' in color_sub_dirs or 'product_only' in color_sub_dirs:
                        tab_content = self._create_tab_content(color_path)
                        if tab_content:
                            self.tabs.addTab(tab_content, color_name)
                            color_tabs_created = True
                except OSError as e:
                    print(f"Error processing color folder {color_path}: {e}")
                    continue
            
            # Case 3: model/product_only 폴더가 전혀 없는 경우 - 기본 탭 생성
            if not color_tabs_created:
                tab_content = self._create_tab_content(product_path)
                if tab_content:
                    self.tabs.addTab(tab_content, "Default")
                    
        except Exception as e:
            print(f"Error setting up representative UI: {e}")
            import traceback
            traceback.print_exc()

    def _create_tab_content(self, path):
        """'대표 이미지' 패널의 각 탭에 들어갈 내용을 생성합니다."""
        try:
            splitter = QSplitter(Qt.Vertical)
            
            # model과 product_only 두 그룹 모두 처리
            for group_name in ["model", "product_only"]:
                group_path = os.path.join(path, group_name)
                
                group_box_title = f"{group_name} {'착용' if group_name == 'model' else '단독'}"
                group_box = QGroupBox(group_box_title)
                layout = QVBoxLayout(group_box)
                
                # 레이아웃 마진과 스페이싱 설정
                layout.setContentsMargins(5, 5, 5, 5)
                layout.setSpacing(5)

                # 폴더가 존재하는지 확인
                if not os.path.isdir(group_path):
                    # 폴더가 없는 경우 안내 메시지
                    message_label = self._create_message_label(
                        f"📁 {group_name} 폴더가 없습니다.\n프로젝트 구조를 확인해주세요."
                    )
                    layout.addWidget(message_label)
                    group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    splitter.addWidget(group_box)
                    continue
                
                # 폴더 내용 확인
                try:
                    files_in_group = os.listdir(group_path)
                    image_files = [f for f in files_in_group if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
                    
                    if len(image_files) == 0:
                        # 이미지가 없는 경우 안내 메시지
                        group_type = "모델 착용" if group_name == "model" else "제품 단독"
                        message_label = self._create_message_label(
                            f"🖼️ {group_type} 대표 이미지가 없습니다.\n\n"
                            f"중앙 작업 영역에서 {group_type} 이미지를\n"
                            f"선택하여 대표 이미지를 설정해주세요."
                        )
                        layout.addWidget(message_label)
                        group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        splitter.addWidget(group_box)
                        continue
                        
                except Exception as e:
                    # 폴더 읽기 오류 시 안내 메시지
                    message_label = self._create_message_label(
                        f"❌ 폴더를 읽을 수 없습니다.\n{str(e)}"
                    )
                    layout.addWidget(message_label)
                    group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    splitter.addWidget(group_box)
                    continue
                
                # 이미지가 있는 경우 - 기존 로직 유지
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                
                # 스크롤 영역의 최소 크기 설정
                scroll_area.setMinimumHeight(200)
                scroll_area.setMinimumWidth(300)

                image_grid = ImageGridWidget(thumbnail_size=150, columns=3, show_star_label=False)  # 우측 패널용 작은 크기, 별모양 라벨 없음
                image_grid.populate(group_path)
                
                # ImageGrid의 크기 정책 설정
                image_grid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                
                # 이미지 그리드가 제대로 표시되도록 크기 힌트 설정
                if len(image_grid.get_labels()) > 0:
                    # 이미지가 있는 경우 적절한 크기 설정 (작은 썸네일 크기에 맞게 조정)
                    cols = 3
                    rows = (len(image_grid.get_labels()) + cols - 1) // cols
                    min_width = min(150 * cols + 50, 500)  # 패딩과 여백 포함, 최대 500픽셀
                    min_height = min(150 * rows + 50, 800)  # 패딩과 여백 포함, 최대 800픽셀
                    image_grid.setMinimumSize(min_width, min_height)
                
                image_grid.image_clicked.connect(
                    lambda label, g=group_name: self.image_selected.emit(label, g)
                )

                scroll_area.setWidget(image_grid)
                layout.addWidget(scroll_area)
                
                # 그룹박스의 크기 정책 설정
                group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                splitter.addWidget(group_box)

            # 만약 어떤 위젯도 추가되지 않았다면 (모든 폴더가 없는 경우) 기본 메시지 표시
            if splitter.count() == 0:
                default_group_box = QGroupBox("대표 이미지")
                default_layout = QVBoxLayout(default_group_box)
                default_layout.setContentsMargins(5, 5, 5, 5)
                
                message_label = self._create_message_label(
                    "📂 대표 이미지 폴더 구조를 설정해주세요.\n\n"
                    "필요한 폴더:\n"
                    "• model/ (모델 착용 이미지)\n"
                    "• product_only/ (제품 단독 이미지)"
                )
                default_layout.addWidget(message_label)
                default_group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                splitter.addWidget(default_group_box)

            # 스플리터 설정 - 항상 최소 1개 이상의 그룹박스가 있음
            if splitter.count() > 0:
                splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                splitter.setChildrenCollapsible(False)  # 자식 위젯이 완전히 축소되지 않도록
                
                # Qt의 이벤트 루프가 처리되도록 잠시 대기 - 안전한 참조 사용
                from PySide6.QtCore import QTimer
                import weakref
                splitter_ref = weakref.ref(splitter)  # 약한 참조 사용
                
                def update_splitter():
                    splitter_obj = splitter_ref()  # 약한 참조에서 객체 가져오기
                    if splitter_obj is not None:  # 객체가 아직 살아있는지 확인
                        try:
                            sizes = [300] * splitter_obj.count()
                            splitter_obj.setSizes(sizes)
                        except RuntimeError:
                            # C++ 객체가 이미 삭제된 경우 무시
                            pass
                
                QTimer.singleShot(100, update_splitter)  # 100ms 후에 크기 설정

            return splitter
        except Exception as e:
            print(f"Error creating tab content for {path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_message_label(self, message):
        """안내 메시지를 표시하는 라벨을 생성합니다."""
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        
        # 폰트 설정
        font = QFont()
        font.setPointSize(12)
        label.setFont(font)
        
        # 스타일 설정
        label.setStyleSheet("""
            QLabel {
                color: #666666;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
            }
        """)
        
        # 크기 정책 설정
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setMinimumHeight(150)
        
        return label

    def sync_tab(self, item_path, current_product_path):
        """좌측 트리 선택에 맞춰 우측 대표 이미지 탭을 자동으로 선택합니다."""
        dir_name = os.path.basename(item_path)
        is_product_level = current_product_path == item_path

        for i in range(self.tabs.count()):
            tab_name = self.tabs.tabText(i)
            if not is_product_level and tab_name == dir_name:
                self.tabs.setCurrentIndex(i)
                return
            if is_product_level and tab_name == "Default":
                self.tabs.setCurrentIndex(i)
                return
    
    def clear(self):
        """탭들을 안전하게 정리합니다."""
        try:
            # 각 탭의 위젯들을 명시적으로 정리
            while self.tabs.count() > 0:
                widget = self.tabs.widget(0)
                self.tabs.removeTab(0)
                if widget:
                    widget.deleteLater()
        except Exception as e:
            print(f"Error clearing tabs: {e}")
            # 기본 clear도 시도
            try:
                self.tabs.clear()
            except:
                pass 