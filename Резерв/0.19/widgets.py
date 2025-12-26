import os
import logging 
import re 
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
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QRect, QUrl, QPoint, QCoreApplication
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QTextCursor

logger = logging.getLogger(__name__)

# --- КОНСТАНТЫ (Для примера, если они не импортируются из config) ---
ITEM_WIDTH = 180
ITEM_HEIGHT = 220
BORDER_RADIUS = 10 

# ----------------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ----------------------------------------------------------------------

def extract_short_info(html_content):
    """
    Извлекает основные детали (год, разработчик и т.д.) из HTML для тултипа.
    """
    
    # ИСПРАВЛЕНИЕ: Теперь ищем все 5 полей, используя <b> тег (из HTML-шаблона) и правильные названия полей
    dev_match = re.search(r'<b>Разработчик:<\/b>\s*([^<]+)', html_content)
    year_match = re.search(r'<b>Дата выхода:<\/b>.*?(\d{4})', html_content) 
    lang_match = re.search(r'<b>Язык игры:<\/b>\s*([^<]+)', html_content)
    players_match = re.search(r'<b>Количество игроков:<\/b>\s*([^<]+)', html_content)
    details_match = re.search(r'<b>Доп\. детали:<\/b>\s*([^<]+)', html_content) 
    
    dev = dev_match.group(1).strip() if dev_match else '???'
    year = year_match.group(1).strip() if year_match else '???'
    lang = lang_match.group(1).strip() if lang_match else '???'
    players = players_match.group(1).strip() if players_match else '???'
    
    # Извлекаем только Жанр из Доп. деталей: "Жанр: XXXXX; YYYYY" -> XXXXX
    details_raw = details_match.group(1).strip() if details_match else '???'
    # Ищем Жанр, который находится в начале Доп. деталей
    genre_match = re.search(r'Жанр:\s*([^;]+)', details_raw)
    genre = genre_match.group(1).strip() if genre_match else details_raw.split(';')[0].strip()
    
    # Формируем итоговую строку для краткого описания
    info_parts = [
        f"Разработчик: {dev}",
        f"Год: {year}",
        f"Язык: {lang}",
        f"Игроки: {players}",
        f"Жанр: {genre}"
    ]
    
    return " | ".join(info_parts)


# ----------------------------------------------------------------------
# КЛАСС ЭЛЕМЕНТА ИГРЫ (GameItem)
# ----------------------------------------------------------------------
class GameItem(QFrame):
    """Виджет для отображения одной игры в сетке."""
    
    # Сигнал для запуска игры
    game_launched = pyqtSignal(str) 
    # Сигнал для запроса полного описания (правый клик)
    show_description_requested = pyqtSignal(str) 

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
        
        image_height = int(item_height * 0.8) 
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
        Устанавливает загруженное изображение на метку обложки.
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
        """Создает заглушку, пока идет загрузка изображения."""
        
        size = self.image_label.size()
        pixmap = QPixmap(size)
        pixmap.fill(QColor(30, 30, 30)) 
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QColor("#DCDCDC"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "Loading...")
        painter.end()
        
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def mouseDoubleClickEvent(self, event):
        """Левый двойной клик: запуск игры через сигнал."""
        if event.button() == Qt.LeftButton:
            self.game_launched.emit(self.rom_path) 
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
            
    def mouseReleaseEvent(self, event):
        """Правый клик: запрос описания."""
        if event.button() == Qt.RightButton:
            self.show_description_requested.emit(self.game_folder) 
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ----------------------------------------------------------------------
# КЛАСС ОКНА ОПИСАНИЯ (DescriptionWindow) 
# ----------------------------------------------------------------------
class DescriptionWindow(QDialog):
    """Модальное окно для отображения полного описания игры (HTML) и скриншотов."""
    
    drag_offset = QPoint()
    
    def __init__(self, game_folder, description, screenshots, parent=None):
        super().__init__(parent)
        
        self.game_folder = game_folder
        self.screenshots = screenshots
        self.game_title = os.path.basename(game_folder)
        
        self.setWindowTitle(f"Описание: {self.game_title}")
        self.setMinimumSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose) 
        
        # 1. Атрибут для включения прозрачного фона у самого окна (делает углы прозрачными)
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.Dialog) 
        
        # Layout for QDialog (holds only the Inner Frame)
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 2. Создаем Внутренний Фрейм, который будет ОПАЧЕН и ОКРУГЛЕН
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("InnerDescriptionFrame")
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        
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
        
        inner_layout.addWidget(self.title_bar) # <-- ДОБАВЛЕНО В inner_layout
        # --- КОНЕЦ КАСТОМНОГО ЗАГОЛОВКА ---

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setObjectName("DescTextBrowser")
        
        self.load_styled_description() 
        
        inner_layout.addWidget(self.browser) # <-- ДОБАВЛЕНО В inner_layout
        
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
        
        inner_layout.addWidget(bottom_widget) # <-- ДОБАВЛЕНО В inner_layout
        
        # 3. Добавляем внутренний фрейм в основной макет QDialog
        main_layout.addWidget(self.inner_frame)
        
        # --- СТИЛИЗАЦИЯ ---
        self.setStyleSheet("""
            QDialog { 
                background-color: transparent; /* Окно-холст полностью прозрачный */
                border: none;
            }
            
            QFrame#InnerDescriptionFrame {
                background-color: #2a2a2a; /* Опачен, это наш видимый фон */
                border: none; /* УДАЛЕНИЕ НЕОНОВОЙ РАМКИ */
                border-radius: 15px; /* Округление применяется здесь */
                margin: 5px; /* Отступ для визуализации прозрачных углов */
            }
            
            /* Стили для кастомного заголовка */
            QWidget#DescTitleBar {
                background-color: #1a1a1a; 
                border-top-left-radius: 15px; /* Новый радиус */
                border-top-right-radius: 15px; /* Новый радиус */
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
                border-bottom-left-radius: 15px; /* Новый радиус */
                border-bottom-right-radius: 15px; /* Новый радиус */
            }
            
            /* Стили браузера */
            QTextBrowser#DescTextBrowser { 
                border: none; 
                background-color: #2a2a2a; /* Однотонный фон (должен совпадать с InnerFrame) */
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
            # Проверяем, находится ли клик в области заголовка (DescTitleBar)
            # Чтобы перетаскивание работало, клик должен быть внутри inner_frame, но в области title_bar
            if self.inner_frame.geometry().contains(event.pos()) and event.pos().y() < self.title_bar.height():
                self.drag_offset = event.globalPos() - self.pos()
                event.accept()
            else:
                super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self.inner_frame.geometry().contains(event.pos()) and event.pos().y() < self.title_bar.height():
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
        """
        
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

        # 1. Генерация тегов <img> для галереи 
        image_tags = []
        for path in self.screenshots:
            
            absolute_path = os.path.normpath(os.path.join(self.game_folder, path))
            file_url = QUrl.fromLocalFile(absolute_path).toString()
            
            tag = f'<img src="{file_url}" alt="{path}" style="max-height: 120px; max-width: 100%; border: 1px solid #444; margin-right: 5px; border-radius: 5px; display: inline-block;">'
            image_tags.append(tag)
        
        # ИСПРАВЛЕНИЕ: Обнуляем padding и margin, которые добавляют отступ.
        gallery_html = f'<div style="white-space: nowrap; overflow-x: auto; padding: 0; margin: 0;">{"".join(image_tags)}</div>'
        
        # 2. Вставка тегов в HTML
        if '<div class="image-gallery"></div>' in html_content:
             html_content = html_content.replace(
                 '<div class="image-gallery"></div>', 
                 gallery_html
             )
        
        # 3. Установка базового URL-адреса для QTextBrowser
        # Указываем на корень папки игры, чтобы браузер мог найти связанные ресурсы (images, css и т.д.)
        base_url = QUrl.fromLocalFile(self.game_folder + os.sep)
        
        # Теперь устанавливаем base_url на документ
        self.browser.document().setBaseUrl(base_url) 
        
        # 4. Финальная загрузка
        self.browser.setHtml(html_content) 
        
        # 5. Прокручиваем документ в начало
        cursor = self.browser.textCursor()
        cursor.setPosition(0)
        self.browser.setTextCursor(cursor)