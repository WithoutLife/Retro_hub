import sys
import os
import logging
import math
import fnmatch 

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
    QHBoxLayout, QFrame, QScrollArea, QGridLayout, QMessageBox, QLineEdit,
    QDialog 
) 
from PyQt5.QtGui import QPixmap, QIcon, QFont, QRegion, QPainterPath
from PyQt5.QtCore import QSize, Qt, QPoint, QRect, QTimer, QRectF

# --- КРИТИЧЕСКИ ВАЖНЫЕ ИМПОРТЫ (ПРЕДПОЛАГАЕТСЯ, ЧТО ФАЙЛЫ РЯДОМ) ---
from config import *
from style import apply_dark_theme 
from threads import EmulatorMonitorThread, ImageLoaderThread 
# ИСПРАВЛЕНО: Import extract_short_info из widgets.py
from widgets import GameItem, DescriptionWindow, extract_short_info 

# >>> ВАЖНО: Импортируем сгенерированный ресурсный файл.
import resources_rc


# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logger = logging.getLogger(__name__) 

# --- НОВАЯ ВЕРСИЯ И ОПИСАНИЕ ИЗМЕНЕНИЯ (Для v0.19) ---
VERSION = "0.19" 
VERSION_CHANGE_NOTE = "UI Clean-up & Fixes" 

def setup_logging():
    """Настраивает базовое логирование и создает лог-файл."""
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s: %(message)s',
                        handlers=[
                            logging.StreamHandler(sys.stdout),
                            # BASE_DIR импортируется из config
                            logging.FileHandler(os.path.join(BASE_DIR, 'retro_hub.log'))
                        ])
    logger.info(f"==========================================")
    logger.info(f"=== Retro HUB v {VERSION} ({VERSION_CHANGE_NOTE}) ===")
    logger.info(f"==========================================")


# --- ОСНОВНОЙ КЛАСС ЛАУНЧЕРА ---
class LauncherApp(QMainWindow): 
    
    def __init__(self):
        super().__init__()
        
        # --- Инициализация QLineEdit и central_widget ---
        class Ui_MainWindow:
            # ИСПРАВЛЕННАЯ ФУНКЦИЯ
            def setupUi(self, MainWindow): 
                self.centralwidget = QWidget(MainWindow)
                MainWindow.setCentralWidget(self.centralwidget)
                layout = QVBoxLayout(self.centralwidget)
                self.lineEdit = QLineEdit() 
                self.centralwidget.setLayout(layout)
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.lineEdit = self.ui.lineEdit 
        self.central_widget = self.ui.centralwidget 
        self.central_widget.setObjectName("centralwidget")

        # --- АТРИБУТЫ КАСТОМНОГО ОКНА ---
        self.drag_offset = QPoint()
        self.resizing = False
        self.emulator_thread = None 
        
        # --- ФЛАГИ БЕССТЫКОВОГО ОКНА ---
        self.setWindowFlags(Qt.FramelessWindowHint) 
        self.setAttribute(Qt.WA_NativeWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowTitle("Retro HUB") 
        
        MIN_WIDTH = ITEM_WIDTH + 20 
        MIN_HEIGHT = 55 + 55 + ITEM_HEIGHT + 15 + 20 
        
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT) 
        self.resize(START_WIDTH, START_HEIGHT)
        
        self.init_ui_elements() 
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft) 
        self.grid_layout.setSpacing(15) 
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.grid_widget)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("gameScrollArea")
        
        self.setup_main_layout()

        self.rom_list = [] 
        self.threads = []  
        self.num_cols = 0 
        
        self.lineEdit.textChanged.connect(self.filter_roms)
        
        self.set_rounded_window_mask(radius=10) 
        
        self._set_window_icon()
        
        # 🌟 ИСПРАВЛЕНИЕ ДЛЯ УСКОРЕНИЯ: Откладываем загрузку ROM'ов
        QTimer.singleShot(0, lambda: self.set_current_console(CURRENT_CONSOLE))
        
        QTimer.singleShot(200, self.force_grid_redraw) 
        
    def _set_window_icon(self):
        """Устанавливает иконку окна, используя путь из ресурсов."""
        icon_path = ICON_FILE_NAME 
        icon = QIcon(icon_path)
        
        if not icon.isNull():
            self.setWindowIcon(icon)
        else:
            logger.warning(f"Иконка окна не найдена по пути: {icon_path}")
        
    def init_ui_elements(self):
        """Инициализация Заголовка, Футера и Кнопки Переключения."""
        
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(50) 
        
        # --- Кнопки управления окном (Стили применяются в apply_icon_buttons_styles) ---
        self.minimize_button = QPushButton("—") 
        self.maximize_button = QPushButton("☐") 
        self.close_button = QPushButton("✕")  
        
        self.minimize_button.setObjectName("minimizeButton")
        self.maximize_button.setObjectName("maximizeButton")
        self.close_button.setObjectName("closeButton")
        
        self.apply_icon_buttons_styles() 
        
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(self.close)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0) 
        title_layout.setSpacing(0) 
        
        # --- Загрузка логотипа-изображения из ресурсов ---
        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")

        logo_path = LOGO_FILE_NAME 
        logo_pixmap = QPixmap(logo_path)
        
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaledToHeight(
                LOGO_HEIGHT, 
                Qt.SmoothTransformation
            )
            self.logo_label.setPixmap(scaled_logo)
            self.logo_label.setStyleSheet("padding-left: 10px;") 
        else:
            self.logo_label.setText("Retro HUB") 
            self.logo_label.setStyleSheet(f"color: #FFFFFF; font-size: 18pt; font-weight: bold; padding: 5px 10px;")


        title_layout.addWidget(self.logo_label)
        title_layout.addStretch(1) 
        
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.maximize_button)
        title_layout.addWidget(self.close_button)
        
        self.switch_button = QPushButton("Переключить")
        self.switch_button.setObjectName("switchButton")
        self.switch_button.setFixedWidth(180)
        self.switch_button.clicked.connect(self.switch_console)
        
        self.footer_widget = QWidget()
        self.footer_widget.setObjectName("footer_widget")
        self.footer_widget.setFixedHeight(15) 
        
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(5, 0, 5, 0) 
        
        # --- ФУТЕР: Отображение версии программы и среды ---
        self.version_label = QLabel(f"v {VERSION} ({VERSION_CHANGE_NOTE})") 
        self.copyright_label = QLabel("No_fate 2025")
        
        self.version_label.setObjectName("footerLabel")
        self.copyright_label.setObjectName("footerLabel")
        
        footer_font = QFont()
        footer_font.setPointSize(7)
        self.version_label.setFont(footer_font)
        self.copyright_label.setFont(footer_font)

        self.footer_layout.addWidget(self.version_label)
        self.footer_layout.addStretch(1) 
        self.footer_layout.addWidget(self.copyright_label)

    # Стили кастомных кнопок (Темный/Неоновый акцент)
    def apply_icon_buttons_styles(self):
        """
        Применяет стили к кастомным кнопкам окна:
        Нормальное состояние: Неоново-пурпурный цвет.
        При наведении: Белый цвет.
        """
        
        # Определяем NEON_COLOR
        NEON_COLOR = "#8A2BE2" 
        HOVER_BG_COLOR = "#383838" 

        style = f"""
            QPushButton {{
                background-color: transparent; 
                border: none;
                font-size: 12pt;
                color: {NEON_COLOR}; 
                padding: 0px 0px;
                min-height: 40px;
                min-width: 40px;
                max-width: 40px;
                font-family: "Segoe UI Symbol", sans-serif;
                font-weight: bold; 
            }}
            
            /* Белый акцент при наведении для ВСЕХ кнопок */
            QPushButton:hover {{
                background-color: {HOVER_BG_COLOR}; 
                color: #FFFFFF; 
            }}
            
            /* Специальное правило для кнопки закрытия при НАЖАТИИ (КРАСНЫЙ ФОН) */
            QPushButton#closeButton:pressed {{
                background-color: #e81123; 
                color: #FFFFFF; 
            }}
        """
        self.minimize_button.setStyleSheet(style)
        self.maximize_button.setStyleSheet(style)
        self.close_button.setStyleSheet(style)
        
    def setup_main_layout(self):
        """Устанавливает элементы в главный Layout."""
        main_layout = self.centralWidget().layout()
        
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 10, 10, 10) 
        search_layout.setSpacing(10)

        self.lineEdit.setObjectName("searchLineEdit")
        search_layout.addWidget(self.lineEdit)
        search_layout.addWidget(self.switch_button)
        
        main_layout.setSpacing(0)
        
        # Очистка Layout перед установкой
        for i in reversed(range(main_layout.count())): 
             widget = main_layout.itemAt(i).widget()
             if widget: widget.setParent(None)

        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(search_container) 
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(self.footer_widget)
            
    def handle_image_ready(self, pixmap, item_widget):
        """Слот: устанавливает загруженный QPixmap в GameItem."""
        item_widget.set_cover_pixmap(pixmap)
        
    # Генерация градиента для фона
    def _get_console_stylesheet(self, console_color, black_color):
        """Создает QSS для диагонального градиента (только centralwidget)."""
        
        settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {})
        gradient_start_color = settings.get("GRADIENT_START", "#1a1a1a")
        gradient_end_color = settings.get("GRADIENT_END", "#280040")

        gradient_style = f"""
        #centralwidget {{ 
            background-color: qlineargradient(
                spread:pad, 
                x1:0, y1:0, x2:1, y2:1, 
                stop:0 {gradient_start_color}, 
                stop:1 {gradient_end_color}
            ); 
        }}
        """
        return gradient_style
        
    def resizeEvent(self, event):
        """Обновление сетки при изменении размера окна и маскирование углов."""
        super().resizeEvent(event)
        
        # Применяем маску только если окно не максимизировано
        if not self.isMaximized(): 
            self.set_rounded_window_mask(radius=10)
        else:
            self.setMask(QRegion()) # Убираем маску при максимальном размере
        
        scroll_area_width = self.scroll_area.viewport().width() 
        spacing = self.grid_layout.spacing()
        
        new_num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))

        if new_num_cols != self.num_cols:
            self.num_cols = new_num_cols
            if self.rom_list: 
                self.populate_grid(self.rom_list) 
            
            for c in range(self.grid_layout.columnCount()):
                self.grid_layout.setColumnStretch(c, 0)
            if self.num_cols > 0:
                self.grid_layout.setColumnStretch(self.num_cols - 1, 1)

    def force_grid_redraw(self):
        """Принудительно вызывает пересчет и перерисовку сетки."""
        self.resizeEvent(None) 
            
    def set_current_console(self, console_key):
        """Устанавливает текущие параметры консоли, градиент и загружает ROM'ы."""
        global CURRENT_CONSOLE
        CURRENT_CONSOLE = console_key
        
        settings = CONSOLE_SETTINGS[CURRENT_CONSOLE]
        
        # 1. Применяем общую темную тему (QSS).
        apply_dark_theme(QApplication.instance()) 
        
        # 2. Применяем специфический QSS с градиентом и акцентными цветами.
        style = self._get_console_stylesheet(settings["GRADIENT_END"], settings["GRADIENT_START"])
        self.centralWidget().setStyleSheet(style) 
        
        other_console = 'SEGA' if console_key == 'DENDY' else 'DENDY'
        self.switch_button.setText(f"Переключить на {other_console}") 
            
        self.load_roms()

    def switch_console(self):
        """Переключает активную консоль."""
        if CURRENT_CONSOLE == "DENDY":
            self.set_current_console("SEGA")
        else:
            self.set_current_console("DENDY")
        
    def find_game_description(self, game_folder_path):
        """Читает index.html и извлекает краткие технические детали для тултипа."""
        
        html_path = os.path.join(game_folder_path, "index.html")
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Используем импортированную функцию из widgets.py
                return extract_short_info(html_content)
                
            except Exception:
                logger.warning(f"Ошибка чтения или парсинга index.html для {os.path.basename(game_folder_path)}", exc_info=True)
        
        # Резервный вариант: чтение description.txt
        desc_path = os.path.join(game_folder_path, "description.txt") 
        if os.path.exists(desc_path):
            try:
                with open(desc_path, 'r', encoding='utf-8') as f:
                    # Возвращаем первые 250 символов
                    return f.read(250).strip()
            except Exception:
                return "Описание недоступно."
                
        return "Краткое описание отсутствует." 

    def find_screenshots(self, game_folder_path):
        """Находит все файлы изображений в папке /images, кроме 'cartridge'."""
        images_dir = os.path.join(game_folder_path, "images")
        screenshots = []
        
        ALLOWED_SCREENSHOT_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]
        
        if os.path.isdir(images_dir):
            for filename in os.listdir(images_dir):
                if "cartridge" not in filename.lower() and any(
                    filename.lower().endswith(ext) for ext in ALLOWED_SCREENSHOT_EXTENSIONS
                ):
                    # Важно: сохраняем путь как относительный к папке игры (images/filename)
                    screenshots.append(f"images/{filename}")
                    
        return screenshots
    
    def show_game_description(self, game_folder_path):
        """
        Находит данные игры по пути к папке и открывает окно описания.
        Этот метод вызывается по сигналу правого клика из GameItem.
        """
        
        game_data = next((item for item in self.rom_list if item['folder'] == game_folder_path), None)
        
        if game_data:
            logger.info(f"Открытие окна описания для: {game_data['title']}")
            
            description_window = DescriptionWindow(
                game_folder=game_data['folder'],
                description=game_data['description'],
                screenshots=game_data['screenshots'],
                parent=self
            )
            
            # Центрируем окно описания относительно главного окна
            main_rect = self.frameGeometry()
            desc_rect = description_window.frameGeometry()
            desc_rect.moveCenter(main_rect.center())
            description_window.move(desc_rect.topLeft())

            description_window.exec_()
        else:
            logger.warning(f"Данные игры для папки {game_folder_path} не найдены.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти данные для описания этой игры.")


    def populate_grid(self, filtered_roms):
        """Полностью очищает сетку, создает виджеты GameItem и запускает потоки загрузки."""
        
        for i in reversed(range(self.grid_layout.count())): 
            widget_to_remove = self.grid_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        self.threads = [] 

        if not filtered_roms:
            empty_label = QLabel(f"Игры для {CONSOLE_SETTINGS[CURRENT_CONSOLE]['NAME']} не найдены.")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0, 1, 1) 
            return

        scroll_area_width = self.scroll_area.viewport().width()
        spacing = self.grid_layout.spacing()
        self.num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))
        
        for index, game_data in enumerate(filtered_roms):
            row = index // self.num_cols
            col = index % self.num_cols
            
            item_widget = GameItem(
                game_folder=game_data['folder'], 
                rom_path=game_data['rom'],
                description=game_data['description'],
                item_width=ITEM_WIDTH,      
                item_height=ITEM_HEIGHT,
                screenshots=game_data['screenshots']
            )
            # ИСПРАВЛЕНО: Подключение сигнала напрямую
            item_widget.game_launched.connect(self.launch_game)
            item_widget.show_description_requested.connect(self.show_game_description)
            
            self.grid_layout.addWidget(item_widget, row, col)
            
            # 🌟 ИСПРАВЛЕНИЕ: Удален лишний аргумент ICON_SIZE, который вызывал TypeError
            loader = ImageLoaderThread(
                item_widget, 
                game_data['folder'], # game_folder (Позиционный аргумент #2)
                allowed_cover_extensions=ALLOWED_COVER_EXTENSIONS
            )
            loader.image_ready.connect(self.handle_image_ready)
            self.threads.append(loader)
            loader.start()
        
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)
        if self.num_cols > 0:
            self.grid_layout.setColumnStretch(self.num_cols - 1, 1)

    def filter_roms(self, text):
        """Фильтрует игры и обновляет сетку."""
        search_text = text.lower()
        filtered = [game for game in self.rom_list if search_text in game['title'].lower()]
        self.populate_grid(filtered) 
        
        
    def load_roms(self):
        """Сканирует корневую папку текущей консоли и загружает список игр.""" 
        self.rom_list.clear()
        
        settings = CONSOLE_SETTINGS[CURRENT_CONSOLE]
        GAME_ROOT_FOLDER = settings["ROOT_FOLDER"]
        ALLOWED_ROM_EXTENSIONS = settings["ROM_EXTENSIONS"]
        
        if not os.path.exists(GAME_ROOT_FOLDER):
            QMessageBox.critical(self, "Ошибка", f"Корневая папка игр ({settings['NAME']}) не найдена: {GAME_ROOT_FOLDER}")
            self.populate_grid([])
            return

        for item_name in os.listdir(GAME_ROOT_FOLDER):
            game_folder_path = os.path.join(GAME_ROOT_FOLDER, item_name)
            
            if os.path.isdir(game_folder_path):
                rom_path = self.find_rom_file(game_folder_path, ALLOWED_ROM_EXTENSIONS)
                
                if rom_path:
                    # >>> Используем find_game_description, который вызывает extract_short_info <<<
                    description = self.find_game_description(game_folder_path) 
                    screenshots = self.find_screenshots(game_folder_path)
                    
                    self.rom_list.append({
                        'folder': game_folder_path,
                        'rom': rom_path,
                        'title': item_name,
                        'description': description,
                        'screenshots': screenshots 
                    })
        self.rom_list.sort(key=lambda x: x['title'])
        self.populate_grid(self.rom_list)
        self.lineEdit.clear()
            

    def find_rom_file(self, game_folder_path, allowed_extensions):
        """Ищет ROM-файл в подпапке /rom, используя заданные расширения."""
        rom_dir = os.path.join(game_folder_path, "rom")
        
        if os.path.isdir(rom_dir):
            for filename in os.listdir(rom_dir):
                for ext in allowed_extensions:
                    if filename.lower().endswith(ext):
                        return os.path.join(rom_dir, filename)
        return None
        
    def show_launcher(self):
        """Разворачивает лаунчер из свернутого состояния после закрытия эмулятора."""
        
        self.emulator_thread = None 
        
        self.setWindowState(Qt.WindowNoState)
        self.showNormal() 
        
        self.maximize_button.setText("☐")
        
        if self.rom_list:
            self.load_roms()
            logger.info("Сетка игр обновлена после закрытия эмулятора.")
        
    def showMinimized(self):
        self.setWindowState(Qt.WindowMinimized)
        super().showMinimized()
        
    def launch_game(self, rom_path):
        """Запускает эмулятор текущей консоли в отдельном потоке и сворачивает лаунчер."""
        
        settings = CONSOLE_SETTINGS[CURRENT_CONSOLE]
        EMULATOR_PATH = settings["EMULATOR_PATH"]

        if not os.path.exists(EMULATOR_PATH):
            QMessageBox.critical(self, "Ошибка Запуска", f"Эмулятор {settings['NAME']} не найден по пути: {EMULATOR_PATH}")
            logger.error(f"Эмулятор не найден: {EMULATOR_PATH}")
            return
            
        try:
            # Получаем аргумент полного экрана из config.py
            fullscreen_arg = settings['FULLSCREEN_ARG'] 
            
            self.emulator_thread = EmulatorMonitorThread(EMULATOR_PATH, rom_path, fullscreen_arg)
            self.emulator_thread.emulator_closed.connect(self.show_launcher)
            self.emulator_thread.start()
            self.showMinimized() 
            logger.info(f"Игра {os.path.basename(os.path.dirname(rom_path))} запущена.")
            
        except Exception:
            logger.error("Не удалось запустить процесс эмулятора:", exc_info=True)
            QMessageBox.critical(self, "Ошибка Запуска", "Не удалось запустить процесс эмулятора.")

    def toggle_maximized(self):
        """Переключает состояние окна между нормальным и максимизированным."""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("☐")
        else:
            self.showMaximized()
            self.maximize_button.setText("❐") 

    def set_rounded_window_mask(self, radius=10):
        """Применяет маску для скругления углов бесстыкового окна."""
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(QRectF(rect), radius, radius)
        
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        
    # --- ОБРАБОТЧИКИ СОБЫТИЙ ДЛЯ ПЕРЕТАСКИВАНИЯ И РЕСАЙЗА ---
    RESIZE_BORDER_WIDTH = 5 

    def _get_cursor_from_edge(self, edges):
        """Сопоставляет флаги края с формой курсора."""
        if edges == (Qt.TopEdge | Qt.LeftEdge) or edges == (Qt.BottomEdge | Qt.RightEdge): 
            return Qt.SizeFDiagCursor
        if edges == (Qt.TopEdge | Qt.RightEdge) or edges == (Qt.BottomEdge | Qt.LeftEdge): 
            return Qt.SizeBDiagCursor
        if edges == Qt.LeftEdge or edges == Qt.RightEdge: 
            return Qt.SizeHorCursor
        if edges == Qt.TopEdge or edges == Qt.BottomEdge: 
            return Qt.SizeVerCursor
        return None 
        
    def get_resize_edge(self, pos):
        """Определяет, находится ли курсор в зоне для изменения размера и возвращает флаг края (Qt.Edges)."""
        if self.isMaximized():
            return Qt.Edges(0) 
            
        rect = self.rect()
        b = self.RESIZE_BORDER_WIDTH

        on_left = pos.x() < b
        on_right = pos.x() > rect.width() - b
        on_top = pos.y() < b
        on_bottom = pos.y() > rect.height() - b

        edges = Qt.Edges(0) 
        
        if on_left: edges |= Qt.LeftEdge
        if on_right: edges |= Qt.RightEdge
        if on_top: edges |= Qt.TopEdge
        if on_bottom: edges |= Qt.BottomEdge
        
        return edges
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            
            resize_edge = self.get_resize_edge(event.pos()) 
            
            if resize_edge:
                self.resizing = True
                self.windowHandle().startSystemResize(resize_edge) 
                event.accept()
                return
            
            if event.pos().y() < self.title_bar.height():
                self.drag_offset = event.globalPos() - self.pos()
                event.accept()
            else:
                super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.isMaximized():
            super().mouseMoveEvent(event)
            return

        if event.buttons() == Qt.LeftButton:
            if not self.resizing and event.pos().y() < self.title_bar.height():
                self.move(event.globalPos() - self.drag_offset)
        else:
            resize_edge = self.get_resize_edge(event.pos()) 
            cursor_shape = self._get_cursor_from_edge(resize_edge) 
            
            if cursor_shape:
                self.setCursor(cursor_shape)
            else:
                self.unsetCursor()
            
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.unsetCursor()
        super().mouseReleaseEvent(event)
        
    def closeEvent(self, event):
        """Очищает все потоки перед закрытием основного окна."""
        
        logger.info("Закрытие приложения. Остановка всех активных потоков.")
        
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        
        if self.emulator_thread is not None and self.emulator_thread.isRunning():
            self.emulator_thread.quit()
            self.emulator_thread.wait()
            
        super().closeEvent(event)

# ----------------------------------------------------------------------
# ТОЧКА ВХОДА
# ----------------------------------------------------------------------
if __name__ == "__main__":
    
    setup_logging()
    
    app = QApplication(sys.argv)
    
    apply_dark_theme(app)
    
    try:
        window = LauncherApp()
    except Exception as e:
        logger.critical(f"Критическая ошибка при создании LauncherApp: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Приложение не может запуститься из-за ошибки: {e}")
        sys.exit(1)
        
    window.show()
    sys.exit(app.exec_())