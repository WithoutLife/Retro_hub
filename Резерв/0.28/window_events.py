import logging
from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QPainterPath, QRegion

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# КЛАСС WindowEventsMixin (Смешиваемый класс для LauncherApp)
# ----------------------------------------------------------------------

class WindowEventsMixin:
    """Содержит все обработчики событий для кастомного окна (перетаскивание, изменение размера, закрытие)."""
    
    RESIZE_BORDER_WIDTH = 5 
    # ... (методы toggle_maximized, set_rounded_window_mask, _get_cursor_from_edge, get_resize_edge без изменений)
    
    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("☐")
            self.set_rounded_window_mask(radius=10) 
        else:
            self.showMaximized()
            self.maximize_button.setText("❐") 
            self.setMask(QRegion())

    def set_rounded_window_mask(self, radius=10):
        if self.isMaximized(): return
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(QRectF(rect), radius, radius)
        
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        
    def _get_cursor_from_edge(self, edges):
        if edges == (Qt.TopEdge | Qt.LeftEdge) or edges == (Qt.BottomEdge | Qt.RightEdge): 
            return Qt.SizeFDiagCursor
        if edges == (Qt.TopEdge | Qt.RightEdge) or edges == (Qt.BottomEdge | Qt.LeftEdge): 
            return Qt.SizeBDiagCursor
        if edges == Qt.LeftEdge or edges == Qt.RightEdge: 
            return Qt.SizeHorCursor
        if edges == Qt.TopEdge or edges == Qt.BottomEdge: 
            return Qt.SizeVerCursor
        return None 
        
    def get_resize_edge(self, pos: QPoint):
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
            
            # Проверка, что нажатие произошло в Title Bar
            # Это условие проверяет только вертикальную координату (y)
            if hasattr(self, 'title_bar') and event.pos().y() < self.title_bar.height():
                self.drag_offset = event.globalPos() - self.pos()
                event.accept()
                return # Мы обработали событие, дальнейший вызов не нужен
            
        # 🚨 СТРОКА 88 В ВАШЕМ КОДЕ ДОЛЖНА БЫТЬ ЗДЕСЬ И БЫТЬ ВЫЗВАНА
        # ТОЛЬКО ЕСЛИ СОБЫТИЕ НЕ БЫЛО ОБРАБОТАНО Mixin'ом.
        # Если Mixin не обработал событие (например, клик на игру),
        # мы передаем его в базовый класс QMainWindow, а затем в GameItem.
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.isMaximized():
            super().mouseMoveEvent(event)
            return

        if event.buttons() == Qt.LeftButton:
            # Проверяем, что drag_offset определен и мы находимся в области заголовка
            if hasattr(self, 'drag_offset') and not self.resizing and event.pos().y() < self.title_bar.height():
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
        
        # self.threads, self.emulator_thread, self.game_loader_thread должны быть определены
        
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
            
        super().closeEvent(event)