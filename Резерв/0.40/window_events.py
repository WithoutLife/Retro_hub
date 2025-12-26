# window_events.py (ФИНАЛЬНЫЙ ИСПРАВЛЕННЫЙ КОД ДЛЯ RESIZE)

import logging
from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QPainterPath, QRegion, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QDesktopWidget, QPushButton 
from PyQt5.QtCore import QRectF # Явно импортируем QRectF

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# КЛАСС WindowEventsMixin 
# ----------------------------------------------------------------------

class WindowEventsMixin:
    """Содержит все обработчики событий для кастомного окна (перетаскивание, изменение размера, закрытие)."""
    
    RESIZE_BORDER_WIDTH = 5 
    
    def __init__(self, *args, **kwargs):
        """
        Инициализация переменных с кооперативным super().__init__.
        """
        super().__init__(*args, **kwargs) 
        
        self.dragging = False
        self.drag_position = QPoint()
        self.resizing = False
        self.resize_edge = None

    # --- Вспомогательные методы для границ и курсора ---
    
    def _get_cursor_from_edge(self, edge):
        """Возвращает соответствующую форму курсора для края."""
        if edge in (Qt.TopEdge, Qt.BottomEdge): 
            return Qt.SizeVerCursor
        if edge in (Qt.LeftEdge, Qt.RightEdge): 
            return Qt.SizeHorCursor
        if edge in (Qt.TopLeftCorner, Qt.BottomRightCorner): 
            return Qt.SizeFDiagCursor
        if edge in (Qt.TopRightCorner, Qt.BottomLeftCorner): 
            return Qt.SizeBDiagCursor
        return None

    def _get_resize_edge(self, pos):
        """Определяет, находится ли курсор на границе окна для изменения размера."""
        rect = self.rect()
        width = self.RESIZE_BORDER_WIDTH
        
        # Точная логика определения углов и краев.
        
        is_top = rect.topLeft().y() <= pos.y() <= rect.topLeft().y() + width
        is_bottom = rect.bottomLeft().y() - width <= pos.y() <= rect.bottomLeft().y()
        is_left = rect.topLeft().x() <= pos.x() <= rect.topLeft().x() + width
        is_right = rect.topRight().x() - width <= pos.x() <= rect.topRight().x()

        if is_top and is_left:
            return Qt.TopLeftCorner
        if is_top and is_right:
            return Qt.TopRightCorner
        if is_bottom and is_left:
            return Qt.BottomLeftCorner
        if is_bottom and is_right:
            return Qt.BottomRightCorner
            
        # Края
        if is_top:
            return Qt.TopEdge
        if is_bottom:
            return Qt.BottomEdge
        if is_left:
            return Qt.LeftEdge
        if is_right:
            return Qt.RightEdge
            
        return None
        
    # --- Основные обработчики событий ---

    def center_window(self):
        """Центрирует окно на экране."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def toggle_maximized(self):
        """Переключает окно между нормальным и максимизированным состояниями."""
        if self.isMaximized():
            self.showNormal()
            if hasattr(self, 'maximize_button') and isinstance(self.maximize_button, QPushButton):
                self.maximize_button.setText("☐")
        else:
            self.showMaximized()
            if hasattr(self, 'maximize_button') and isinstance(self.maximize_button, QPushButton):
                self.maximize_button.setText("❐")
                
    def set_rounded_window_mask(self, radius=10):
        """
        Создает и применяет маску для скругления углов безрамочного окна.
        """
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius) 
        
        region = QRegion(path.toFillPolygon().toPolygon())
        
        self.setMask(region)


    def mousePressEvent(self, event):
        """
        Обрабатывает нажатие кнопки мыши.
        """
        if event.button() == Qt.LeftButton: 
            
            # 1. Проверяем, находится ли курсор на границе для Resizing
            if not self.isMaximized():
                self.resize_edge = self._get_resize_edge(event.pos())
                
                if self.resize_edge:
                    self.resizing = True
                    self.drag_position = event.pos()
                    return 

            # 2. Проверяем Title Bar (для Dragging)
            if hasattr(self, 'title_bar'):
                title_bar_rect = QRectF(self.title_bar.geometry())
                
                # Используем globalPos, чтобы учесть текущее положение окна
                if title_bar_rect.contains(event.pos()):
                    self.dragging = True
                    self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                    return
        
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """
        Обрабатывает движение мыши для перетаскивания и изменения размера.
        """
        if self.isMaximized():
            self.unsetCursor()
            self.resizing = False
            self.dragging = False 
        
        # 1. Изменение размера
        elif self.resizing and event.buttons() == Qt.LeftButton:
            
            self.resizeWindow(self.resize_edge, event.globalPos())
            
            cursor_shape = self._get_cursor_from_edge(self.resize_edge) 
            if cursor_shape:
                self.setCursor(cursor_shape)

        # 2. Перетаскивание
        elif self.dragging and event.buttons() == Qt.LeftButton:
            
            if self.isMaximized():
                 self.dragging = False
                 return 
                 
            self.move(event.globalPos() - self.drag_position)

        # 3. Обновление курсора (если не перетаскиваем и не изменяем размер)
        elif not self.dragging and not self.resizing and not self.isMaximized():
            resize_edge = self._get_resize_edge(event.pos())
            cursor_shape = self._get_cursor_from_edge(resize_edge) 
            
            if cursor_shape:
                self.setCursor(cursor_shape)
            else:
                self.unsetCursor()
        
        # Обязательный вызов super() для обработки внутренних виджетов
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Обрабатывает отпускание кнопки мыши (завершение перетаскивания/изменения размера).
        """
        self.dragging = False
        self.resizing = False
        self.unsetCursor()
        
        super().mouseReleaseEvent(event)

    def resizeWindow(self, edge, pos):
        """
        Низкоуровневая функция для изменения размера окна.
        """
        if not isinstance(self, QMainWindow):
            return

        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()

        new_w = w
        new_h = h
        new_x = x
        new_y = y

        global_x = pos.x()
        global_y = pos.y()
        
        # Используем минимальный размер, установленный в main_app
        MIN_SAFE_W = self.minimumSize().width()
        MIN_SAFE_H = self.minimumSize().height()
        
        if MIN_SAFE_W == 0: MIN_SAFE_W = 100
        if MIN_SAFE_H == 0: MIN_SAFE_H = 100
        

        # Изменение размера по горизонтали
        if edge in (Qt.LeftEdge, Qt.TopLeftCorner, Qt.BottomLeftCorner):
            new_w = w - (global_x - x)
            new_x = global_x
        elif edge in (Qt.RightEdge, Qt.TopRightCorner, Qt.BottomRightCorner):
            new_w = global_x - x

        # Изменение размера по вертикали
        if edge in (Qt.TopEdge, Qt.TopLeftCorner, Qt.TopRightCorner):
            new_h = h - (global_y - y)
            new_y = global_y
        elif edge in (Qt.BottomEdge, Qt.BottomLeftCorner, Qt.BottomRightCorner):
            new_h = global_y - y

        # Применяем ограничения
        
        if new_w < MIN_SAFE_W:
            new_w = MIN_SAFE_W
            if edge in (Qt.LeftEdge, Qt.TopLeftCorner, Qt.BottomLeftCorner):
                 new_x = x + (w - MIN_SAFE_W)
            
        if new_h < MIN_SAFE_H:
            new_h = MIN_SAFE_H
            if edge in (Qt.TopEdge, Qt.TopLeftCorner, Qt.TopRightCorner):
                 new_y = y + (h - MIN_SAFE_H)

        self.setGeometry(new_x, new_y, new_w, new_h)

    def closeEvent(self, event):
        logger.info("Закрытие приложения. Остановка всех активных потоков.")
        
        if hasattr(self, 'threads'):
            for thread in self.threads:
                if thread.isRunning():
                    thread.quit() 
                    thread.wait()
        
        if hasattr(self, 'emulator_thread') and self.emulator_thread is not None and self.emulator_thread.isRunning():
            self.emulator_thread.quit()
            self.emulator_thread.wait()
            
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread is not None and self.game_loader_thread.isRunning():
            self.game_loader_thread.quit()
            self.game_loader_thread.wait()
            
        event.accept()