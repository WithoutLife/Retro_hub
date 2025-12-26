# main_app.py

import sys
import os
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QFrame, QScrollArea, QGridLayout, QMessageBox, QLineEdit,
    QDialog, QButtonGroup
)
from PyQt5.QtGui import QPixmap, QIcon, QRegion, QPainterPath, QFont
from PyQt5.QtCore import QSize, Qt, QPoint, QTimer, QRectF, QCoreApplication, QEvent, QObject, QThread, pyqtSignal

# --- КРИТИЧЕСКИ ВАЖНЫЕ ИМПОРТЫ ---
from config import *
from style import apply_dark_theme
from threads import EmulatorMonitorThread, ImageLoaderThread, GameLoaderThread
from widgets import GameItem, DescriptionWindow, extract_short_info

import resources_rc

from app_logic import AppLogicMixin
from window_events import WindowEventsMixin


logger = logging.getLogger(__name__)

VERSION = "0.40"
VERSION_CHANGE_NOTE = "Console buttons moved to search bar. Action bar removed."

def setup_logging():
    """Настраивает базовое логирование и создает лог-файл."""
    log_file_path = os.path.join(BASE_DIR, "launcher.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class LauncherApp(AppLogicMixin, WindowEventsMixin, QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.rom_list = []
        self.num_cols = 0
        self.game_loader_thread = None
        self.emulator_thread = None
        self.threads = []
        
        self.console_button_group = None

        self.init_ui_elements()
        self.apply_initial_styles()
        self.setWindowTitle(f"Ретро Лаунчер v{VERSION}")
        self.setWindowIcon(QIcon(":/launcher_icon.ico"))

        # 🔴 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Удаляем вызов switch_console(CURRENT_CONSOLE).
        # Начальная загрузка теперь происходит в apply_initial_styles().
        # QTimer.singleShot(100, lambda: self.switch_console(CURRENT_CONSOLE))


    # --- ИНИЦИАЛИЗАЦИЯ UI ---
    def init_ui_elements(self):
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # --- ЦЕНТРАЛЬНЫЙ ВИДЖЕТ ---
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(self.centralwidget)
        
        # --- 1. ПАНЕЛЬ ЗАГОЛОВКА (Title Bar) ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(55)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(10, 5, 5, 5)
        self.title_bar_layout.setSpacing(10)
        
        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")
        
        pixmap = QPixmap(":/retro_hub_logo.png")
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaledToHeight(50, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            self.logo_label.setFixedWidth(scaled_pixmap.width())
        else:
            self.logo_label.setText(f"Ретро Лаунчер v{VERSION}")
            logger.warning("Логотип 'retro_hub_logo.png' не найден в ресурсах. Используется текстовый заголовок.")
            
        self.title_bar_layout.addWidget(self.logo_label)
        self.title_bar_layout.addStretch(1)
        
        # Кнопки управления окном
        self.minimize_button = QPushButton("—")
        self.maximize_button = QPushButton("☐")
        self.close_button = QPushButton("✕")
        
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(self.close)

        for btn in [self.minimize_button, self.maximize_button, self.close_button]:
            btn.setFixedSize(40, 40)
            btn.setObjectName("windowControlButton")
            self.title_bar_layout.addWidget(btn)

        self.main_layout.addWidget(self.title_bar)
        
        # --- 2. ПАНЕЛЬ ПОИСКА И КНОПКИ КОНСОЛЕЙ ---
        self.search_container = QFrame()
        self.search_container.setObjectName("searchContainer")
        self.search_layout = QHBoxLayout(self.search_container)
        self.search_layout.setContentsMargins(10, 5, 10, 5)
        self.search_layout.setSpacing(10)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Поиск игр...")
        self.search_box.setObjectName("searchBox")
        self.search_box.setFixedHeight(40)
        self.search_box.textChanged.connect(self.filter_roms)
        self.search_box.setClearButtonEnabled(True)
        self.search_layout.addWidget(self.search_box, 1)

        # КНОПКИ КОНСОЛЕЙ 
        self.dendy_button = QPushButton("")
        self.sega_button = QPushButton("")
        self.sony_button = QPushButton("")
        
        # Иконки (Убедились, что пути соответствуют коротким именам в .qrc)
        ICON_MAP = {
            "DENDY": ":/icon_dendy.png",
            "SEGA": ":/icon_sega.png",
            "SONY": ":/icon_sony.png"
        }
        
        # ДОБАВЛЯЕМ ГРУППУ КНОПОК
        self.console_button_group = QButtonGroup(self)
        self.console_button_group.setExclusive(True)
        
        for btn, console_name in zip(
            [self.dendy_button, self.sega_button, self.sony_button],
            ["DENDY", "SEGA", "SONY"]
        ):
            btn.setCheckable(True)
            btn.setObjectName("simpleConsoleButton")
            btn.setFixedSize(40, 40)
            
            # Отключаем политику фокуса
            btn.setFocusPolicy(Qt.NoFocus)
            
            # Установка иконки
            if console_name in ICON_MAP:
                btn.setIcon(QIcon(ICON_MAP[console_name]))
                btn.setIconSize(QSize(32, 32))
            
            self.console_button_group.addButton(btn)
            
            btn.clicked.connect(lambda checked, name=console_name: self._debug_switch_console(name))
            self.search_layout.addWidget(btn)
        
        
        self.main_layout.addWidget(self.search_container)
        
        # --- 3. ОБЛАСТЬ ПРОКРУТКИ (Scroll Area) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("gameScrollArea")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("gridWidget")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_area.setWidget(self.grid_widget)
        
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # --- 4. ФУТЕР (Footer) ---
        self.footer_widget = QFrame()
        self.footer_widget.setObjectName("footerWidget")
        self.footer_widget.setFixedHeight(25)
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(10, 0, 10, 0)
        
        # 1. ТЕКСТ ВЕРСИИ (Прижат к левой стороне)
        version_info = f"Retro HUB Ver {VERSION} ({VERSION_CHANGE_NOTE})"
        self.version_label = QLabel(version_info)
        self.version_label.setObjectName("footerLabel")
        self.version_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.footer_layout.addWidget(self.version_label)
        
        # Распорка, которая прижимает два QLabel к разным сторонам
        self.footer_layout.addStretch(1)
        
        # 2. ТЕКСТ РАЗРАБОТЧИКА (Прижат к правой стороне)
        creator_info = "© 2025, Developed by No_fate"
        self.creator_label = QLabel(creator_info)
        self.creator_label.setObjectName("footerLabel")
        self.creator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.footer_layout.addWidget(self.creator_label)

        self.main_layout.addWidget(self.footer_widget)

    # --- ДИНАМИЧЕСКИЕ МЕТОДЫ ---

    def apply_initial_styles(self):
        """
        Применяет общую темную тему и начальные стили консоли, 
        а также запускает первоначальную загрузку контента.
        """
        app = QCoreApplication.instance()
        apply_dark_theme(app)
        
        # 1. Применяем начальный градиентный стиль (из AppLogicMixin)
        self.apply_console_style()
        
        # 🟢 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Инициализация контента при запуске
        
        # 2. Устанавливаем checked-состояние для начальной кнопки (DENDY)
        # Этот метод вызывает self.dendy_button.setChecked(True)
        self.update_console_buttons()
        
        # 3. Запускаем загрузку ROM'ов и обновление заголовка
        self.update_ui_for_console(CURRENT_CONSOLE) 

        
if __name__ == "__main__":
    
    setup_logging()
    
    try:
        app = QApplication(sys.argv)
        
        launcher = LauncherApp()
        
        INITIAL_WIDTH = 780
        INITIAL_HEIGHT = 740
        
        launcher.setMinimumSize(INITIAL_WIDTH, INITIAL_HEIGHT)
        launcher.resize(INITIAL_WIDTH, INITIAL_HEIGHT)
        launcher.center_window()

        launcher.show()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical("Критическая ошибка при запуске приложения:", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Приложение не может запуститься из-за ошибки: {e}")
        sys.exit(1)