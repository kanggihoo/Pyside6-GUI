from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeyEvent, QShortcut, QKeySequence
from PySide6.QtCore import Qt


class KeyboardNavigationHandler:
    """키보드 네비게이션을 처리하는 클래스"""
    
    def __init__(self, main_window):
        """
        Args:
            main_window: MainWindow 인스턴스
        """
        self.main_window = main_window
        self.shortcuts = []
        self._setup_global_shortcuts()
    
    def _setup_global_shortcuts(self):
        """전체 애플리케이션에서 작동하는 키보드 단축키를 설정합니다."""
        # Mac 환경을 고려한 키 조합 - J, K 키 사용 (vim 스타일)
        shortcut_prev = QShortcut(QKeySequence(Qt.Key_J), self.main_window)
        shortcut_prev.activated.connect(lambda: self._navigate_to_product(-1))
        
        shortcut_next = QShortcut(QKeySequence(Qt.Key_K), self.main_window)
        shortcut_next.activated.connect(lambda: self._navigate_to_product(1))
        
        # Cmd + J, K (Mac의 Cmd 키)
        shortcut_cmd_prev = QShortcut(QKeySequence(Qt.META | Qt.Key_J), self.main_window)
        shortcut_cmd_prev.activated.connect(lambda: self._navigate_to_product(-1))
        
        shortcut_cmd_next = QShortcut(QKeySequence(Qt.META | Qt.Key_K), self.main_window)
        shortcut_cmd_next.activated.connect(lambda: self._navigate_to_product(1))
        
        # Ctrl + J, K 키: 대안 단축키
        shortcut_ctrl_prev = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_J), self.main_window)
        shortcut_ctrl_prev.activated.connect(lambda: self._navigate_to_product(-1))
        
        shortcut_ctrl_next = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_K), self.main_window)
        shortcut_ctrl_next.activated.connect(lambda: self._navigate_to_product(1))
        
        # 좌/우 방향키: 추가 대안 단축키
        shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self.main_window)
        shortcut_left.activated.connect(lambda: self._navigate_to_product(-1))
        
        shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self.main_window)
        shortcut_right.activated.connect(lambda: self._navigate_to_product(1))
        
        # Page Up/Down 키: 추가 제품 이동 단축키
        shortcut_page_up = QShortcut(QKeySequence(Qt.Key_PageUp), self.main_window)
        shortcut_page_up.activated.connect(lambda: self._navigate_to_product(-1))
        
        shortcut_page_down = QShortcut(QKeySequence(Qt.Key_PageDown), self.main_window)
        shortcut_page_down.activated.connect(lambda: self._navigate_to_product(1))
        
        # 모든 단축키를 저장하고 애플리케이션 전체에서 작동하도록 설정
        self.shortcuts = [
            shortcut_prev, shortcut_next,
            shortcut_cmd_prev, shortcut_cmd_next,
            shortcut_ctrl_prev, shortcut_ctrl_next,
            shortcut_left, shortcut_right,
            shortcut_page_up, shortcut_page_down
        ]
        
        for shortcut in self.shortcuts:
            shortcut.setContext(Qt.ApplicationShortcut)  # 앱 전역에서 작동
    
    def handle_key_press_event(self, event: QKeyEvent):
        """키보드 이벤트를 직접 처리합니다."""
        key = event.key()
        text = event.text().lower()  # 입력된 텍스트를 소문자로 변환
        
        # j 또는 k 키 처리 (한/영키 상태와 무관하게)
        if text == 'j' or key == Qt.Key_J:
            self._navigate_to_product(-1)
            event.accept()
            return True
        elif text == 'k' or key == Qt.Key_K:
            self._navigate_to_product(1)
            event.accept()
            return True
        
        return False  # 처리되지 않은 키
    
    def _navigate_to_product(self, direction: int):
        """제품 간 이동 (direction: -1=이전, 1=다음)"""
        try:
            # 현재 선택된 아이템 가져오기
            current_item = self.main_window.product_tree_widget.currentItem()
            
            if not current_item:
                # 선택된 아이템이 없으면 첫 번째 제품으로 이동
                first_product = self._get_first_product_item()
                if first_product:
                    self.main_window.product_tree_widget.setCurrentItem(first_product)
                return
            
            # 제품 레벨 아이템들을 모두 찾기
            product_items = self._get_all_product_items()
            if not product_items:
                return
            
            # 현재 제품 아이템 찾기
            current_product_item = self._find_parent_product_item(current_item)
            if not current_product_item:
                return
            
            # 현재 제품의 인덱스 찾기
            try:
                current_index = product_items.index(current_product_item)
            except ValueError:
                return
            
            # 다음/이전 인덱스 계산 (순환하도록)
            new_index = (current_index + direction) % len(product_items)
            next_product_item = product_items[new_index]
            
            # 새로운 제품으로 이동
            self.main_window.product_tree_widget.setCurrentItem(next_product_item)
            self.main_window.product_tree_widget.expandItem(next_product_item)  # 펼치기
            
        except Exception as e:
            pass  # 조용히 실패
    
    def _get_all_product_items(self):
        """모든 제품 레벨 아이템들을 순서대로 반환합니다."""
        product_items = []
        
        # 현재 선택된 아이템 가져오기
        current_item = self.main_window.product_tree_widget.currentItem()
        if not current_item:
            return product_items
        
        # 현재 아이템이 제품 레벨인지 확인하고, 그 부모를 찾음
        current_path = current_item.data(0, Qt.UserRole)
        
        # 현재 아이템이 제품인지 확인
        if current_path and self._is_actual_product_folder(current_path):
            # 현재 아이템이 제품이면, 그 부모의 모든 자식들을 찾음
            parent_item = current_item.parent()
            
            if parent_item:
                # 부모가 있는 경우 - 부모의 자식들을 모두 확인
                container_item = parent_item
            else:
                # 부모가 없는 경우 - 최상위 레벨에서 형제들을 찾음
                for i in range(self.main_window.product_tree_widget.topLevelItemCount()):
                    top_item = self.main_window.product_tree_widget.topLevelItem(i)
                    if top_item:
                        item_path = top_item.data(0, Qt.UserRole)
                        if item_path and self._is_actual_product_folder(item_path):
                            product_items.append(top_item)
                return product_items
        else:
            # 현재 아이템이 제품이 아닌 경우, 상위로 올라가며 제품 찾기
            temp_item = current_item
            while temp_item:
                temp_path = temp_item.data(0, Qt.UserRole)
                if temp_path and self._is_actual_product_folder(temp_path):
                    # 이 제품의 부모를 찾아서 형제들을 검색
                    parent_item = temp_item.parent()
                    if parent_item:
                        container_item = parent_item
                        break
                    else:
                        # 최상위 레벨에서 검색
                        for i in range(self.main_window.product_tree_widget.topLevelItemCount()):
                            top_item = self.main_window.product_tree_widget.topLevelItem(i)
                            if top_item:
                                item_path = top_item.data(0, Qt.UserRole)
                                if item_path and self._is_actual_product_folder(item_path):
                                    product_items.append(top_item)
                        return product_items
                temp_item = temp_item.parent()
            
            if not temp_item:
                return product_items
            container_item = parent_item
        
        # container_item의 자식들 중에서 제품들을 찾기
        for i in range(container_item.childCount()):
            child_item = container_item.child(i)
            if child_item:
                item_path = child_item.data(0, Qt.UserRole)
                if item_path and self._is_actual_product_folder(item_path):
                    product_items.append(child_item)
        
        return product_items
    
    def _is_actual_product_folder(self, folder_path):
        """경로가 실제 제품 폴더인지 확인합니다 (스캔된 제품 목록과 비교)."""
        return folder_path in self.main_window.all_products
    
    def _find_parent_product_item(self, item):
        """주어진 아이템의 상위 제품 아이템을 찾습니다."""
        current = item
        
        while current:
            # 현재 아이템이 제품 아이템인지 확인
            item_path = current.data(0, Qt.UserRole)
            if item_path and self._is_actual_product_folder(item_path):
                return current
            
            # 상위 아이템으로 이동
            current = current.parent()
        
        return None
    
    def _get_first_product_item(self):
        """첫 번째 제품 아이템을 반환합니다."""
        product_items = self._get_all_product_items()
        return product_items[0] if product_items else None 