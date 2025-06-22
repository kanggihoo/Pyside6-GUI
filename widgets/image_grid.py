import os
from PySide6.QtWidgets import QWidget, QGridLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QSize, Signal

from .image_label import ImageLabel

class ImageGridWidget(QWidget):
    '''
    이 ImageGridWidget 모듈은 이미지들을 그리드 형태로 표시하는 위젯입니다.
    주요 기능:
        이미지 그리드 표시: 폴더 내 이미지들을 그리드로 정렬
        썸네일 생성: 설정 가능한 크기로 이미지 스케일링
        클릭 이벤트 처리: 각 이미지 클릭 시 image_clicked 시그널 방출
        동적 업데이트: populate() 메서드로 새로운 폴더의 이미지들 로드
        시각 효과 옵션: show_star_label로 선택된 이미지의 표시 방식 제어
    핵심 구성요소:
        QGridLayout: 이미지들을 격자 형태로 배치
        ImageLabel: 개별 이미지를 표시하는 커스텀 라벨 (선택/호버 효과 포함)
        labels 리스트: 생성된 모든 이미지 라벨 참조 저장
    '''
    image_clicked = Signal(object) # object is ImageLabel

    def __init__(self, parent=None, thumbnail_size=200, columns=4, show_star_label=False):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.labels = []
        self.thumbnail_size = thumbnail_size
        self.columns = columns
        self.show_star_label = show_star_label
    
    def get_labels(self):
        return self.labels

    def populate(self, folder_path):
        self.clear_grid()
        
        THUMBNAIL_SIZE = self.thumbnail_size
        COLUMNS = self.columns

        if not os.path.isdir(folder_path):
            return

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
        
        image_files = []
        for root, _, files in os.walk(folder_path):
            for file in sorted(files):
                if os.path.splitext(file)[1].lower() in image_extensions:
                    image_files.append(os.path.join(root, file))

        for i, image_path in enumerate(image_files):
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                continue

            label = ImageLabel(
                pixmap.scaled(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE), Qt.KeepAspectRatio, Qt.SmoothTransformation), 
                image_path,
                show_star_label=self.show_star_label
            )
            label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            label.clicked.connect(self.image_clicked.emit)
            
            row, col = divmod(i, COLUMNS)
            self.layout.addWidget(label, row, col)
            self.labels.append(label)

        # 레이아웃 업데이트 강제 실행
        self.layout.update()
        self.updateGeometry()

    def clear_grid(self):
        # Taking widgets from layout is safer
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.labels.clear() 