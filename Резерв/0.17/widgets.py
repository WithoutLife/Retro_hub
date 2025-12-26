import os
import sys
import subprocess
from PyQt5.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QFrame, 
    QTextBrowser, 
    QPushButton,
    QDialog 
)
# ИСПРАВЛЕНИЕ: QTextCursor перемещен из QtCore в QtGui
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QRect, QUrl, QPoint 
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QTextCursor 

# --- КОНСТАНТЫ (Для примера, если они не импортируются из config) ---
ITEM_WIDTH = 180
ITEM_HEIGHT = 220
BORDER_RADIUS = 10 

# ----------------------------------------------------------------------
# КЛАСС ИНДИКАТОРА ГЕЙМПАДОВ (без изменений)
# ----------------------------------------------------------------------
class GamepadIndicator(QWidget):
    """Виджет, отображающий статус до 4-х геймпадов (зеленый/красный круг)."""
    
    def __init__(self, max_pads=4, parent=None):
        super().__init__(parent)
        self.max_pads = max_pads
        self.dots = []
        
        self.setFixedWidth(max_pads * 10 + (max_pads + 1) * 5) 
        
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for i in range(max_pads):
            dot = QLabel()
            dot.setFixedSize(QSize(10, 10))
            self.set_dot_color(dot, QColor(60, 60, 60)) 
            self.dots.append(dot)
            layout.addWidget(dot)

    def set_dot_color(self, label, color):
        """Устанавливает цвет точки с помощью QPixmap, рисуя круг."""
        size = label.size().width()
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size) 
        painter.end()
        
        label.setPixmap(pixmap)

    def update_status(self, connected_count):
        """Обновляет статус точек: до connected_count зеленые, остальные красные."""
        
        count = min(connected_count, self.max_pads) 
        
        for i in range(count):
            self.set_dot_color(self.dots[i], QColor(50, 200, 50)) 
            
        for i in range(count, self.max_pads):
            self.set_dot_color(self.dots[i], QColor(200, 50, 50)) 


# ----------------------------------------------------------------------
# КЛАСС ЭЛЕМЕНТА ИГРЫ (GameItem)
# ----------------------------------------------------------------------
class GameItem(QFrame):
    """Виджет для отображения одной игры в сетке."""
    
    show_description_requested = pyqtSignal(str) 
    game_launched = None 

    def __init__(self, game_folder, rom_path, description, item_width, item_height, screenshots, parent=None):
        
        self.item_width = item_width
        self.item_height = item_height
        
        super().__init__(parent)
        self.setObjectName("GameItem")
        self.setFixedSize(item_width, item_height) 
        self.setCursor(Qt.PointingHandCursor) 
        self.setToolTip(f"**{os.path.basename(game_folder)}**\n\n{description}")
        
        self.game_folder = game_folder
        self.rom_path = rom_path
        self.description = description
        self.screenshots = screenshots 
        
        # Макет
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2) 

        # 1. Обложка/Изображение
        self.image_label = QLabel()
        self.image_label.setObjectName("GameItemImage")
        self.image_label.setAlignment(Qt.AlignCenter)
        
        image_height = int(item_height * 0.75) 
        self.image_label.setFixedSize(QSize(item_width - 10, image_height)) 
        
        self.image_label.setPixmap(self._create_placeholder_pixmap())
        
        # 2. Название игры
        self.title_label = QLabel(os.path.basename(game_folder))
        self.title_label.setObjectName("GameItemTitle")
        self.title_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.title_label.setFont(QFont("Segoe UI", 10))
        self.title_label.setWordWrap(False) 

        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.title_label, stretch=1) 
        
        # Применяем базовые стили (скопировано из вашего старого файла, без изменений)
        self.setStyleSheet(f"""
            QFrame#GameItem {{
                background-color: transparent; 
                border: 2px solid #5a5a5a; 
                border-radius: {BORDER_RADIUS}px;
                padding: 0;
            }}
            QFrame#GameItem:hover {{
                border: 2px solid #FF60FF; 
            }}
            QLabel#GameItemImage {{
                border: none;
            }}
            QLabel#GameItemTitle {{
                color: #dcdcdc;
                font-size: 9pt;
                font-weight: bold;
                white-space: nowrap; 
                margin-top: 5px;
            }}
        """)
        
    def set_cover_pixmap(self, pixmap):
        """
        Устанавливает загруженное изображение на метку обложки, 
        масштабируя его по размеру метки.
        """
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setPixmap(self._create_placeholder_pixmap()) 

    def _create_placeholder_pixmap(self):
        """Создает заглушку, пока идет загрузка изображения. Без рамки."""
        
        size = self.image_label.size()
        pixmap = QPixmap(size)
        pixmap.fill(QColor(30, 30, 30)) 
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "Loading...")
        painter.end()
        
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_description_requested.emit(self.game_folder) 
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.game_launched:
                self.game_launched(self.rom_path) 
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


# ----------------------------------------------------------------------
# КЛАСС ОКНА ОПИСАНИЯ (DescriptionWindow) 
# ----------------------------------------------------------------------
class DescriptionWindow(QDialog):
    """Окно для отображения HTML-описания игры."""
    
    drag_offset = QPoint()
    
    def __init__(self, game_folder, description, screenshots, parent=None):
        super().__init__(parent)
        
        self.game_folder = game_folder
        self.screenshots = screenshots
        self.game_title = os.path.basename(game_folder)
        
        self.setWindowTitle(f"Описание: {self.game_title}")
        self.setMinimumSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose) 
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog) 
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- КАСТОМНЫЙ ЗАГОЛОВОК ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DescTitleBar")
        self.title_bar.setFixedHeight(35) 
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(0)
        
        # Заголовок
        self.title_label = QLabel(f"Описание: {self.game_title}")
        self.title_label.setObjectName("DescTitleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        
        # Кнопка Закрыть
        self.close_button_icon = QPushButton("✕")
        self.close_button_icon.setObjectName("DescCloseButton")
        self.close_button_icon.clicked.connect(self.accept) 
        title_layout.addWidget(self.close_button_icon)
        
        main_layout.addWidget(self.title_bar)
        # --- КОНЕЦ КАСТОМНОГО ЗАГОЛОВКА ---

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setObjectName("DescTextBrowser")
        
        self.load_styled_description() 
        
        main_layout.addWidget(self.browser)
        
        # --- Нижняя панель с кнопкой "Закрыть" ---
        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(40)
        bottom_widget.setObjectName("DescBottomBar")
        
        button_layout = QHBoxLayout(bottom_widget)
        button_layout.setContentsMargins(10, 0, 10, 0)
        button_layout.addStretch(1)
        
        self.close_button = QPushButton("Закрыть")
        self.close_button.setObjectName("DescCloseConfirmButton")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        main_layout.addWidget(bottom_widget)
        
        # --- СТИЛИЗАЦИЯ ---
        self.setStyleSheet("""
            QDialog { 
                background-color: #2a2a2a; 
                border: 1px solid #00FFFF; 
                border-radius: 5px;
            }
            
            /* Стили для кастомного заголовка */
            QWidget#DescTitleBar {
                background-color: #1a1a1a; 
                border-top-left-radius: 5px; 
                border-top-right-radius: 5px;
            }
            
            QLabel#DescTitleLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 10pt;
                line-height: 35px;
            }
            
            /* ИСПРАВЛЕННЫЙ СТИЛЬ КНОПКИ ЗАКРЫТИЯ */
            QPushButton#DescCloseButton {
                background-color: transparent; 
                border: none;
                font-size: 10pt; 
                color: #DCDCDC;
                min-width: 35px; 
                max-width: 35px; 
                padding: 0;
            }
            QPushButton#DescCloseButton:hover {
                background-color: #e81123; 
                color: #FFFFFF; 
            }
            
            QWidget#DescBottomBar {
                background-color: #1a1a1a;
                border-bottom-left-radius: 5px; 
                border-bottom-right-radius: 5px;
            }
            
            /* Стили браузера */
            QTextBrowser#DescTextBrowser { 
                border: none; 
                background-color: #2a2a2a; 
                color: #dcdcdc;
                padding: 10px;
            }
            QTextBrowser h1 {
                color: #FFFFFF;
                font-size: 20pt;
                margin-top: 0;
            }
            QTextBrowser h2 {
                color: #00FFFF; 
                font-size: 16pt;
                border-bottom: 2px solid #00FFFF;
                padding-bottom: 5px;
                margin-top: 15px;
            }
        """)
        
    # --- ЛОГИКА ДЛЯ ПЕРЕТАСКИВАНИЯ ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos().y() < self.title_bar.height():
                self.drag_offset = event.globalPos() - self.pos()
                event.accept()
            else:
                super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if event.pos().y() < self.title_bar.height():
                self.move(event.globalPos() - self.drag_offset)
                event.accept()
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.drag_offset = QPoint()
        super().mouseReleaseEvent(event)
    # --- КОНЕЦ ЛОГИКИ ПЕРЕТАСКИВАНИЯ ---
        
    def load_styled_description(self):
        """
        Загружает HTML-контент, вставляет скриншоты, применяет базовый URL и прокручивает в начало.
        
        ИСПРАВЛЕНИЕ: Путь к файлу описания изменен на index.html.
        """
        
        # ИЗМЕНЕНИЕ ПУТИ ФАЙЛА ОПИСАНИЯ
        desc_path = os.path.join(self.game_folder, "index.html")
        
        if not os.path.exists(desc_path):
            self.browser.setHtml(f"<h1>{self.game_title}</h1><p>HTML-файл описания не найден: {desc_path}</p>")
            return

        try:
            with open(desc_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            self.browser.setHtml(f"<h1>{self.game_title}</h1><p>Ошибка чтения файла: {e}</p>")
            return

        # 1. Генерация тегов <img> для галереи (с абсолютным file:// URI)
        image_tags = []
        for path in self.screenshots:
            
            absolute_path = os.path.join(self.game_folder, path)
            file_url = QUrl.fromLocalFile(absolute_path).toString()
            
            tag = f'<img src="{file_url}" alt="{path}" style="max-height: 120px; max-width: 100%; border: 1px solid #444; margin-right: 5px; border-radius: 5px; display: inline-block;">'
            image_tags.append(tag)
        
        gallery_html = f'<div style="white-space: nowrap; overflow-x: auto; padding: 10px 0; margin-bottom: 20px;">{"".join(image_tags)}</div>'
        
        # 2. Вставка тегов в HTML
        if '<div class="image-gallery"></div>' in html_content:
             html_content = html_content.replace(
                 '<div class="image-gallery"></div>', 
                 gallery_html
             )
        
        # 3. Установка базового URL-адреса 
        game_folder_url_path = self.game_folder.replace(os.sep, '/')
        base_url = QUrl.fromLocalFile(f"{game_folder_url_path}/")
        
        self.browser.document().setBaseUrl(base_url) 
        self.browser.document().setHtml(html_content) 
        
        # 4. Прокручиваем документ в начало
        cursor = self.browser.textCursor()
        cursor.setPosition(0)
        self.browser.setTextCursor(cursor)