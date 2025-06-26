import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QSplitter,
    QStatusBar,
)
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QTreeWidgetItem

from widgets.project_tree import ProjectTreeWidget
from widgets.workspace_panel import WorkspacePanel
from widgets.representative_panel import RepresentativePanel
from widgets.image_label import ImageLabel
from widgets.keyboard_navigation import KeyboardNavigationHandler

class MainWindow(QMainWindow):
    """애플리케이션의 메인 윈도우 클래스."""
    def __init__(self):
        """MainWindow의 생성자입니다."""
        super().__init__()
        
        # --- 상태 변수 초기화 ---

        # 애플리케이션의 현재 상태를 저장할 인스턴스 변수들을 초기화합니다.
        self.current_product_path = None # 현재 선택된 제품(의류)의 최상위 경로를 저장합니다.
        self.selected_model_image = None # 모델 이미지 탭에서 현재 선택된 이미지 라벨 객체를 저장합니다.
        self.selected_product_only_image = None # 제품 단독 이미지 탭에서 현재 선택된 이미지 라벨 객체를 저장합니다.
        
        # 대표 이미지 선택 상태 저장용 딕셔너리 (제품별로 저장)
        self.representative_selections = {}  # {product_path: {"model": image_path, "product_only": image_path}}
        
        # 전체 제품 목록 및 진행상황 추적
        self.all_products = []  # 전체 제품 경로 목록
        self.project_root_path = None  # 프로젝트 최상위 경로
        
        # --- UI 설정 ---
        '''
        메인 윈도우의 위치와 크기를 설정합니다. (x, y, width, height) 형식으로, 
        화면 좌측 상단에서 100, 100 픽셀 떨어진 곳에 1600x900 픽셀 크기로 윈도우를 배치합니다.
        '''
        self.setWindowTitle("AI 학습용 의류 대표 이미지 선정 GUI 툴")
        self.setGeometry(100, 100, 1600, 900)

        # --- UI 설정 ---
        '''
        메인 윈도우의 전체적인 UI 레이아웃을 설정합니다.
        '''
        self._setup_ui()
        self._connect_signals() # UI 위젯들의 시그널(이벤트)을 슬롯(이벤트 핸들러)에 연결하는 내부 메서드
        
        # 키보드 네비게이션 핸들러 초기화
        self.keyboard_handler = KeyboardNavigationHandler(self)

    # ===================================================================
    # 1. UI 초기 설정 메서드
    # ===================================================================

    def _setup_ui(self):
        """
        메인 윈도우의 전체적인 UI 레이아웃을 설정합니다.
        메뉴바, 메인 스플리터 및 3개의 핵심 패널을 생성합니다.
        """
        self._create_menus() # 메뉴바와 '파일 > 폴더 열기' 액션을 생성합니다.
        self._create_status_bar() # 상태바를 생성합니다.

        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # 각 패널 위젯 생성 및 부모-자식 관계 설정
        '''
        커스텀 패널 위젯들을 생성합니다. 각 위젯의 생성자에 self (MainWindow 인스턴스)를 전달하여 부모-자식 관계를 설정합니다. 
        이는 위젯의 생명 주기 관리 및 이벤트 전달에 중요합니다.
        '''
        self.tree_panel = ProjectTreeWidget(self) # 프로젝트 트리(파일 탐색기 역할)를 표시하는 위젯입니다.
        self.workspace_panel = WorkspacePanel(self) # 선택된 이미지나 데이터를 표시하는 작업 공간 패널입니다.
        self.representative_panel = RepresentativePanel(self) # 대표 이미지를 선정하고 관리하는 패널입니다.
        
        # self.tree_panel의 product_tree_widget를 직접 참조할 수 있도록 설정
        self.product_tree_widget = self.tree_panel


        # 스플리터에 패널 추가
        self.splitter.addWidget(self.tree_panel)
        self.splitter.addWidget(self.workspace_panel)
        self.splitter.addWidget(self.representative_panel)
        
        # 패널 초기 크기 설정
        self.splitter.setSizes([250, 950, 400])

    def _create_menus(self):
        """메뉴바와 '파일 > 폴더 열기' 액션을 생성합니다."""
        menu_bar = self.menuBar() # QMainWindow는 기본적으로 메뉴바를 가질 수 있습니다.
        menu_bar.setNativeMenuBar(False) # MacOS와 같은 운영 체제에서 네이티브 메뉴바(운영 체제 상단에 통합되는 메뉴바)를 사용하지 않고, 애플리케이션 자체 내부에 메뉴바를 표시하도록 설정
        file_menu = menu_bar.addMenu("&File") # 메뉴바에 "File"이라는 이름의 최상위 메뉴를 추가합니다. &는 "F"를 단축키로 사용할 수 있음.
        
        open_folder_action = QAction("작업 폴더 열기...", self)
        open_folder_action.triggered.connect(self._on_folder_open_clicked)
        file_menu.addAction(open_folder_action)
        
        # 대표 이미지 저장/불러오기 메뉴 추가
        file_menu.addSeparator()
        
        save_selections_action = QAction("대표 이미지 선택 저장", self)
        save_selections_action.triggered.connect(self._save_representative_selections)
        file_menu.addAction(save_selections_action)
        
        load_selections_action = QAction("대표 이미지 선택 불러오기", self)
        load_selections_action.triggered.connect(self._load_representative_selections)
        file_menu.addAction(load_selections_action)

    def _create_status_bar(self):
        """상태바를 생성하고 초기 메시지를 설정합니다."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("대표 이미지 선정을 위한 폴더를 열어주세요. | 키보드: J/j K/k (제품 이동, 한/영키 무관, J/j=이전 K/k=다음) / Cmd+J K / Ctrl+J K / ← → / PgUp PgDn")
    
    def _update_status_bar(self):
        """현재 선택된 대표 이미지 정보와 전체 진행상황으로 상태바를 업데이트합니다."""
        if not self.current_product_path:
            if self.all_products:
                # 프로젝트는 로드되었지만 제품이 선택되지 않은 상태
                progress_info = self._get_progress_info()
                self.status_bar.showMessage(f"진행상황: {progress_info['completed']}/{progress_info['total']}개 제품 완료 ({progress_info['percentage']:.1f}%) | 제품을 선택해주세요. | 키보드: J/j K/k (제품 이동, 한/영키 무관) / Cmd+J K / Ctrl+J K / ← → / PgUp PgDn")
            else:
                self.status_bar.showMessage("대표 이미지 선정을 위한 폴더를 열어주세요. | 키보드: J/j K/k (제품 이동, 한/영키 무관) / Cmd+J K / Ctrl+J K / ← → / PgUp PgDn")
            return
        
        product_name = os.path.basename(self.current_product_path)
        
        model_status = "✓ 선택됨" if self.selected_model_image else "○ 미선택"
        product_only_status = "✓ 선택됨" if self.selected_product_only_image else "○ 미선택"
        
        # 현재 제품 상태
        current_product_status = f"제품: {product_name} | 모델 착용: {model_status} | 제품 단독: {product_only_status}"
        
        # 전체 진행상황
        if self.all_products:
            progress_info = self._get_progress_info()
            progress_status = f"진행상황: {progress_info['completed']}/{progress_info['total']}개 제품 완료 ({progress_info['percentage']:.1f}%)"
            
            if self.selected_model_image and self.selected_product_only_image:
                current_product_status += " | 완료! 🎉"
            
            message = f"{current_product_status} | {progress_status} | 키보드: J/j K/k (제품 이동, 한/영키 무관) / Cmd+J K / Ctrl+J K / ← → / PgUp PgDn"
        else:
            message = f"{current_product_status} | 키보드: J/j K/k (제품 이동, 한/영키 무관) / Cmd+J K / Ctrl+J K / ← → / PgUp PgDn"
        
        self.status_bar.showMessage(message)
    
    def _get_progress_info(self):
        """전체 제품의 대표 이미지 선정 진행상황을 계산합니다."""
        if not self.all_products:
            return {"total": 0, "completed": 0, "percentage": 0.0}
        
        total_products = len(self.all_products)
        completed_products = 0
        
        for product_path in self.all_products:
            if self._is_product_completed(product_path):
                completed_products += 1
        
        percentage = (completed_products / total_products * 100) if total_products > 0 else 0.0
        
        return {
            "total": total_products,
            "completed": completed_products,
            "percentage": percentage
        }
    
    def _is_product_completed(self, product_path):
        """특정 제품의 대표 이미지 선정이 완료되었는지 확인합니다."""
        if product_path not in self.representative_selections:
            return False
        
        selections = self.representative_selections[product_path]
        
        # model과 product_only 둘 다 선택되어야 완료로 간주
        has_model = "model" in selections and selections["model"]
        has_product_only = "product_only" in selections and selections["product_only"]
        
        return has_model and has_product_only
    
    def _scan_all_products(self, project_root):
        """프로젝트 루트에서 모든 제품 폴더를 스캔합니다."""
        self.all_products = []
        
        try:
            # 프로젝트 루트의 모든 하위 폴더를 재귀적으로 확인
            self._scan_products_recursive(project_root, max_depth=5)
            
        except Exception as e:
            pass  # 조용히 실패
    
    def _scan_products_recursive(self, current_path, max_depth=3, current_depth=0):
        """재귀적으로 제품 폴더를 스캔합니다."""
        if current_depth >= max_depth:
            return
            
        try:
            items = os.listdir(current_path)
            
            for item in items:
                item_path = os.path.join(current_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                # 제품 폴더인지 확인
                if self._is_product_folder(item_path):
                    if item_path not in self.all_products:
                        self.all_products.append(item_path)
                else:
                    # 제품 폴더가 아니라면 하위 폴더를 계속 스캔
                    self._scan_products_recursive(item_path, max_depth, current_depth + 1)
                    
        except Exception as e:
            pass  # 조용히 실패
    
    def _is_product_folder(self, folder_path):
        """폴더가 제품 폴더인지 판단합니다."""
        try:
            folder_name = os.path.basename(folder_path)
            
            sub_items = os.listdir(folder_path)
            sub_dirs = [d for d in sub_items if os.path.isdir(os.path.join(folder_path, d))]
            sub_files = [f for f in sub_items if os.path.isfile(os.path.join(folder_path, f))]
            
            # Case 1: 직접 model/product_only 폴더가 있는 경우
            has_model = 'model' in sub_dirs
            has_product_only = 'product_only' in sub_dirs
            
            if has_model or has_product_only:
                return True
            
            # Case 2: 색상 폴더 하위에 model/product_only가 있는 경우
            color_folders_with_model = 0
            for sub_dir in sub_dirs:
                sub_path = os.path.join(folder_path, sub_dir)
                try:
                    sub_sub_items = os.listdir(sub_path)
                    sub_sub_dirs = [d for d in sub_sub_items if os.path.isdir(os.path.join(sub_path, d))]
                    
                    has_sub_model = 'model' in sub_sub_dirs
                    has_sub_product_only = 'product_only' in sub_sub_dirs
                    
                    if has_sub_model or has_sub_product_only:
                        color_folders_with_model += 1
                        
                except OSError as e:
                    continue
            
            if color_folders_with_model > 0:
                return True
            
            # Case 3: 숫자로 된 폴더명이면서 하위에 이미지 파일이나 관련 폴더가 있는 경우
            if folder_name.isdigit() and len(folder_name) >= 6:  # 6자리 이상 숫자인 경우 (제품 코드로 추정)
                # 이미지 파일이 직접 있거나, 의미있는 하위 폴더가 있는지 확인
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
                has_images = any(os.path.splitext(f)[1].lower() in image_extensions for f in sub_files)
                has_meaningful_dirs = False
                if len(sub_dirs) > 0:
                    try:
                        # 처음 3개 폴더만 확인하여 내용이 있는지 체크
                        for d in sub_dirs[:3]:
                            sub_dir_path = os.path.join(folder_path, d)
                            if os.path.isdir(sub_dir_path):
                                sub_dir_contents = os.listdir(sub_dir_path)
                                if len(sub_dir_contents) > 0:
                                    has_meaningful_dirs = True
                                    break
                    except:
                        has_meaningful_dirs = False
                
                if has_images or has_meaningful_dirs:
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def _load_all_representative_selections(self):
        """모든 제품의 저장된 대표 이미지 선택 상태를 로드합니다."""
        for product_path in self.all_products:
            try:
                selections_file = self._get_selections_file_path(product_path)
                if os.path.exists(selections_file):
                    with open(selections_file, 'r', encoding='utf-8') as f:
                        selections = json.load(f)
                        self.representative_selections[product_path] = selections
            except Exception as e:
                pass  # 조용히 실패
        
        completed = sum(1 for p in self.all_products if self._is_product_completed(p))

    def _connect_signals(self):
        """UI 위젯들의 시그널을 해당 슬롯(이벤트 핸들러)에 연결합니다."""
        # product_tree_widget (ProjectTreeWidget)에서 현재 선택된 아이템이 변경될 때
        self.product_tree_widget.currentItemChanged.connect(self._on_tree_selection_changed) 

        # representative_panel (RepresentativePanel) 내부에서 탭이 변경될 때
        self.representative_panel.tab_changed.connect(self._on_representative_tab_changed)  

        # representative_panel (RepresentativePanel) 내부에서 이미지가 선택될 때
        self.representative_panel.image_selected.connect(self._on_image_clicked)
        
        # workspace_panel (WorkspacePanel)에서 대표 이미지 선택 시
        self.workspace_panel.image_selected_for_representative.connect(self._on_workspace_image_clicked)
    
    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트를 키보드 핸들러에 위임합니다."""
        if hasattr(self, 'keyboard_handler') and self.keyboard_handler.handle_key_press_event(event):
            return
        
        # 처리되지 않은 키는 기본 처리로 넘김
        super().keyPressEvent(event)

    # ===================================================================
    # 2. 상태 저장/로드 메서드
    # ===================================================================
    
    def _get_selections_file_path(self, product_path):
        """제품별 대표 이미지 선택 상태를 저장할 파일 경로를 반환합니다."""
        return os.path.join(product_path, "representative_selections.json")
    
    def _save_representative_selections(self):
        """현재 모든 제품의 대표 이미지 선택 상태를 저장합니다."""
        try:
            for product_path, selections in self.representative_selections.items():
                if not product_path or not os.path.isdir(product_path):
                    continue
                    
                selections_file = self._get_selections_file_path(product_path)
                with open(selections_file, 'w', encoding='utf-8') as f:
                    json.dump(selections, f, indent=2, ensure_ascii=False)
            
            # 진행상황 업데이트
            self._update_status_bar()
        except Exception as e:
            pass  # 조용히 실패
    
    def _load_representative_selections(self):
        """저장된 대표 이미지 선택 상태를 불러옵니다."""
        try:
            if not self.current_product_path:
                return
                
            selections_file = self._get_selections_file_path(self.current_product_path)
            if not os.path.exists(selections_file):
                return
                
            with open(selections_file, 'r', encoding='utf-8') as f:
                selections = json.load(f)
                self.representative_selections[self.current_product_path] = selections
                
            # UI에 선택 상태 반영
            self._apply_saved_selections()
            # 진행상황 업데이트
            self._update_status_bar()
        except Exception as e:
            pass  # 조용히 실패
    
    def _apply_saved_selections(self):
        """불러온 선택 상태를 UI에 반영합니다."""
        if not self.current_product_path or self.current_product_path not in self.representative_selections:
            return
            
        selections = self.representative_selections[self.current_product_path]
        
        # 현재 대표 패널의 모든 이미지 라벨들을 찾아 선택 상태 적용
        self._apply_selections_to_panel(selections)
    
    def _apply_selections_to_panel(self, selections):
        """대표 패널의 이미지들에 선택 상태를 적용합니다."""
        try:
            # RepresentativePanel의 모든 탭을 순회
            for tab_index in range(self.representative_panel.tabs.count()):
                tab_widget = self.representative_panel.tabs.widget(tab_index)
                if not tab_widget:
                    continue
                    
                # 각 탭의 스플리터 내부 그룹박스들을 순회
                for group_index in range(tab_widget.count()):
                    group_widget = tab_widget.widget(group_index)
                    if not group_widget:
                        continue
                        
                    # 그룹명 추출 (model 또는 product_only)
                    group_title = group_widget.title().lower()
                    if "model" in group_title:
                        group_name = "model"
                    elif "단독" in group_title or "product_only" in group_title:
                        group_name = "product_only"
                    else:
                        continue
                        
                    if group_name not in selections:
                        continue
                        
                    selected_path = selections[group_name]
                    
                    # 그룹 내의 모든 ImageLabel 찾기
                    self._find_and_select_image_label(group_widget, selected_path, group_name)
                        
        except Exception as e:
            pass  # 조용히 실패
    
    def _find_and_select_image_label(self, widget, target_path, group_name):
        """위젯 트리를 순회하며 해당 경로의 이미지 라벨을 찾아 선택 상태로 만듭니다."""
        from widgets.image_label import ImageLabel
        
        # 위젯의 모든 자식을 재귀적으로 순회
        for child in widget.findChildren(ImageLabel):
            if hasattr(child, 'path') and child.path == target_path:
                child.select()
                # MainWindow의 선택 상태도 업데이트
                if group_name == "model":
                    if self.selected_model_image and self.selected_model_image != child:
                        self.selected_model_image.deselect()
                    self.selected_model_image = child
                elif group_name == "product_only":
                    if self.selected_product_only_image and self.selected_product_only_image != child:
                        self.selected_product_only_image.deselect()
                    self.selected_product_only_image = child
                
                # 양쪽 패널에서 동기화 (무한 루프 방지를 위해 직접 호출)
                self.workspace_panel.update_representative_selection(group_name, target_path)
                break

    def _save_current_product_selections(self):
        """현재 제품의 대표 이미지 선택 상태만 저장합니다."""
        if not self.current_product_path or self.current_product_path not in self.representative_selections:
            return
            
        try:
            selections_file = self._get_selections_file_path(self.current_product_path)
            selections = self.representative_selections[self.current_product_path]
            
            with open(selections_file, 'w', encoding='utf-8') as f:
                json.dump(selections, f, indent=2, ensure_ascii=False)
            
            # 진행상황 업데이트를 위해 상태바 갱신 (약간의 지연 후)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self._update_status_bar)
                
        except Exception as e:
            pass  # 조용히 실패

    # ===================================================================
    # 4. UI 업데이트 로직
    # ===================================================================

    def _update_right_panel(self, current_tree_item, item_path):
        """
        트리 선택에 따라 우측 대표 이미지 패널을 업데이트하거나,
        필요한 경우 탭을 동기화합니다.
        """
        product_path = self._find_product_root(current_tree_item, item_path)

        if not product_path:
            if self.current_product_path:
                self.representative_panel.clear()
                self.current_product_path = None
            return

        # 다른 제품을 선택한 경우, 대표 이미지 UI를 새로 구성
        if product_path and product_path != self.current_product_path:
            self.current_product_path = product_path
            self.representative_panel.setup_ui(product_path)
            
            # 저장된 선택 상태 자동 로드
            self._load_current_product_selections()
        
        # 현재 선택된 폴더에 맞춰 대표 이미지 탭을 동기화
        if self.current_product_path:
            self.representative_panel.sync_tab(item_path, self.current_product_path)
        
        # 상태바 업데이트
        self._update_status_bar()
    
    def _load_current_product_selections(self):
        """현재 제품의 저장된 대표 이미지 선택 상태를 자동으로 불러옵니다."""
        if not self.current_product_path:
            return
            
        try:
            selections_file = self._get_selections_file_path(self.current_product_path)
            if os.path.exists(selections_file):
                with open(selections_file, 'r', encoding='utf-8') as f:
                    selections = json.load(f)
                    self.representative_selections[self.current_product_path] = selections
                    
                # UI에 선택 상태 반영 (약간의 지연 후 실행)
                from PySide6.QtCore import QTimer
                QTimer.singleShot(200, self._apply_saved_selections)
                QTimer.singleShot(400, self._update_status_bar)  # 선택 상태 적용 후 상태바 업데이트
                
        except Exception as e:
            pass  # 조용히 실패

    def _find_product_root(self, tree_item, item_path):
        """
        선택된 트리 아이템의 최상위 아이템 경로를 제품 루트로 반환합니다.
        """
        product_item = tree_item
        while product_item.parent():
            product_item = product_item.parent()
        
        product_path = product_item.data(0, Qt.UserRole)
        # 만약 찾은 경로에 model/product_only가 없다면, 현재 아이템 경로를 사용
        try:
            subdirs = [d for d in os.listdir(product_path) if os.path.isdir(os.path.join(product_path, d))]
            if not any(d in ['model', 'product_only'] for d in subdirs):
                 # 하위 폴더도 확인
                 if not any( os.path.isdir(os.path.join(product_path, sd, 'model')) or os.path.isdir(os.path.join(product_path, sd, 'product_only')) for sd in subdirs):
                     # 그래도 없으면 현재 아이템 경로가 루트일 수 있음
                     current_subdirs = [d for d in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, d))]
                     if any(d in ['model', 'product_only'] for d in current_subdirs):
                        return item_path

        except (OSError, TypeError):
            pass

        return product_path

    def _clear_all_panels(self):
        """모든 동적 UI 요소들을 초기화합니다."""
        self.product_tree_widget.clear()
        self.representative_panel.clear()
        self.workspace_panel.clear_content()
        self.current_product_path = None
        # 선택 상태도 초기화
        self.selected_model_image = None
        self.selected_product_only_image = None
        self.representative_selections.clear()
        # 전체 제품 목록도 초기화
        self.all_products.clear()
        self.project_root_path = None
        # 상태바 업데이트
        self._update_status_bar()

    # ===================================================================
    # 3. 이벤트 핸들러 (슬롯)
    # ===================================================================
    @Slot()
    def _on_folder_open_clicked(self):
        """'폴더 열기' 메뉴가 클릭되었을 때 실행되는 슬롯."""
        # 사용자에게 기존 디렉터리를 선택할 수 있는 대화 상자를 띄웁니다. 선택된 폴더 경로는 folder_path 변수에 저장
        folder_path = QFileDialog.getExistingDirectory(self, "최상위 작업폴더 선택")
        if folder_path: # 사용자가 폴더를 선택하고 "확인"을 클릭하여 유효한 경로를 반환했을 경우
            self._clear_all_panels()
            self.project_root_path = folder_path
            self._scan_all_products(folder_path)
            self._load_all_representative_selections()
            self.product_tree_widget.load_project(folder_path)
            self._update_status_bar()
    
    @Slot()
    def _on_tree_selection_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """좌측 트리에서 아이템 선택이 변경될 때 실행되는 메인 슬롯."""
        if not current:
            # self._clear_all_panels() # 선택이 없을 때 클리어하면 불편할 수 있음
            return
        '''
        현재 선택된 트리 아이템에서 Qt.UserRole에 저장된 데이터를 가져옵니다. 
        '''
        # 0번째 열의 Qt.UserRole 주소에 저장된 데이터를 가져옵니다.(여기선 선택된 item의 pull path)
        item_path = current.data(0, Qt.UserRole)
        if not item_path or not os.path.isdir(item_path):
            return

        # 중앙 패널 업데이트 (눌린 item의 경로에 맞춰 업데이트)
        self.workspace_panel.update_content(item_path)

        # 우측 대표 이미지 패널 업데이트
        self._update_right_panel(current, item_path)
        
    @Slot()
    def _on_representative_tab_changed(self, index: int):
        """우측 대표 이미지 탭이 변경될 때 선택 상태를 초기화하는 슬롯."""
        self.selected_model_image = None
        self.selected_product_only_image = None
        self._update_status_bar()

    @Slot()
    def _on_image_clicked(self, clicked_label: 'ImageLabel', group: str):
        """우측 대표 이미지 패널(RepresentativePanel) 내부의 이미지 라벨이 클릭되었을 때 선택 상태를 관리하는 슬롯."""
        self._handle_image_selection(clicked_label, group, from_representative_panel=True)
    
    @Slot()
    def _on_workspace_image_clicked(self, clicked_label: 'ImageLabel', group: str):
        """중앙 작업 패널(WorkspacePanel)에서 이미지가 클릭되었을 때 대표 이미지로 선정하는 슬롯."""
        self._handle_image_selection(clicked_label, group, from_representative_panel=False)
    
    def _handle_image_selection(self, clicked_label: 'ImageLabel', group: str, from_representative_panel: bool):
        """이미지 선택을 처리하고 양쪽 패널의 선택 상태를 동기화합니다."""
        target_selection_attr = f"selected_{group}_image"
        
        current_selection = getattr(self, target_selection_attr)
        
        # 기존 선택 해제
        if current_selection and current_selection is not clicked_label:
            current_selection.deselect()

        if clicked_label.is_selected:
            # 이미 선택된 상태라면 선택 해제
            clicked_label.deselect()
            setattr(self, target_selection_attr, None)
            # 선택 해제 시 저장된 상태에서도 제거
            self._update_representative_selection(group, None)
            # 양쪽 패널에서 선택 해제
            self._sync_panel_selection(group, None)
        else:
            # 새로 선택
            clicked_label.select()
            setattr(self, target_selection_attr, clicked_label)
            # 선택 시 상태 저장
            self._update_representative_selection(group, clicked_label.path)
            # 양쪽 패널에서 선택 상태 동기화
            self._sync_panel_selection(group, clicked_label.path)
        
        # 상태바 업데이트
        self._update_status_bar()
    
    def _sync_panel_selection(self, group: str, selected_image_path: str):
        """양쪽 패널(중앙/우측)에서 동일한 이미지의 선택 상태를 동기화합니다."""
        # 중앙 패널 동기화
        self.workspace_panel.update_representative_selection(group, selected_image_path)
        
        # 우측 패널 동기화 - RepresentativePanel의 모든 이미지 라벨 찾기
        self._sync_representative_panel_selection(group, selected_image_path)
    
    def _sync_representative_panel_selection(self, group: str, selected_image_path: str):
        """우측 대표 패널의 이미지들에 선택 상태를 동기화합니다."""
        try:
            from widgets.image_label import ImageLabel
            
            # RepresentativePanel의 모든 탭을 순회
            for tab_index in range(self.representative_panel.tabs.count()):
                tab_widget = self.representative_panel.tabs.widget(tab_index)
                if not tab_widget:
                    continue
                    
                # 각 탭의 스플리터 내부 그룹박스들을 순회
                for group_index in range(tab_widget.count()):
                    group_widget = tab_widget.widget(group_index)
                    if not group_widget:
                        continue
                        
                    # 그룹명 추출 (model 또는 product_only)
                    group_title = group_widget.title().lower()
                    if "model" in group_title and group == "model":
                        target_group = True
                    elif ("단독" in group_title or "product_only" in group_title) and group == "product_only":
                        target_group = True
                    else:
                        target_group = False
                        
                    if not target_group:
                        continue
                        
                    # 그룹 내의 모든 ImageLabel 찾기 및 선택 상태 업데이트
                    for child in group_widget.findChildren(ImageLabel):
                        if hasattr(child, 'path'):
                            if selected_image_path and child.path == selected_image_path:
                                # 대표로 선택된 이미지
                                if not child.is_selected:
                                    child.select()
                            else:
                                # 선택 해제
                                if child.is_selected:
                                    child.deselect()
                        
        except Exception as e:
            pass  # 조용히 실패
    
    def _update_representative_selection(self, group: str, image_path: str):
        """대표 이미지 선택 상태를 업데이트하고 자동 저장합니다."""
        if not self.current_product_path:
            return
            
        if self.current_product_path not in self.representative_selections:
            self.representative_selections[self.current_product_path] = {}
            
        if image_path:
            self.representative_selections[self.current_product_path][group] = image_path
        else:
            # 선택 해제 시 해당 그룹 제거
            if group in self.representative_selections[self.current_product_path]:
                del self.representative_selections[self.current_product_path][group]
        
        # 자동 저장
        self._save_current_product_selections()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())