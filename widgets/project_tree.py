import os
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt


class ProjectTreeWidget(QTreeWidget):
    """
    주요 기능
        폴더 구조 탐색: 지정된 루트 경로의 모든 하위 폴더를 재귀적으로 탐색
        트리 형태 표시: 폴더들을 계층적 트리 구조로 시각화
        데이터 저장: 각 트리 아이템에 해당 폴더의 전체 경로를 Qt.UserRole에 저장
    핵심 구성요소
        QTreeWidget을 상속받아 폴더 탐색 기능 구현
        load_project(): 새로운 프로젝트 폴더 로드
        _populate_tree_recursive(): 재귀적으로 폴더 구조 생성
    사용처
    메인 애플리케이션에서 좌측 패널의 파일 탐색기 역할을 하며, 사용자가 프로젝트 내 특정 폴더를 선택할 수 있는 인터페이스를 제공합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Project Structure"])

    '''
    load_project(): 사용자가 메뉴에서 "폴더 열기"를 선택했을 때 직접 호출되는 일반 메서드
    '''
    def load_project(self, root_path):
        """
        지정된 경로의 폴더 구조를 읽어와 트리 위젯을 채웁니다.
        """
        self.clear()
        try:
            self.setHeaderLabel(os.path.basename(root_path))
            self._populate_tree_recursive(self, root_path)
        except Exception as e:
            print(f"Error loading directory tree: {e}")

    '''
    load_project() 내부에서 재귀적으로 호출되는 헬퍼 메서드
    '''
    def _populate_tree_recursive(self, parent_item, path):
        """
        재귀적으로 폴더를 탐색하며 트리 위젯에 항목을 추가합니다.
        """
        for item_name in sorted(os.listdir(path)):
            full_path = os.path.join(path, item_name)
            if os.path.isdir(full_path):
                item = QTreeWidgetItem(parent_item, [item_name])
                item.setData(0, Qt.UserRole, full_path)
                self._populate_tree_recursive(item, full_path) 