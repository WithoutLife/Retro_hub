import sys
import os
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QFrame, QScrollArea, QGridLayout, QMessageBox, QLineEdit,
    QDialog, QButtonGroup, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QIcon, QRegion, QPainterPath, QFont
from PyQt5.QtCore import QSize, Qt, QPoint, QTimer, QRectF, QCoreApplication, QEvent, QObject, QThread, pyqtSignal, QRect # <--- QRect добавлен

# --- КРИТИЧЕСКИ ВАЖНЫЕ ИМПОРТЫ ---
from config import *
from style import apply_dark_theme
from threads import EmulatorMonitorThread, ImageLoaderThread, GameLoaderThread
from widgets import GameItem, DescriptionWindow, extract_short_info

import resources_rc

# 💡 Предполагаем, что app_logic.py и window_events.py существуют
from app_logic import AppLogicMixin
from window_events import WindowEventsMixin


logger = logging.getLogger(__name__)

VERSION = "0.51"
VERSION_CHANGE_NOTE = "Full-screen stabilization and removal of minimum size limit." # Обновлено

def setup_logging():
# ... (Без изменений) ...
    """Настраивает базовое логирование и создает лог-файл."""
    try:
        log_file_path = os.path.join(BASE_DIR, "launcher.log")
    except NameError:
        log_file_path = "launcher.log"
        
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
        self.game_items = {} 
        self.vertical_spacer = None 
        
        self.is_maximized = False
        self.normal_margins = 10 
        
        # 💡 ИСПРАВЛЕНИЕ 1: Инициализация normal_geometry
        self.normal_geometry = QRect(100, 100, 780, 740) # Произвольная начальная позиция
        
        self.init_ui_elements()
        self.apply_initial_styles()
        self.setWindowTitle(f"Ретро Лаунчер v{VERSION}")
        self.setWindowIcon(QIcon(":/launcher_icon.ico")) 


    # --- ИНИЦИАЛИЗАЦИЯ UI (Без изменений, только для контекста) ---
    def init_ui_elements(self):
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # --- ЦЕНТРАЛЬНЫЙ ВИДЖЕТ ---
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(self.centralwidget)
        
        # --- КОНТЕЙНЕР ДЛЯ СОДЕРЖИМОГО ---
        self.content_container = QWidget(self.centralwidget)
        self.content_container.setObjectName("contentContainer")
        self.content_layout = QVBoxLayout(self.content_container)
        
        self.content_layout.setContentsMargins(
            self.normal_margins, self.normal_margins, 
            self.normal_margins, self.normal_margins
        )
        self.content_layout.setSpacing(0)
        
        # 1. ПАНЕЛЬ ЗАГОЛОВКА (Title Bar) 
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

        self.content_layout.addWidget(self.title_bar)
        
        # 2. ПАНЕЛЬ ПОИСКА И КНОПКИ КОНСОЛЕЙ (Без изменений)
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
        
        self.search_input = self.search_box

        # КНОПКИ КОНСОЛЕЙ
        self.dendy_button = QPushButton("")
        self.sega_button = QPushButton("")
        self.sony_button = QPushButton("")
        
        ICON_MAP = {
            "DENDY": ":/icon_dendy.png",
            "SEGA": ":/icon_sega.png",
            "SONY": ":/icon_sony.png"
        }
        
        self.console_button_group = QButtonGroup(self)
        self.console_button_group.setExclusive(True)
        
        if not hasattr(self, 'console_buttons'):
            self.console_buttons = {}
        
        for btn, console_name in zip(
            [self.dendy_button, self.sega_button, self.sony_button],
            ["DENDY", "SEGA", "SONY"]
        ):
            btn.setCheckable(True)
            btn.setObjectName("simpleConsoleButton")
            btn.setFixedSize(40, 40)
            btn.setFocusPolicy(Qt.NoFocus)
            
            if console_name in ICON_MAP:
                btn.setIcon(QIcon(ICON_MAP[console_name]))
                btn.setIconSize(QSize(32, 32))
            
            self.console_button_group.addButton(btn)
            self.console_buttons[console_name] = btn
            btn.clicked.connect(lambda checked, name=console_name: self.switch_console(name))
            self.search_layout.addWidget(btn)
        
        
        self.content_layout.addWidget(self.search_container)
        
        # 3. ОБЛАСТЬ ПРОКРУТКИ (Scroll Area) 
        self.scroll_area = QScrollArea() 
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("gameScrollArea")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("gridWidget")
        self.grid_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.grid_layout = QGridLayout(self.grid_widget) 
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        self.vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.grid_layout.addItem(self.vertical_spacer, 999, 0, 1, 1) 
        
        self.scroll_area.setWidget(self.grid_widget)
        
        self.content_layout.addWidget(self.scroll_area, 1)
        
        # 4. ФУТЕР (Footer) (Без изменений)
        self.footer_widget = QFrame()
        self.footer_widget.setObjectName("footerWidget")
        self.footer_widget.setFixedHeight(25)
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(10, 0, 10, 0)
        
        version_info = f"Retro HUB Ver {VERSION} ({VERSION_CHANGE_NOTE})"
        self.version_label = QLabel(version_info)
        self.version_label.setObjectName("footerLabel")
        self.version_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.footer_layout.addWidget(self.version_label)
        
        self.footer_layout.addStretch(1)
        
        creator_info = "© 2025, Developed by No_fate"
        self.creator_label = QLabel(creator_info)
        self.creator_label.setObjectName("footerLabel")
        self.creator_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.footer_layout.addWidget(self.creator_label)

        self.content_layout.addWidget(self.footer_widget)
        
        self.main_layout.addWidget(self.content_container)


    # --- ОБРАБОТЧИКИ СОБЫТИЙ ОКНА (С КРИТИЧЕСКИМИ ИСПРАВЛЕНИЯМИ) ---

    def toggle_maximized(self):
        """Переключает состояние окна между развернутым и нормальным, используя QRect."""
        if self.is_maximized:
            # 🟢 ВОССТАНОВЛЕНИЕ: Возвращаемся к сохраненной геометрии
            self.setGeometry(self.normal_geometry)
            
            self.is_maximized = False
            self.maximize_button.setText("☐")
            
            # Возврат отступов для content_container
            self.content_layout.setContentsMargins(
                self.normal_margins, self.normal_margins, 
                self.normal_margins, self.normal_margins
            ) 
            logger.info("Окно восстановлено.")
        else:
            # 🔴 РАЗВЕРТЫВАНИЕ
            # 1. Сохраняем текущую (нормальную) геометрию
            self.normal_geometry = self.geometry()
            
            # 2. Получаем геометрию доступного экрана (без панели задач Windows)
            # QApplication.desktop().availableGeometry() - предпочтительнее для Frameless
            screen = QApplication.desktop().availableGeometry()
            
            # 3. Устанавливаем геометрию на полный экран
            self.setGeometry(screen)

            self.is_maximized = True
            self.maximize_button.setText("❐")
            
            # Убираем отступы для content_container при максимизации
            self.content_layout.setContentsMargins(0, 0, 0, 0) 
            logger.info("Окно развернуто.")
            
        # Принудительное обновление
        self.main_layout.activate()
        self.centralwidget.update()
        
    def resizeEvent(self, event):
        """Принудительно обновляет макеты и пересчитывает сетку игр."""
        super().resizeEvent(event)
        
        # Если окно НЕ развернуто, сохраняем его текущую геометрию
        if not self.is_maximized:
             self.normal_geometry = self.geometry()
             
        if self.centralwidget:
            self.centralwidget.style().polish(self.centralwidget)
            self.centralwidget.update()
        
        # Вызываем layout_roms, чтобы пересчитать num_cols
        if hasattr(self, 'layout_roms') and self.rom_list:
            self.layout_roms(self.rom_list) 
        
        self.title_bar.update()
        logger.debug(f"ResizeEvent: Window size updated to {self.width()}x{self.height()}")
        
    def changeEvent(self, event):
        """Обрабатывает изменения состояния окна (Maximized/Normal)."""
        super().changeEvent(event)
        
        if event.type() == QEvent.WindowStateChange:
            is_os_maximized = self.windowState() & Qt.WindowMaximized
            
            if self.is_maximized != is_os_maximized:
                # Если состояние изменилось нативное (напр., двойной клик или drag к краю)
                self.is_maximized = is_os_maximized
                self.maximize_button.setText("❐" if self.is_maximized else "☐")
                
                # Обновление отступов
                new_margins = 0 if self.is_maximized else self.normal_margins
                self.content_layout.setContentsMargins(new_margins, new_margins, new_margins, new_margins) 
                
                # Если нативно развернули, сохраняем текущую геометрию как 'нормальную' (чтобы выйти из развернутого)
                if not self.is_maximized:
                     self.normal_geometry = self.geometry() 
            
            self.main_layout.activate()
            self.centralwidget.update()
            
            logger.info(f"Change event detected. WindowMaximized={is_os_maximized}")


    # --- ДИНАМИЧЕСКИЕ МЕТОДЫ (Без изменений) ---
    def clear_grid(self, clear_spacer=True):
        if not hasattr(self, 'grid_layout') or self.grid_layout is None:
            return
            
        if self.vertical_spacer and clear_spacer:
            try:
                self.grid_layout.removeItem(self.vertical_spacer)
                self.vertical_spacer.in_layout = False
            except:
                pass 

        temp_items = []
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.takeAt(i)
            temp_items.append(item)
        
        for item in temp_items:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            
        if clear_spacer:
            self.game_items = {}
            if self.vertical_spacer and clear_spacer:
                self.grid_layout.addItem(self.vertical_spacer, 999, 0, 1, 1)
                self.vertical_spacer.in_layout = True
            logger.debug("Сетка виджетов и кэш полностью очищены.")
        else:
            logger.debug("Сетка макета очищена, кэш game_items сохранен.")


    def apply_initial_styles(self):
        app = QCoreApplication.instance()
        apply_dark_theme(app)
        
        self.clear_grid(clear_spacer=True)
        
        if CURRENT_CONSOLE in self.console_buttons:
             self.console_buttons[CURRENT_CONSOLE].setChecked(True)
        
        self.update_ui_for_console(CURRENT_CONSOLE) 

        
if __name__ == "__main__":
    
    setup_logging()
    
    try:
        app = QApplication(sys.argv)
        
        if CURRENT_CONSOLE not in CONSOLE_SETTINGS:
            QMessageBox.critical(None, "Ошибка Конфигурации", 
                                 f"Начальная консоль '{CURRENT_CONSOLE}' не найдена в CONSOLE_SETTINGS.")
            sys.exit(1)
        
        launcher = LauncherApp()
        
        INITIAL_WIDTH = 780
        INITIAL_HEIGHT = 740
        
        # 🔴 ИСПРАВЛЕНИЕ 2: Удаляем ограничение минимального размера
        # launcher.setMinimumSize(INITIAL_WIDTH, INITIAL_HEIGHT)
        
        launcher.resize(INITIAL_WIDTH, INITIAL_HEIGHT)
        
        # 💡 ИСПРАВЛЕНИЕ 3: Сохраняем начальный размер в normal_geometry
        launcher.normal_geometry = launcher.geometry()
        
        launcher.show()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical("Критическая ошибка при запуске приложения:", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Приложение не может запуститься из-за ошибки: {e}")
        sys.exit(1)