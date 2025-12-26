# widgets.py (ФИНАЛЬНАЯ ВЕРСИЯ - УСЛОВНЫЙ ВЫВОД ИНФОРМАЦИИ)

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
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QRect, QUrl, QPoint, QCoreApplication, QEvent
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
    Извлекает основные детали (год, разработчик, оценка критиков и т.д.) из HTML для тултипа.
    Поля, которые не удалось спарсить (возвращают '???'), исключаются из итогового описания.
    """
    
    # Полный список мета-полей для использования в lookahead
    META_FIELDS = ["Дата выхода", "Разработчик", "Издатель", "Количество игроков", "Жанр", "Доп. детали", "Год", "Оценка критиков", "Язык игры"]

    # Создаем строку-разделитель, которая ищет любое название поля, завершающееся двоеточием
    field_separators = "|".join([re.escape(f + ":") for f in META_FIELDS])

    def get_value(field_name, content):
        """Вспомогательная функция для надежного извлечения значения поля по его имени."""
        
        # Регулярное выражение для извлечения значения поля
        pattern = re.search(
            # Start: Имя поля: и опциональные пробелы
            rf'{re.escape(field_name)}:\s*'
            # Value: Нежадный захват (.*?)
            r'(.*?)'
            # Lookahead (Конец): Остановка перед следующим полем, блочным тегом или концом строки.
            rf'(?=\s*(?:<[^>]+>)*\s*(?:{field_separators})|\s*</p>|\s*</li>|\s*</div>|$)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if pattern:
            raw_value = pattern.group(1).strip()
            
            # Агрессивно удаляем ВСЕ HTML-теги и сущности
            clean_value = re.sub(r'<[^>]+>', '', raw_value).strip()
            clean_value = clean_value.replace('&nbsp;', ' ').strip()

            return clean_value if clean_value else '???'

        return '???'

    # --- 1. Парсинг основных полей ---
    dev_data = get_value("Разработчик", html_content)
    lang_data = get_value("Количество игроков", html_content)

    # --- 2. Парсинг Года ---
    year_data = get_value("Год", html_content)
    year_match = re.search(r'(\d{4})', year_data)
    year = year_match.group(1) if year_match else '???'
    
    if year == '???':
        year_data_full = get_value("Дата выхода", html_content)
        year_match = re.search(r'(\d{4})', year_data_full)
        year = year_match.group(1) if year_match else '???'
    
    # --- 3. Обработка ОЦЕНКИ КРИТИКОВ ---
    critics_rating_data = get_value("Оценка критиков", html_content)
    
    # ----------------------------------------------------------------------------------
    # --- 4. Формирование итоговой строки (С УСЛОВИЕМ) ---
    # ----------------------------------------------------------------------------------
    info_parts = []
    
    # Вспомогательная функция для добавления строки только при наличии данных
    def add_info_part(label, data):
        if data != '???':
            info_parts.append(f"{label}: {data}")

    add_info_part("Разработчик", dev_data)
    add_info_part("Год", year)
    add_info_part("Количество игроков", lang_data)
    add_info_part("Оценка критиков", critics_rating_data)
    
    return "\n".join(info_parts)


# ----------------------------------------------------------------------
# КЛАСС ЭЛЕМЕНТА ИГРЫ (GameItem)
# ----------------------------------------------------------------------
class GameItem(QFrame):
    """Виджет для отображения одной игры в сетке."""

    game_launched = pyqtSignal(str)
    show_description_requested = pyqtSignal(str)

    def __init__(self, game_folder, rom_path, description, item_width, item_height, screenshots, parent=None):

        self.item_width = item_width
        self.item_height = item_height

        super().__init__(parent)
        self.setObjectName("GameItem")
        self.setFixedSize(item_width, item_height)
        self.setCursor(Qt.PointingHandCursor)

        # Тултип отображает КРАТКОЕ описание (description)
        self.setToolTip(f"**{os.path.basename(game_folder)}**\n\n{description}")

        self.game_folder = game_folder
        self.rom_path = rom_path
        self.description = description
        self.screenshots = screenshots

        title = os.path.basename(game_folder)

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
        self.title_label = QLabel(title)
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

    # ✅ ИСПРАВЛЕНИЕ: Используем mousePressEvent для правого клика
    def mousePressEvent(self, event):
        """Правый клик: запрос описания."""
        if event.button() == Qt.RightButton:
            logger.info(f"Запрос описания по правому клику для: {os.path.basename(self.game_folder)}")
            self.show_description_requested.emit(self.game_folder)
            event.accept()
        else:
            super().mousePressEvent(event)


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

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.Dialog)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("InnerDescriptionFrame")
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        # --- КАСТОМНЫЙ ЗАГОЛОВОК ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("DescTitleBar")
        self.title_bar.setFixedHeight(35) # Высота 35px

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 5, 0)
        title_layout.setSpacing(0)

        self.title_label = QLabel(f"Описание: {self.game_title}")
        self.title_label.setObjectName("DescTitleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)

        self.close_button_icon = QPushButton("✕")
        self.close_button_icon.setObjectName("DescCloseButton")
        self.close_button_icon.clicked.connect(self.accept)
        title_layout.addWidget(self.close_button_icon)

        inner_layout.addWidget(self.title_bar)
        # --- КОНЕЦ КАСТОМНОГО ЗАГОЛОВКА ---

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setObjectName("DescTextBrowser")

        self.load_styled_description(description)

        inner_layout.addWidget(self.browser)

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

        inner_layout.addWidget(bottom_widget)

        main_layout.addWidget(self.inner_frame)

        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
                border: none;
            }

            QFrame#InnerDescriptionFrame {
                background-color: #2a2a2a;
                border: none;
                border-radius: 15px;
                margin: 5px;
            }

            QWidget#DescTitleBar {
                background-color: #1a1a1a;
                border-top-left-radius: 15px;
                /* 🟢 Изменение: Добавление радиуса для правого угла */
                border-top-right-radius: 15px;
            }

            QLabel#DescTitleLabel {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 10pt;
                line-height: 35px;
            }

            QPushButton#DescCloseButton {
                background-color: transparent;
                border: none;
                font-size: 10pt;
                color: #DCDCDC;

                /* 🟢 ИЗМЕНЕНИЕ: Уменьшение размера до 25x25px */
                min-width: 25px;
                max-width: 25px;
                min-height: 25px;
                max-height: 25px;
                padding: 0;

                /* 🟢 ИЗМЕНЕНИЕ: Добавление закругления угла */
                border-top-right-radius: 15px;
            }
            /* 🟢 ИЗМЕНЕНИЕ: Убираем красное выделение при наведении */
            QPushButton#DescCloseButton:hover {
                background-color: #3a3a3a; /* Нейтральный темный цвет */
                color: #FFFFFF;
            }

            QWidget#DescBottomBar {
                background-color: #1a1a1a;
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }

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
            QTextBrowser h3 {
                color: #00FF00;
                font-size: 13pt;
                margin-top: 10px;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:

            local_pos_in_frame = self.inner_frame.mapFromParent(event.pos())

            if self.inner_frame.geometry().contains(event.pos()) and local_pos_in_frame.y() < self.title_bar.height():
                self.drag_offset = event.globalPos() - self.pos()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:

            local_pos_in_frame = self.inner_frame.mapFromParent(event.pos())

            if self.inner_frame.geometry().contains(event.pos()) and local_pos_in_frame.y() < self.title_bar.height():
                self.move(event.globalPos() - self.drag_offset)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = QPoint()
        super().mouseReleaseEvent(event)

    def load_styled_description(self, html_content):
        """
        Загружает HTML-контент, вставляет скриншоты, применяет базовый URL и прокручивает в начало.
        """
        desc_path = os.path.join(self.game_folder, "index.html")

        # 1. Генерация тегов <img> для галереи
        image_tags = []
        for path in self.screenshots:

            absolute_path = os.path.normpath(os.path.join(self.game_folder, path))
            file_url = QUrl.fromLocalFile(absolute_path).toString()

            tag = f'<img src="{file_url}" alt="{path}" style="height: 120px; max-width: none; border: 1px solid #444; margin-right: 5px; border-radius: 5px; float: left;">'
            image_tags.append(tag)

        gallery_html = f'<div style="white-space: nowrap; overflow-x: scroll; padding: 0; margin: 0; border: 1px solid #1a1a1a;">{"".join(image_tags)}</div>'

        # 2. Вставка тегов в HTML
        if '<div class="image-gallery"></div>' in html_content:
             html_content = html_content.replace(
                 '<div class="image-gallery"></div>',
                 gallery_html
               )

        # 3. Установка базового URL-адреса для QTextBrowser
        base_url = QUrl.fromLocalFile(self.game_folder + os.sep)
        self.browser.document().setBaseUrl(base_url)

        # 4. Финальная загрузка
        self.browser.setHtml(html_content)

        # 5. Прокручиваем документ в начало
        QCoreApplication.processEvents()
        cursor = self.browser.textCursor()
        cursor.setPosition(0)
        self.browser.setTextCursor(cursor)