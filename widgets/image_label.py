from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QPainter, QPen, QFont
from PySide6.QtCore import Qt, Signal


class ImageLabel(QLabel):
    """
    이 ImageLabel 모듈은 PySide6 기반의 커스텀 이미지 라벨 위젯입니다.
    주요 기능:
        이미지 표시 및 클릭 이벤트 처리
        마우스 호버 시 시각적 피드백 (파란색 테두리)
        선택 상태 관리 (더 굵은 빨간색 테두리 + 선택적 "대표" 라벨)
        클릭 시 자신의 인스턴스를 시그널로 방출
    핵심 구성요소:
        QLabel을 상속받아 이미지 표시 기능 확장
        clicked 시그널: 클릭 시 자신의 인스턴스 전달
        3가지 테두리 스타일: 기본(회색), 호버(연한 파란색), 선택(진한 빨간색)
        select()/deselect() 메서드로 선택 상태 제어
        선택적 "대표" 라벨 오버레이 표시 (show_label 옵션)
    사용처:
    ImageGridWidget에서 썸네일 이미지들을 표시하는 데 사용되며, 사용자가 이미지를 선택하고 관리할 수 있는 인터페이스를 제공합니다.
    """
    clicked = Signal(object)

    def __init__(self, pixmap, path, parent=None, show_star_label=False):
        """
        ImageLabel의 생성자입니다.
        :param pixmap: 표시할 이미지 (QPixmap 객체)
        :param path: 이미지의 파일 경로
        :param parent: 부모 위젯
        :param show_star_label: 선택 시 "★ 대표" 라벨을 표시할지 여부 (기본: False)
        """
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.path = path
        self.is_selected = False
        self.show_star_label = show_star_label

        self.BORDER_DEFAULT = "2px solid #ddd"
        self.BORDER_HOVER = "3px solid #5DADE2"
        self.BORDER_SELECTED = "4px solid #E74C3C"  # 더 눈에 띄는 빨간색 테두리

        self.setPixmap(pixmap)
        self.setStyleSheet(f"border: {self.BORDER_DEFAULT}; margin: 2px; border-radius: 4px;")
        self.setAlignment(Qt.AlignCenter)

    def _update_pixmap(self):
        """현재 상태에 맞춰 픽스맵을 업데이트합니다."""
        if self.is_selected and self.show_star_label:
            # 선택된 상태 + 라벨 표시: "대표" 라벨 오버레이 추가
            pixmap_with_overlay = self.original_pixmap.copy()
            painter = QPainter(pixmap_with_overlay)
            
            # 반투명 배경
            painter.fillRect(0, 0, pixmap_with_overlay.width(), 25, Qt.red)
            
            # "대표" 텍스트
            painter.setPen(QPen(Qt.white))
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(5, 18, "★ 대표")
            
            painter.end()
            self.setPixmap(pixmap_with_overlay)
        else:
            # 기본 상태 또는 라벨 없는 선택 상태: 원본 이미지
            self.setPixmap(self.original_pixmap)

    '''
    Qt의 이벤트 핸들러(Event Handler) 메서드들입니다:
    enterEvent, leaveEvent, mousePressEvent는 Qt 위젯의 기본 이벤트 핸들러로, 마우스나 키보드 같은 사용자 입력 이벤트를 직접 처리
    '''
    # ===================================================================
    # 1. 이벤트 핸들러 메서드들
    # ===================================================================

    def enterEvent(self, event):
        """마우스 커서가 위젯 위에 올라왔을 때 호버 효과를 적용합니다."""
        if not self.is_selected:
            self.setStyleSheet(f"border: {self.BORDER_HOVER}; margin: 2px; border-radius: 4px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스 커서가 위젯 밖으로 나갔을 때 호버 효과를 제거합니다."""
        if not self.is_selected:
            self.setStyleSheet(f"border: {self.BORDER_DEFAULT}; margin: 2px; border-radius: 4px;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """위젯이 마우스로 클릭되면 'clicked' 시그널을 방출합니다."""
        self.clicked.emit(self)
        super().mousePressEvent(event)

    def select(self):
        """이미지를 '선택됨' 상태로 만들고, 시각적 효과를 업데이트합니다."""
        self.is_selected = True
        self.setStyleSheet(f"border: {self.BORDER_SELECTED}; margin: 2px; border-radius: 4px; background-color: #ffe6e6;")
        self._update_pixmap()

    def deselect(self):
        """이미지의 '선택됨' 상태를 해제하고, 기본 스타일로 되돌립니다."""
        self.is_selected = False
        self.setStyleSheet(f"border: {self.BORDER_DEFAULT}; margin: 2px; border-radius: 4px;") 
        self._update_pixmap() 