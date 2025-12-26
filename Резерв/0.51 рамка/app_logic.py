# F:\User\project\Retro_HUB\app_logic.py
# ФИНАЛЬНЫЙ ИСПРАВЛЕННЫЙ КОД: Версия 0.51. Устранение артефактов скроллинга,
# возврат "Загрузка..." (34pt) и градиента.

import os
import logging
import math
import fnmatch

# 🟢 ОБНОВЛЕННЫЕ ИМПОРТЫ 
from PyQt5.QtWidgets import QMessageBox, QLabel, QGraphicsOpacityEffect, QWidget 
from PyQt5.QtCore import QTimer, Qt, QSize, QCoreApplication, QPropertyAnimation 

# --- ИМПОРТЫ ИЗ main_app.py (должны быть доступны) ---
from config import (
    CONSOLE_SETTINGS, CURRENT_CONSOLE, 
    ITEM_WIDTH, ITEM_HEIGHT, 
    ALLOWED_COVER_EXTENSIONS 
)
from threads import EmulatorMonitorThread, ImageLoaderThread, GameLoaderThread
from widgets import GameItem, DescriptionWindow, extract_short_info 

logger = logging.getLogger(__name__)

# 🔴 ОБНОВЛЕННАЯ ВЕРСИЯ
VERSION = "0.51"
VERSION_CHANGE_NOTE = "UI stability fix in QScrollArea (clipping/transparency issue resolved), added loading label, and improved performance."


# ----------------------------------------------------------------------
# КЛАСС AppLogicMixin (Смешиваемый класс для LauncherApp)
# ----------------------------------------------------------------------

class AppLogicMixin:
    """Содержит всю логику управления данными игр и сеткой."""
    
    def __init__(self, *args, **kwargs): 
        # Инициализация атрибутов, используемых в миксине
        super().__init__(*args, **kwargs)
        self.game_items = {} 
        self.console_buttons = {}
        # Инициализация путей, используемых в новых методах
        self.current_rom_path = None
        self.rom_extensions = []
        # 🟢 НОВЫЙ АТРИБУТ: Для сохранения ссылок на объекты анимации
        self.active_animations = [] 
        # 🟢 ДОБАВЛЕНО: Для метки загрузки
        self.loading_label = None 
        # 💡 КРИТИЧНО: Для сохранения полного списка ROM'ов
        self._all_roms_list = [] 
        
        # self.rom_list, self.game_loader_thread, self.threads 
        # инициализированы в main_app.py

    # ----------------------------------------------------------------------
    # МЕТОДЫ: update_rom_folder и load_roms (Вернули метку загрузки + 34pt)
    # ----------------------------------------------------------------------
    
    def update_rom_folder(self, console_key):
        """Обновляет путь к ROM'ам в зависимости от выбранной консоли."""
        
        settings = CONSOLE_SETTINGS.get(console_key, {})
        self.current_rom_path = settings.get("ROM_PATH") 
        self.rom_extensions = settings.get("ROM_EXTENSIONS", [])
        
        if not self.current_rom_path or not os.path.isdir(self.current_rom_path):
            logger.error(f"Папка ROM'ов не найдена для {console_key}: {self.current_rom_path}")
            self.layout_roms([]) 
        else:
            logger.info(f"Установлена папка ROM'ов для {console_key}: {self.current_rom_path}")


    def load_roms(self, apply_layout=True):
        """Запускает поток загрузки игр, который сканирует папку ROM'ов."""
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread and self.game_loader_thread.isRunning():
            self.game_loader_thread.requestInterruption()
            self.game_loader_thread.wait()
            
        if hasattr(self, 'clear_grid'): self.clear_grid() 
        
        if not self.current_rom_path:
             logger.warning("Путь к ROM'ам не установлен. Загрузка пропущена.")
             return
             
        # 🟢 ВОЗВРАТ: Отображаем индикатор загрузки
        if hasattr(self, 'grid_layout') and hasattr(self, 'grid_widget'):
            self.loading_label = QLabel("Загрузка...")
            self.loading_label.setObjectName("loadingLabel") 
            self.loading_label.setAlignment(Qt.AlignCenter)
            
            # 💡 НОВОЕ ИСПРАВЛЕНИЕ: Устанавливаем размер шрифта 34pt
            self.loading_label.setStyleSheet("QLabel#loadingLabel { font-size: 34pt; color: #CCCCCC; }")
            
            # Убедимся, что метка загрузки не была удалена (если осталась от предыдущего запуска)
            self.remove_all_non_spacer_items()

            if hasattr(self, 'num_cols'):
                 col_span = self.num_cols
            else:
                 col_span = 1
                 
            self.grid_layout.addWidget(self.loading_label, 0, 0, 1, col_span, Qt.AlignCenter)
            self.grid_widget.update() 
            logger.info("Отображена надпись 'Загрузка...' в центре сетки.")
            
        self.game_loader_thread = GameLoaderThread(
            self.current_rom_path, 
            self.rom_extensions, 
            ALLOWED_COVER_EXTENSIONS, 
            existing_roms=self._all_roms_list, 
            parent=self 
        )
        self.game_loader_thread.game_found.connect(self.handle_new_game_item)
        
        if apply_layout:
             self.game_loader_thread.finished_loading.connect(self.layout_roms)
             
        self.game_loader_thread.start()
        logger.info(f"Запущен поток загрузки игр для {CURRENT_CONSOLE}.")


    # ----------------------------------------------------------------------
    # МЕТОДЫ: switch_console, update_ui_for_console, apply_console_style, 
    #         update_console_buttons (Без изменений)
    # ----------------------------------------------------------------------
    def switch_console(self, console_key):
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

    def update_ui_for_console(self, console_key):
        if console_key not in CONSOLE_SETTINGS:
            logger.error(f"Неизвестный ключ консоли при обновлении UI: {console_key}")
            return
        logger.info(f"Обновление UI для консоли: {console_key}")
        self.apply_console_style()
        self.update_console_buttons()
        self.update_rom_folder(console_key) 
        self.load_roms() 
        if hasattr(self, 'search_input') and hasattr(self.search_input, 'clear'):
            self.search_input.clear()

    def apply_console_style(self):
        try:
            settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {})
            console_name = settings.get('NAME', CURRENT_CONSOLE)
            gradient_start = settings.get('GRADIENT_START', '#1e1e1e') 
            gradient_end = settings.get('GRADIENT_END', '#404040') 
            
            style_sheet = f"""
                QMainWindow {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                stop: 0 {gradient_start}, 
                                                stop: 1 {gradient_end}) !important;
                }}
                #centralwidget {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                stop: 0 {gradient_start}, 
                                                stop: 1 {gradient_end}) !important;
                    border-radius: 10px;
                }}
            """
            app = QCoreApplication.instance()
            app.setStyleSheet(app.styleSheet() + style_sheet)

            if hasattr(self, 'centralwidget') and self.centralwidget:
                self.centralwidget.style().polish(self.centralwidget)
                self.centralwidget.update()
            
            self.setWindowTitle(f"Retro Hub - {console_name}")
            logger.info(f"Стили консоли и градиент применены для: {console_name}")
            
        except Exception as e:
            logger.error(f"Ошибка при применении стилей консоли: {e}")
            
    def update_console_buttons(self):
        if not self.console_buttons:
            logger.warning("Атрибут 'self.console_buttons' не найден или пуст. Пропуск обновления кнопок консоли.")
            return

        try:
            for console_name, button in self.console_buttons.items():
                if console_name == CURRENT_CONSOLE:
                    button.setProperty("active", True)
                else:
                    button.setProperty("active", False)
                
                button.style().polish(button)
            
            logger.info("Кнопки консоли успешно обновлены.")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении кнопок консоли: {e}")
            
    def handle_new_game_item(self, game_data):
        """Создает и кэширует новый виджет GameItem и скрывает его."""
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
            self.grid_layout.addWidget(item_widget, 0, 0) 
            item_widget.setVisible(False) 
        
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
        
        logger.info(f"Создан и закэширован новый СКРЫТЫЙ виджет для: {folder_name}")


    # ----------------------------------------------------------------------
    # МЕТОД: layout_roms (ФИНАЛЬНЫЙ СТАБИЛЬНЫЙ КОД С ПРОЗРАЧНОСТЬЮ)
    # ----------------------------------------------------------------------
    def layout_roms(self, rom_list):
        
        if hasattr(self.game_loader_thread, 'isFinished') and self.game_loader_thread.isFinished():
            self._all_roms_list = rom_list 
        
        self.rom_list = rom_list 
        
        # 🟢 ВОЗВРАТ: Удаление индикатора загрузки
        if hasattr(self, 'loading_label') and self.loading_label:
            try:
                self.grid_layout.removeWidget(self.loading_label)
                self.loading_label.deleteLater()
                self.loading_label = None
                logger.debug("Индикатор 'Загрузка...' удален из сетки.")
            except Exception as e:
                logger.warning(f"Ошибка при удалении loading_label: {e}")
        
        # ----------------------------------------------------------------------
        # Логика обработки пустого списка
        # ----------------------------------------------------------------------
        if not self.rom_list:
            if hasattr(self, 'grid_layout'):
                for item in self.game_items.values():
                    item.setVisible(False)
                    
                message = QLabel(f"Игры для {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены.")
                message.setObjectName("emptyGridLabel")
                num_cols = getattr(self, 'num_cols', 1) 
                
                self.remove_all_non_spacer_items() 
                if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
                     try:
                         self.grid_layout.removeItem(self.vertical_spacer)
                     except:
                         pass
                    
                self.grid_layout.addWidget(message, 0, 0, 1, num_cols, Qt.AlignCenter)
                
                if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
                    self.grid_layout.addItem(self.vertical_spacer, 999, 0, 1, self.grid_layout.columnCount())
                    self.grid_layout.setRowStretch(999, 1) 
            return
            
        logger.info(f"Размещение {len(self.rom_list)} игр в сетке...")
        
        if not all(hasattr(self, attr) for attr in ['scroll_area', 'grid_layout', 'grid_widget']):
             logger.error("UI-элементы (scroll_area/grid_layout/grid_widget) недоступны.")
             return
            
        # 🔴 КРИТИЧЕСКИЙ БЛОК: Устранение артефактов и возврат градиента
        # 1. Убедимся, что непрозрачность (скрывающая градиент) отключена
        if self.grid_widget.testAttribute(Qt.WA_OpaquePaintEvent):
            self.grid_widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
        
        # 2. Явно устанавливаем прозрачность
        self.grid_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.grid_widget.setStyleSheet("background-color: transparent;")
        
        # ------------------------------------------------------------------

        scroll_area_width = self.grid_widget.width() if self.grid_widget.width() > 0 else self.scroll_area.viewport().width() 
        spacing = self.grid_layout.spacing()
        self.num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))
        
        row = 0
        col = 0
        
        # 🟢 ШАГ 1: ЗАМОРОЗКА обновления макета
        self.grid_widget.setUpdatesEnabled(False)
        self.scroll_area.setUpdatesEnabled(False)
        
        for item in self.game_items.values():
            item.setVisible(False) 

        self.remove_all_non_spacer_items()

        if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
            try:
                self.grid_layout.removeItem(self.vertical_spacer)
            except:
                pass


        # 🟢 Очистка и подготовка списка анимаций (без анимаций прозрачности)
        self.active_animations = [] 


        for rom_data in self.rom_list:
            folder_name = rom_data['FOLDER_NAME']
            
            if folder_name in self.game_items:
                game_item = self.game_items[folder_name]
                
                # Переназначение виджета на правильную позицию
                try:
                    self.grid_layout.removeWidget(game_item)
                except:
                    pass
                
                self.grid_layout.addWidget(game_item, row, col) 
                
                # Удаляем QGraphicsOpacityEffect, так как он вызывает артефакты
                game_item.setGraphicsEffect(None)
                
                # Показываем элемент
                game_item.setVisible(True) 
                
            else:
                logger.error(f"Виджет для '{folder_name}' отсутствует в кэше! Пропуск.")
                continue

            col += 1
            if col >= self.num_cols:
                col = 0
                row += 1
                
        # 🟢 ШАГ 3: ВОССТАНОВЛЕНИЕ ВЕРТИКАЛЬНОЙ РАСПОРКИ
        if hasattr(self, 'vertical_spacer') and self.vertical_spacer:
            spacer_row = row if col == 0 else row + 1 
            self.grid_layout.addItem(self.vertical_spacer, spacer_row, 0, 1, self.num_cols)
            self.grid_layout.setRowStretch(spacer_row, 1)

        # Настройка растяжения столбцов
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)
        if self.num_cols > 0:
            self.grid_layout.setColumnStretch(self.num_cols - 1, 1)

        # 🟢 ШАГ 4: РАЗМОРОЗКА и ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ
        self.grid_widget.setUpdatesEnabled(True)
        self.scroll_area.setUpdatesEnabled(True)
        
        self.grid_layout.invalidate()
        self.grid_widget.updateGeometry() 
        self.grid_widget.repaint()
        # Принудительная перерисовка viewports для устранения артефактов
        self.scroll_area.viewport().update()
        self.scroll_area.update()
        
        logger.info("Размещение завершено. Стабильность сетки сохранена, градиент возвращен.")

    def remove_all_non_spacer_items(self):
         """Удаляет все виджеты из макета (кроме GameItem и распорки), а также метку emptyGridLabel/loading_label."""
         if not hasattr(self, 'grid_layout'): return

         for i in reversed(range(self.grid_layout.count())):
             item = self.grid_layout.itemAt(i)
             if item is None: continue

             widget = item.widget()
             
             if widget:
                 if widget.objectName() in ["emptyGridLabel", "loadingLabel"]:
                     self.grid_layout.removeItem(item)
                     widget.setParent(None)
                     widget.deleteLater()
                 elif isinstance(widget, QWidget) and widget not in self.game_items.values():
                     self.grid_layout.removeItem(item)
                     widget.setParent(None)
                     widget.deleteLater()
             elif item.spacerItem():
                 continue

    # ----------------------------------------------------------------------
    # [ ... ОСТАЛЬНЫЕ МЕТОДЫ (Без изменений) ...]
    # ----------------------------------------------------------------------
    
    def handle_image_ready(self, game_item_widget, pixmap):
        game_item_widget.set_cover_pixmap(pixmap)
        
    def filter_roms(self, text):
        search_text = text.strip().lower()
        
        if not hasattr(self, '_all_roms_list') or not self._all_roms_list: 
            logger.warning("Полный список _all_roms_list недоступен для фильтрации.")
            return
        
        if not search_text:
            filtered_list = self._all_roms_list
        else:
            filtered_list = [
                game for game in self._all_roms_list 
                if search_text in game.get('title', '').lower()
            ]
            
        self.layout_roms(filtered_list)
        
        logger.info(f"Фильтрация по тексту '{text}' завершена. Показано {len(filtered_list)} игр.")

    def request_game_description(self, game_folder):
        if not hasattr(self, '_all_roms_list'): return
        
        game_data = next((game for game in self._all_roms_list if game.get('FOLDER_PATH') == game_folder), None)
        
        if game_data:
            full_html_content = self.load_full_html_content(game_data['FOLDER_PATH'])
            
            self.show_game_description(
                game_data['FOLDER_PATH'], 
                full_html_content, 
                game_data['screenshots']
            )
        else:
            logger.error(f"Данные для игры в папке {game_folder} не найдены.")
            QMessageBox.warning(self, "Информация", "Не удалось найти описание игры. Пожалуйста, убедитесь, что index.html существует.")

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
            )
            desc_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при отображении окна описания: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось отобразить подробное описание игры.")