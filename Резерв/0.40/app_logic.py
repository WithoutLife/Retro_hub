# app_logic.py (ИСПРАВЛЕННЫЙ КОД)

import os
import logging
import math
import fnmatch

from PyQt5.QtWidgets import QMessageBox, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap

# --- ИМПОРТЫ ИЗ main_app.py (должны быть доступны) ---
from config import (
    CONSOLE_SETTINGS, CURRENT_CONSOLE, 
    ITEM_WIDTH, ITEM_HEIGHT, 
    ALLOWED_COVER_EXTENSIONS
)
from threads import ImageLoaderThread, GameLoaderThread, EmulatorMonitorThread
from widgets import GameItem, DescriptionWindow, extract_short_info 

logger = logging.getLogger(__name__)

VERSION = "0.40" 
VERSION_CHANGE_NOTE = "Console buttons moved to search bar. Action bar removed." 


# ----------------------------------------------------------------------
# КЛАСС AppLogicMixin (Смешиваемый класс для LauncherApp)
# ----------------------------------------------------------------------

class AppLogicMixin:
    """Содержит всю логику управления данными игр и сеткой."""
    
    def _debug_switch_console(self, new_console):
        logger.info(f"--- 📞 КЛИКНУТА КНОПКА: {new_console} ---")
        self.switch_console(new_console)
        
    def _find_console_button(self, console_name):
        """Вспомогательный метод для поиска кнопки консоли по имени."""
        buttons = {
            "DENDY": self.dendy_button,
            "SEGA": self.sega_button,
            "SONY": self.sony_button,
        }
        return buttons.get(console_name)
        
    def switch_console(self, new_console):
        """
        Переключает текущую консоль и обновляет UI.
        """
        # 🟢 ИСПРАВЛЕНО: Удалили "from config import CURRENT_CONSOLE"
        global CURRENT_CONSOLE
            
        # Теперь CURRENT_CONSOLE гарантированно содержит актуальное значение, 
        # установленное при последнем переключении консоли.
        if CURRENT_CONSOLE == new_console:
            logger.info(f"Консоль {new_console} уже активна. Сброса не требуется.")
            return
            
        logger.info(f"    -> НАЧАЛО ПЕРЕКЛЮЧЕНИЯ: Текущая: {CURRENT_CONSOLE}, Новая: {new_console}.")
        
        self.cleanup_threads()
        
        # 🟢 Критический шаг: Снимаем checked-состояние с текущей (для надежности)
        old_button = self._find_console_button(CURRENT_CONSOLE)
        if old_button:
            old_button.setChecked(False)

        CURRENT_CONSOLE = new_console # <-- Обновляем глобальную переменную
        
        # 🟢 Критический шаг: Устанавливаем checked-состояние для новой консоли
        new_button = self._find_console_button(CURRENT_CONSOLE)
        if new_button:
            new_button.setChecked(True)
        
        # Применяем новые стили (градиент)
        self.apply_console_style()
        
        # Обновляем футер 
        self.update_footer_info()
        
        logger.info(f"    -> ПЕРЕКЛЮЧЕНИЕ ЗАВЕРШЕНО. Новая активная консоль: {CURRENT_CONSOLE}")
        
        # Запускаем обновление UI через QTimer для гарантии, что стили применились
        QTimer.singleShot(10, lambda: self.update_ui_for_console(new_console))

    def update_footer_info(self): # Переименовал, так как кнопки уже не обновляются здесь
        """Обновляет информацию в футере."""
        from config import CURRENT_CONSOLE
        
        # 🟢 ИСПРАВЛЕНИЕ ФУТЕРА: Формируем полный текст с нужными данными и текущей консолью
        if hasattr(self, 'version_label') and hasattr(self, 'creator_label'):
            
            # Мы используем два QLabel в QHBoxLayout, поэтому просто обновляем их текст
            version_info = f"Retro HUB Ver {VERSION} ({VERSION_CHANGE_NOTE})"
            creator_info = f"© 2025, Developed by No_fate" 
            
            # Обновляем текст, используя QLabel.setText (так как layout управляет растяжкой)
            self.version_label.setText(version_info)
            self.creator_label.setText(creator_info)


    def update_console_buttons(self):
        """
        🟢 УПРОЩЕНО: Теперь этот метод только обеспечивает, что checked-состояние соответствует CURRENT_CONSOLE.
        Снята лишняя перерисовка стиля.
        """
        from config import CURRENT_CONSOLE
        
        logger.info("    -> ОБНОВЛЕНИЕ КНОПОК: Проверка состояния.")
        for name, button in {
            "DENDY": self.dendy_button,
            "SEGA": self.sega_button,
            "SONY": self.sony_button,
        }.items():
            
            # Устанавливаем checked-состояние
            is_active = (name == CURRENT_CONSOLE)
            if button.isChecked() != is_active:
                button.setChecked(is_active)
                logger.info(f"        -> Установлено: {name}.checked = {is_active}")
                
            # 🔴 УДАЛЕНО: button.style().unpolish(button) и polish(button)

    # 🔴 ФИКС ГРАДИЕНТА: Реализуем метод, который динамически применяет градиентный фон.
    def apply_console_style(self):
        """Применяет специфичный для текущей консоли диагональный градиентный фон к QScrollArea."""
        try:
            settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, CONSOLE_SETTINGS['DENDY'])
            
            GRADIENT_START = settings.get("GRADIENT_START", "#101018")
            GRADIENT_END = settings.get("GRADIENT_END", "#200035")
            
            # Изменено: x1:0, y1:0 (левый верх) -> x2:1, y2:1 (правый низ) для диагонали
            gradient_qss = f"""
                QScrollArea#gameScrollArea {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, 
                                                stop: 0 {GRADIENT_START}, 
                                                stop: 1 {GRADIENT_END});
                    border: none;
                }}
            """
            
            if hasattr(self, 'scroll_area'):
                self.scroll_area.setStyleSheet(gradient_qss)
                logger.info(f"Применен диагональный стиль консоли: {CURRENT_CONSOLE} с градиентом.")
            else:
                logger.warning("scroll_area не найден. Градиент не применен.")
                
        except Exception:
            logger.error("Ошибка при применении стиля консоли:", exc_info=True)


    def update_ui_for_console(self, console_name):
        """Обновляет заголовок и запускает загрузку ROM'ов."""
        settings = CONSOLE_SETTINGS.get(console_name, {})
        console_name_display = settings.get("NAME", console_name)
        
        # Используем локальную константу VERSION для заголовка
        self.setWindowTitle(f"Retro HUB v{VERSION} - {console_name_display}")
        self.load_roms()

    def cleanup_threads(self):
        """Останавливает и очищает все активные потоки загрузки изображений и метаданных."""
        logger.info("Очистка потоков...")
        if hasattr(self, 'threads'):
            for thread in self.threads:
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
            self.threads = []
        
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread is not None and self.game_loader_thread.isRunning():
             self.game_loader_thread.quit()
             self.game_loader_thread.wait()

    def clear_grid(self):
        """Полностью очищает QGridLayout от всех виджетов."""
        if hasattr(self, 'grid_layout'):
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
    def load_roms(self, text=None):
        """
        Запускает GameLoaderThread для асинхронного сканирования диска и парсинга метаданных.
        """ 
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread is not None and self.game_loader_thread.isRunning():
            logger.warning("Отмена предыдущей загрузки метаданных.")
            self.game_loader_thread.quit()
            self.game_loader_thread.wait()
            
        self.cleanup_threads() 
        self.clear_grid() 
        
        settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}) 
        folder = settings.get("ROOT_FOLDER") 
        extensions = settings.get("ROM_EXTENSIONS")
        
        if not folder or not extensions:
            logger.error(f"Параметры для консоли {CURRENT_CONSOLE} не найдены.")
            return
            
        if not os.path.isdir(folder):
            logger.error(f"Корневая папка не найдена: {folder}")
            # Отображаем сообщение об ошибке
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Корневая папка для {settings.get('NAME', CURRENT_CONSOLE)} не найдена по пути: {folder}"
            )
            self.clear_grid()
            message = QLabel(f"Папка {settings.get('NAME', CURRENT_CONSOLE)} не найдена.")
            message.setObjectName("emptyGridLabel")
            self.grid_layout.addWidget(message, 0, 0, Qt.AlignCenter)
            return

        logger.info(f"Начало загрузки ROM'ов для {CURRENT_CONSOLE} из папки: {folder}")
        
        # Запускаем поток загрузки игр
        self.game_loader_thread = GameLoaderThread(folder, extensions, parent=self)
        self.game_loader_thread.data_loaded.connect(self.handle_roms_loaded)
        self.game_loader_thread.start()

    def handle_roms_loaded(self, rom_data):
        """Обрабатывает полученные данные ROM'ов."""
        self.rom_list = rom_data
        
        if not self.rom_list:
            QMessageBox.information(
                self, 
                "Информация", 
                f"Игры для консоли {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены."
            )
            self.clear_grid()
            message = QLabel(f"Игры для {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены.")
            message.setObjectName("emptyGridLabel")
            self.grid_layout.addWidget(message, 0, 0, Qt.AlignCenter)
            return
            
        logger.info(f"Найдено {len(self.rom_list)} игр. Заполнение сетки.")
        self.populate_grid(self.rom_list)

    def handle_image_ready(self, game_item_widget, pixmap):
        """Обновляет изображение на виджете игры после загрузки."""
        game_item_widget.set_cover_pixmap(pixmap)
        
    def populate_grid(self, roms):
        """Заполняет сетку объектами GameItem на основе списка ROM'ов."""
        self.clear_grid()
        self.cleanup_threads()
        
        if not roms:
            return

        # Пересчет колонок (логика из main_app.py:resizeEvent)
        # Убедитесь, что self.scroll_area и self.grid_layout доступны.
        if not hasattr(self, 'scroll_area') or not hasattr(self, 'grid_layout'):
            logger.error("Виджеты сетки не инициализированы.")
            return

        scroll_area_width = self.scroll_area.viewport().width() 
        spacing = self.grid_layout.spacing()
        self.num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))
        
        for index, game_data in enumerate(roms):
            row = index // self.num_cols
            col = index % self.num_cols
            
            short_description = extract_short_info(game_data['description'])
            
            item_widget = GameItem(
                game_folder=game_data['folder'], 
                rom_path=game_data['rom'],
                description=short_description, 
                item_width=ITEM_WIDTH,      
                item_height=ITEM_HEIGHT,
                screenshots=game_data['screenshots']
            )
            item_widget.game_launched.connect(self.launch_game)
            item_widget.show_description_requested.connect(self.request_game_description)
            
            self.grid_layout.addWidget(item_widget, row, col)
            
            # Запуск потока загрузки изображения
            # 🟢 ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: Удаляем item_widget.image_label.size(), чтобы передать 4 аргумента.
            loader = ImageLoaderThread(
                game_data['folder'],                               # Позиционный #1: Path (str)
                item_widget,                                       # Позиционный #2: Widget (GameItem)
                ALLOWED_COVER_EXTENSIONS,                          # Позиционный #3: Extensions
                self                                               # Позиционный #4: Parent
            )
            if not hasattr(self, 'threads'):
                self.threads = []
            loader.image_ready.connect(self.handle_image_ready)
            self.threads.append(loader)
            loader.start()
        
        # Настройка растяжения колонок
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)
        if self.num_cols > 0:
            self.grid_layout.setColumnStretch(self.num_cols - 1, 1)
            
    def request_game_description(self, game_folder):
        """
        Находит полные данные игры по папке и вызывает DescriptionWindow.
        """
        if not hasattr(self, 'rom_list'): return
        
        game_data = next((game for game in self.rom_list if game['folder'] == game_folder), None)
        
        if game_data:
            full_html_content = self.load_full_html_content(game_data['folder'])
            
            # Используем сохраненный HTML-шаблон для окна описания
            self.show_game_description(
                game_data['folder'], 
                full_html_content, 
                game_data['screenshots']
            )
        else:
            logger.error(f"Данные для игры в папке {game_folder} не найдены.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти описание игры. Пожалуйста, убедитесь, что index.html существует.")

    def load_full_html_content(self, game_folder_path):
        """Читает весь файл index.html."""
        html_path = os.path.join(game_folder_path, "index.html")
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Ошибка чтения полного HTML для {game_folder_path}: {e}")
        return "<h1>Ошибка загрузки описания</h1><p>Полный файл index.html не найден или не может быть прочитан.</p>"
            
    def filter_roms(self, text):
        """Фильтрует игры и обновляет сетку."""
        search_text = text.lower()
        if not hasattr(self, 'rom_list') or not self.rom_list: 
            return
        
        if not search_text:
            filtered_list = self.rom_list
        else:
            filtered_list = [
                game for game in self.rom_list 
                if search_text in game['title'].lower()
            ]
        
        self.populate_grid(filtered_list)

    # ----------------------------------------------------------------------
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: МЕТОД show_launcher
    # ----------------------------------------------------------------------
    def show_launcher(self):
        """Восстанавливает главное окно после закрытия эмулятора."""
        # showNormal() гарантирует, что окно будет показано, даже если оно было свернуто.
        self.showNormal() 
        # Дополнительно: активируем окно, перенося его на передний план
        self.activateWindow() 
        logger.info("Главное окно лаунчера восстановлено.")

    def launch_game(self, rom_path):
        """Запускается по двойному клику."""
        if hasattr(self, 'emulator_thread') and self.emulator_thread and self.emulator_thread.isRunning():
            logger.warning("Эмулятор уже запущен. Игнорирование запроса на запуск.")
            return

        settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {})
        EMULATOR_PATH = settings.get("EMULATOR_PATH") 
        
        if not os.path.exists(EMULATOR_PATH):
            QMessageBox.critical(self, "Ошибка Запуска", f"Эмулятор {settings.get('NAME', 'Консоли')} не найден по пути: {EMULATOR_PATH}")
            logger.error(f"Эмулятор не найден: {EMULATOR_PATH}")
            return
            
        try:
            fullscreen_arg = settings.get('FULLSCREEN_ARG')
            
            self.emulator_thread = EmulatorMonitorThread(EMULATOR_PATH, rom_path, fullscreen_arg, parent=self)
            # Подключение к новому методу
            self.emulator_thread.emulator_closed.connect(self.show_launcher) 
            self.emulator_thread.start()
            
            self.showMinimized() 
            logger.info(f"Игра {os.path.basename(os.path.dirname(rom_path))} запущена.")
            
        except Exception:
            logger.error("Не удалось запустить процесс эмулятора:", exc_info=True)
            QMessageBox.critical(self, "Ошибка Запуска", "Не удалось запустить процесс эмулятора.")
            
    def show_game_description(self, game_folder, description, screenshots):
        """Отображает кастомное окно с подробным описанием игры."""
        try:
            desc_window = DescriptionWindow(
                game_folder, 
                description, 
                screenshots, 
                parent=self
            )
            desc_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при отображении окна описания: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось отобразить подробное описание игры.")