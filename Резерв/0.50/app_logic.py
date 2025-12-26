# app_logic.py (ФРАГМЕНТЫ: Применен фикс градиента)

import os
import logging
import math
import fnmatch

from PyQt5.QtWidgets import QMessageBox, QLabel
from PyQt5.QtCore import QTimer, Qt, QSize
# 🟢 ДОБАВЛЕН ИМПОРТ QCoreApplication
from PyQt5.QtCore import QCoreApplication 

# --- ИМПОРТЫ ИЗ main_app.py (должны быть доступны) ---
from config import (
    CONSOLE_SETTINGS, CURRENT_CONSOLE, 
    ITEM_WIDTH, ITEM_HEIGHT, 
    ALLOWED_COVER_EXTENSIONS 
)
from threads import EmulatorMonitorThread, ImageLoaderThread, GameLoaderThread
from widgets import GameItem, DescriptionWindow, extract_short_info 

logger = logging.getLogger(__name__)

VERSION = "0.50"
VERSION_CHANGE_NOTE = "Optimization of game loading (caching). Added Console Selector to Search Bar."


# ----------------------------------------------------------------------
# КЛАСС AppLogicMixin (Смешиваемый класс для LauncherApp)
# ----------------------------------------------------------------------

class AppLogicMixin:
    """Содержит всю логику управления данными игр и сеткой."""
    
    def __init__(self, *args, **kwargs): 
        # Инициализация атрибутов, используемых в миксине
        super().__init__(*args, **kwargs)
        self.game_items = {} 
        self.console_buttons = {} # Используется в update_console_buttons
        # Инициализация путей, используемых в новых методах
        self.current_rom_path = None
        self.rom_extensions = []
        # self.rom_list, self.game_loader_thread, self.threads 
        # инициализированы в main_app.py

    # ----------------------------------------------------------------------
    # 🟢 ДОБАВЛЕНО: update_rom_folder и load_roms
    # ----------------------------------------------------------------------
    
    def update_rom_folder(self, console_key):
        """Обновляет путь к ROM'ам в зависимости от выбранной консоли."""
        
        settings = CONSOLE_SETTINGS.get(console_key, {})
        # Используем путь из CONSOLE_SETTINGS
        self.current_rom_path = settings.get("ROM_PATH") 
        self.rom_extensions = settings.get("ROM_EXTENSIONS", [])
        
        if not self.current_rom_path or not os.path.isdir(self.current_rom_path):
            logger.error(f"Папка ROM'ов не найдена для {console_key}: {self.current_rom_path}")
            # Очистить сетку, если путь недействителен
            self.layout_roms([]) 
        else:
            logger.info(f"Установлена папка ROM'ов для {console_key}: {self.current_rom_path}")


    def load_roms(self, apply_layout=True):
        """
        Запускает поток загрузки игр, который сканирует папку ROM'ов.
        Добавлен флаг apply_layout, чтобы избежать повторного вызова layout_roms
        при инициализации, если это не требуется.
        """
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread and self.game_loader_thread.isRunning():
            self.game_loader_thread.requestInterruption()
            self.game_loader_thread.wait()
            
        # 🟢 ВАЖНО: Вызов метода очистки сетки из main_app.py
        if hasattr(self, 'clear_grid'): self.clear_grid() 
        self.game_items = {}
        
        if not self.current_rom_path:
             logger.warning("Путь к ROM'ам не установлен. Загрузка пропущена.")
             return
            
        self.game_loader_thread = GameLoaderThread(
            self.current_rom_path, 
            self.rom_extensions, 
            ALLOWED_COVER_EXTENSIONS, 
            parent=self 
        )
        self.game_loader_thread.game_found.connect(self.handle_new_game_item)
        
        # 🟢 ИСПРАВЛЕНИЕ: Подключаем layout_roms только если он нужен
        if apply_layout:
             self.game_loader_thread.finished_loading.connect(self.layout_roms)
             
        self.game_loader_thread.start()
        logger.info(f"Запущен поток загрузки игр для {CURRENT_CONSOLE}.")


    # ----------------------------------------------------------------------
    # 🟢 МЕТОД: switch_console
    # ----------------------------------------------------------------------
    def switch_console(self, console_key):
        """
        Обрабатывает нажатие кнопки консоли: обновляет CURRENT_CONSOLE 
        и запускает полное обновление UI.
        """
        global CURRENT_CONSOLE
        
        if console_key not in CONSOLE_SETTINGS:
            logger.error(f"Попытка переключиться на неизвестную консоль: {console_key}")
            return
            
        if console_key == CURRENT_CONSOLE:
            logger.debug(f"Консоль {console_key} уже активна. Пропуск переключения.")
            return

        CURRENT_CONSOLE = console_key
        logger.info(f"Переключение на консоль: {CURRENT_CONSOLE}")

        self.update_ui_for_console(CURRENT_CONSOLE)

    # ----------------------------------------------------------------------
    # 🟢 МЕТОД: update_ui_for_console (АКТИВИРОВАНА ЗАГРУЗКА ИГР)
    # ----------------------------------------------------------------------
    def update_ui_for_console(self, console_key):
        """
        Главный метод, который обновляет весь UI для выбранной консоли.
        """
        
        if console_key not in CONSOLE_SETTINGS:
            logger.error(f"Неизвестный ключ консоли при обновлении UI: {console_key}")
            return
            
        logger.info(f"Обновление UI для консоли: {console_key}")
        
        # 1. Применение стилей (включая градиент)
        self.apply_console_style()
        
        # 2. Обновление кнопок
        self.update_console_buttons()
        
        # 3. Запуск загрузки ROM'ов
        self.update_rom_folder(console_key) 
        self.load_roms() 
        
        # 4. Сброс поиска
        if hasattr(self, 'search_input') and hasattr(self.search_input, 'clear'):
            self.search_input.clear()

    # ----------------------------------------------------------------------
    # 🟢 МЕТОД: apply_console_style (ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ДЛЯ ГРАДИЕНТА)
    # ----------------------------------------------------------------------
    def apply_console_style(self):
        """Применяет стили, специфичные для текущей консоли, включая динамический градиент."""
        try:
            settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {})
            console_name = settings.get('NAME', CURRENT_CONSOLE)
            
            # --- Настройка градиента ---
            # Получаем цвета из CONSOLE_SETTINGS. Если не найдены, используем дефолтные темные.
            gradient_start = settings.get('GRADIENT_START', '#1e1e1e') 
            gradient_end = settings.get('GRADIENT_END', '#404040') 
            
            # 🟢 QSS: Применяем градиент к QMainWindow и #centralwidget с !important
            style_sheet = f"""
                /* 💡 Теперь, когда в style.py нет конфликта, этот стиль должен сработать */
                QMainWindow {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 {gradient_start}, 
                                                stop: 1 {gradient_end}) !important;
                }}
                /* Применяем также к centralwidget, если QMainWindow сделан прозрачным */
                #centralwidget {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 {gradient_start}, 
                                                stop: 1 {gradient_end}) !important;
                    border-radius: 10px;
                }}
            """
            
            # Применяем стили.
            app = QCoreApplication.instance()
            app.setStyleSheet(app.styleSheet() + style_sheet)

            # 🟢 ДОПОЛНИТЕЛЬНЫЙ ШАГ: Принудительное обновление виджетов для применения стилей
            if hasattr(self, 'centralwidget') and self.centralwidget:
                self.centralwidget.style().polish(self.centralwidget)
                self.centralwidget.update()
            
            # Обновляем заголовок
            if hasattr(self, 'setWindowTitle'):
                 self.setWindowTitle(f"Retro Hub - {console_name}")
            
            logger.info(f"Стили консоли и градиент применены (с !important) для: {console_name} (Начало: {gradient_start}, Конец: {gradient_end})")
            
        except Exception as e:
            logger.error(f"Ошибка при применении стилей консоли: {e}")
            
    # ----------------------------------------------------------------------
    # 🟢 МЕТОД: update_console_buttons
    # ----------------------------------------------------------------------
    def update_console_buttons(self):
        """Обновляет внешний вид или состояние кнопок консолей/меню."""
        
        if not self.console_buttons:
            logger.warning("Атрибут 'self.console_buttons' не найден или пуст. Пропуск обновления кнопок консоли.")
            return

        try:
            for console_name, button in self.console_buttons.items():
                if console_name == CURRENT_CONSOLE:
                    button.setProperty("active", True)
                else:
                    button.setProperty("active", False)
                
                # Обеспечиваем перерисовку кнопки, чтобы применились QSS-свойства
                button.style().polish(button)
            
            logger.info("Кнопки консоли успешно обновлены.")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении кнопок консоли: {e}")
            
    # ----------------------------------------------------------------------
    # ОСТАЛЬНЫЕ МЕТОДЫ (Без изменений)
    # ----------------------------------------------------------------------

    def handle_new_game_item(self, game_data):
        """Создает и кэширует новый виджет GameItem."""
        if not hasattr(self, 'game_items'): self.game_items = {}
        folder_name = game_data['FOLDER_NAME']
        if folder_name in self.game_items:
            logger.debug(f"Виджет для {folder_name} уже существует в кэше UI. Пропуск.")
            return

        short_description = extract_short_info(game_data['description'])
        
        item_widget = GameItem(
            game_folder=game_data['FOLDER_PATH'], 
            rom_path=game_data['FULL_ROM_PATH'],
            description=short_description, 
            item_width=ITEM_WIDTH,      
            item_height=ITEM_HEIGHT,
            screenshots=game_data['screenshots']
        )
        item_widget.game_launched.connect(self.launch_game)
        item_widget.show_description_requested.connect(self.request_game_description)
        
        self.game_items[folder_name] = item_widget
        
        if hasattr(self, 'grid_layout'):
            # Виджеты добавляются в поток, но на этом этапе grid_layout должен быть создан.
            # Мы просто добавляем их в (0,0) на время, пока не будет вызван layout_roms
            # layout_roms переназначит их в правильные места.
            self.grid_layout.addWidget(item_widget, 0, 0) 
        
        loader = ImageLoaderThread(
            game_data['FOLDER_PATH'], 
            item_widget, 
            ALLOWED_COVER_EXTENSIONS, 
            parent=self 
        )
        if not hasattr(self, 'threads'): self.threads = []
        loader.image_ready.connect(self.handle_image_ready)
        self.threads.append(loader)
        loader.start()
        
        logger.info(f"Создан и закэширован новый виджет для: {folder_name}")


    def layout_roms(self, rom_list):
        self.rom_list = rom_list
        
        if not self.rom_list:
            # Сетка должна быть очищена в load_roms() или switch_console()
            
            if hasattr(self, 'grid_layout'):
                message = QLabel(f"Игры для {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены.")
                message.setObjectName("emptyGridLabel")
                # Убедимся, что num_cols известен
                num_cols = getattr(self, 'num_cols', 1) 
                
                # 🟢 ИСПРАВЛЕНИЕ: Перед добавлением QLabel, удаляем вертикальную распорку,
                # если она есть, чтобы QLabel стал единственным элементом.
                if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
                    self.grid_layout.removeItem(self.vertical_spacer)
                    
                self.grid_layout.addWidget(message, 0, 0, 1, num_cols, Qt.AlignCenter)
                
                # Опционально: восстанавливаем распорку, если она нужна
                if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
                    self.grid_layout.addItem(self.vertical_spacer, 999, 0, 1, self.grid_layout.columnCount())
                    
                # 💡 Предупреждение пользователю (в идеале нужно отображать только один раз)
                # QMessageBox.information(self, "Информация", f"Игры для консоли {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены.")
            return
            
        logger.info(f"Размещение {len(self.rom_list)} игр в сетке...")
        
        # 💡 Убедимся, что self.scroll_area и self.grid_layout доступны
        if not hasattr(self, 'scroll_area') or not hasattr(self, 'grid_layout'):
             logger.error("UI-элементы (scroll_area/grid_layout) недоступны для размещения ROM'ов.")
             return
            
        scroll_area_width = self.scroll_area.viewport().width() 
        spacing = self.grid_layout.spacing()
        # Гарантируем, что num_cols не меньше 1
        self.num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))
        
        row = 0
        col = 0
        
        # 🟢 ИСПРАВЛЕНИЕ: Удаляем временный QLabel, если он был
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() == "emptyGridLabel":
                widget.setParent(None)
                widget.deleteLater()
        
        
        # 🟢 ИСПРАВЛЕНИЕ: Перед добавлением виджетов, удаляем вертикальную распорку, 
        # чтобы она была добавлена в конце, после последнего элемента
        if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
            self.grid_layout.removeItem(self.vertical_spacer)

        
        for rom_data in self.rom_list:
            folder_name = rom_data['FOLDER_NAME']
            
            if folder_name in self.game_items:
                game_item = self.game_items[folder_name]
                
                # Защита от повторного добавления (хотя clear_grid должен был сработать)
                try:
                    self.grid_layout.removeWidget(game_item)
                except:
                    pass
                
                self.grid_layout.addWidget(game_item, row, col) 
                game_item.show() 
                
            else:
                logger.error(f"Виджет для '{folder_name}' отсутствует в кэше! Пропуск.")
                continue

            col += 1
            if col >= self.num_cols:
                col = 0
                row += 1
                
        # 🟢 ВОССТАНОВЛЕНИЕ ВЕРТИКАЛЬНОЙ РАСПОРКИ (обязательно после добавления всех виджетов)
        if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
            self.grid_layout.addItem(self.vertical_spacer, row, 0, 1, self.num_cols, Qt.AlignTop)


        # Настройка растяжения столбцов
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)
        if self.num_cols > 0:
            # Растягиваем последний столбец, чтобы центрировать сетку
            self.grid_layout.setColumnStretch(self.num_cols - 1, 1)

        logger.info("Размещение завершено.")


    def handle_image_ready(self, game_item_widget, pixmap):
        game_item_widget.set_cover_pixmap(pixmap)
        
    def populate_grid(self, roms):
        pass

    def filter_roms(self, text):
        search_text = text.lower()
        if not hasattr(self, 'rom_list') or not self.rom_list: 
            return
        
        for folder_name, item_widget in self.game_items.items():
            game_data = next((game for game in self.rom_list if game.get('FOLDER_NAME') == folder_name), None)
            
            if not game_data:
                item_widget.hide()
                continue
            
            game_title = game_data.get('title', folder_name)

            if not search_text or search_text in game_title.lower():
                item_widget.show()
            else:
                item_widget.hide()
                
        logger.info(f"Фильтрация по тексту '{text}' завершена.")


    def request_game_description(self, game_folder):
        if not hasattr(self, 'rom_list'): return
        
        game_data = next((game for game in self.rom_list if game.get('FOLDER_PATH') == game_folder), None)
        
        if game_data:
            full_html_content = self.load_full_html_content(game_data['FOLDER_PATH'])
            
            # Используем сохраненный HTML-шаблон для окна описания
            self.show_game_description(
                game_data['FOLDER_PATH'], 
                full_html_content, 
                game_data['screenshots']
            )
        else:
            logger.error(f"Данные для игры в папке {game_folder} не найдены.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти описание игры. Пожалуйста, убедитесь, что index.html существует.")

    def load_full_html_content(self, game_folder_path):
        html_path = os.path.join(game_folder_path, "index.html")
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content
            except Exception as e:
                logger.error(f"Ошибка чтения полного HTML для {game_folder_path}: {e}")
        return "<h1>Ошибка загрузки описания</h1><p>Полный файл index.html не найден или не может быть прочитан.</p>"

    
    def show_launcher(self):
        self.showNormal() 
        self.activateWindow() 
        logger.info("Главное окно лаунчера восстановлено.")

    def launch_game(self, rom_path):
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
            self.emulator_thread.emulator_closed.connect(self.show_launcher) 
            self.emulator_thread.start()
            
            self.showMinimized() 
            logger.info(f"Игра {os.path.basename(os.path.dirname(rom_path))} запущена.")
            
        except Exception:
            logger.error("Не удалось запустить процесс эмулятора:", exc_info=True)
            QMessageBox.critical(self, "Ошибка Запуска", "Не удалось запустить процесс эмулятора.")
            
    def show_game_description(self, game_folder, description, screenshots):
        try:
            desc_window = DescriptionWindow(
                game_folder, 
                description, 
                screenshots, 
                parent=self,
                # 💡 ИСПОЛЬЗУЕМ СОХРАНЕННЫЙ HTML-ШАБЛОН ДЛЯ ОПИСАНИЯ
                # Здесь может быть логика для загрузки шаблона, если DescriptionWindow его использует
            )
            desc_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при отображении окна описания: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось отобразить подробное описание игры.")