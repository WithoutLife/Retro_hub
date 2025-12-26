# main_app.py

import sys
import os
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
    QHBoxLayout, QFrame, QScrollArea, QGridLayout, QMessageBox, QLineEdit,
    QDialog 
) 
from PyQt5.QtGui import QPixmap, QIcon, QRegion, QPainterPath, QFont
from PyQt5.QtCore import QSize, Qt, QPoint, QTimer, QRectF

# --- КРИТИЧЕСКИ ВАЖНЫЕ ИМПОРТЫ ---
from config import *
from style import apply_dark_theme 
from threads import EmulatorMonitorThread, ImageLoaderThread, GameLoaderThread 
from widgets import GameItem, DescriptionWindow, extract_short_info 

import resources_rc

from app_logic import AppLogicMixin
from window_events import WindowEventsMixin


logger = logging.getLogger(__name__) 

VERSION = "0.28" 
# 🚨 ИСПОЛЬЗУЕМ ЭТО НАЗВАНИЕ ВЕРСИИ ДЛЯ ФУТЕРА
VERSION_CHANGE_NOTE = "Full Description, Tooltip Fix & Footer Info" 

def setup_logging():
    """Настраивает базовое логирование и создает лог-файл."""
    log_file_path = os.path.join(BASE_DIR, 'retro_hub.log')
    
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s: %(message)s',
                        handlers=[
                            logging.StreamHandler(sys.stdout),
                            logging.FileHandler(log_file_path, encoding='utf-8')
                        ])
    logger.info(f"==========================================")
    logger.info(f"=== Retro HUB v {VERSION} ({VERSION_CHANGE_NOTE}) ===")
    logger.info(f"==========================================")


# ----------------------------------------------------------------------
# ГЛАВНЫЙ КЛАСС ОКНА
# ----------------------------------------------------------------------
class LauncherApp(WindowEventsMixin, QMainWindow, AppLogicMixin): 
    
    def __init__(self):
        super().__init__() 
        
        self.setWindowFlags(Qt.FramelessWindowHint) 
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"Retro HUB v{VERSION}") 
        
        MIN_WIDTH = ITEM_WIDTH + 20 
        MIN_HEIGHT = 55 + 55 + ITEM_HEIGHT + 15 + 20 
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT) 
        self.resize(START_WIDTH, START_HEIGHT)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(QVBoxLayout(self.central_widget))
        self.central_widget.setObjectName("centralwidget")
        
        self.title_bar = QWidget()
        self.minimize_button = QPushButton("—")
        self.maximize_button = QPushButton("☐")
        self.close_button = QPushButton("✕")
        self.dendy_button = QPushButton("Dendy")
        self.sega_button = QPushButton("Sega")
        self.sony_button = QPushButton("Sony")
        
        self.footer_widget = QWidget() 
        self.lineEdit = QLineEdit() 
        
        self.init_ui_elements() 
        self.setup_footer() 
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft) 
        self.grid_layout.setSpacing(15) 
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.grid_widget)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("gameScrollArea")

        self.rom_list = [] 
        self.threads = []  
        self.emulator_thread = None 
        self.game_loader_thread = None 
        self.num_cols = 0 
        
        self.resizing = False
        self.drag_offset = QPoint()
        
        self.setup_main_layout() 
        
        self.lineEdit.textChanged.connect(self.filter_roms) 
        
        self.set_rounded_window_mask(radius=10)
        self._set_window_icon()
        
        QTimer.singleShot(0, lambda: self.update_ui_for_console(CURRENT_CONSOLE))
        QTimer.singleShot(200, self.force_grid_redraw) 

    # ----------------------------------------------------------------------
    # МЕТОДЫ UI И СТИЛИ
    # ----------------------------------------------------------------------
    
    def setup_footer(self):
        """Настраивает виджет с информацией о версии."""
        self.footer_widget.setObjectName("footerWidget")
        self.footer_widget.setFixedHeight(25)
        
        footer_layout = QHBoxLayout(self.footer_widget)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setSpacing(10)
        
        # 🚨 ОБНОВЛЕННАЯ Подпись версии (с англ. названием последнего изменения)
        version_info = f"Retro HUB Ver {VERSION} ({VERSION_CHANGE_NOTE})"
        version_label = QLabel(version_info)
        version_label.setObjectName("footerLabel")
        
        # 🚨 ОБНОВЛЕННАЯ Подпись автора и года
        creator_label = QLabel("© 2025, Developed by No_fate")
        creator_label.setObjectName("footerLabel")
        
        footer_layout.addWidget(version_label)
        footer_layout.addStretch(1)
        footer_layout.addWidget(creator_label)
        
    def _set_window_icon(self):
        self.setWindowIcon(QIcon(":/launcher_icon.ico")) 

    def apply_icon_buttons_styles(self):
        style = """
        QPushButton {
            background-color: transparent;
            border: none;
            color: #FFFFFF;
            font-weight: bold;
            font-size: 14pt;
            min-width: 30px;
            min-height: 30px;
        }
        QPushButton:hover {
            background-color: #555555;
        }
        QPushButton#closeButton:hover {
            background-color: #FF4444; 
        }
        """
        self.minimize_button.setStyleSheet(style)
        self.maximize_button.setStyleSheet(style)
        self.close_button.setStyleSheet(style)
        self.close_button.setObjectName("closeButton")

    def init_ui_elements(self):
        
        self.title_bar.setObjectName("titleBar")
        
        self.dendy_button.setObjectName("consoleButton")
        self.dendy_button.clicked.connect(lambda: self.switch_console("DENDY"))
        
        self.sega_button.setObjectName("consoleButton")
        self.sega_button.clicked.connect(lambda: self.switch_console("SEGA"))
        
        self.sony_button.setObjectName("consoleButton")
        self.sony_button.clicked.connect(lambda: self.switch_console("SONY"))
        
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximized) 
        self.close_button.clicked.connect(self.close)
        
        self.apply_icon_buttons_styles()
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 0, 5, 0)
        
        logo_label = QLabel("Retro HUB")
        logo_label.setObjectName("logoLabel")
        
        font = QFont("Arial", 12)
        font.setBold(True)
        logo_label.setFont(font)
        
        title_layout.addWidget(logo_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.maximize_button)
        title_layout.addWidget(self.close_button)
        
    def setup_main_layout(self):
        main_layout = self.centralWidget().layout()
        
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 10, 10, 10) 
        search_layout.setSpacing(10)

        self.lineEdit.setObjectName("searchLineEdit")
        
        search_layout.addWidget(self.dendy_button)
        search_layout.addWidget(self.sega_button)
        search_layout.addWidget(self.sony_button)
        search_layout.addStretch(1) 
        search_layout.addWidget(self.lineEdit)
        
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(search_container) 
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(self.footer_widget) 
        
    def _get_console_stylesheet(self, console_color, black_color):
        """Формирует QSS для фона и кнопок консолей на основе текущего градиента."""
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
        button_style = f"""
        QPushButton#consoleButton {{
            background-color: #333333;
            border: 1px solid #555555;
            padding: 5px 15px;
            border-radius: 4px;
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton#consoleButton:hover {{
            background-color: #555555;
        }}
        /* Стиль для активной кнопки */
        QPushButton#consoleButton[class="active"] {{
            background-color: {gradient_end_color};
            border: 1px solid #FFFFFF;
            color: #FFFFFF;
        }}
        """
        # 🚨 НОВЫЙ СТИЛЬ ФУТЕРА: Темный фон и стиль текста
        footer_widget_style = """
        QWidget#footerWidget {
            background-color: #101010; /* Темный фон для футера */
            border-top: 1px solid #333333; /* Небольшая граница для разделения */
        }
        QLabel#footerLabel {
            color: #AAAAAA;
            font-size: 8pt;
        }
        """
        return gradient_style + button_style + footer_widget_style

    def update_ui_for_console(self, console_key):
        """
        Обновляет UI-параметры (градиент, стили кнопок) после смены консоли.
        Этот метод вызывается из AppLogicMixin.switch_console.
        """
        
        settings = CONSOLE_SETTINGS[console_key]
        
        # 1. Обновление стиля фона
        apply_dark_theme(QApplication.instance()) 
        style = self._get_console_stylesheet(settings["GRADIENT_END"], settings["GRADIENT_START"])
        self.centralWidget().setStyleSheet(style) 
        
        # 2. Обновление стиля кнопок
        buttons = {
            "DENDY": self.dendy_button,
            "SEGA": self.sega_button,
            "SONY": self.sony_button,
        }
        
        for key, button in buttons.items():
            if key == console_key:
                button.setProperty("class", "active")
            else:
                button.setProperty("class", "")
            
            button.style().polish(button)
            
        # 3. Загрузка ROM'ов только если это инициализация (первый запуск)
        if not self.rom_list:
            self.load_roms()


    def show_launcher(self):
        self.emulator_thread = None 
        self.setWindowState(Qt.WindowNoState)
        self.showNormal() 
        self.maximize_button.setText("☐")
        if self.rom_list:
            self.populate_grid(self.rom_list) 
            logger.info("Сетка игр обновлена после закрытия эмулятора.")
            
    def showMinimized(self):
        self.setWindowState(Qt.WindowMinimized)
        super().showMinimized()
        
    def force_grid_redraw(self):
        self.resizeEvent(None) 

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if not self.isMaximized(): 
            self.set_rounded_window_mask(radius=10)
        else:
            self.setMask(QRegion()) 
        
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