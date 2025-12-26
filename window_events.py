# F:\User\project\Retro_HUB\window_events.py

import logging
from PyQt5.QtCore import Qt, QPoint, QRectF, QRect
from PyQt5.QtGui import QPainterPath, QRegion, QCursor
from PyQt5.QtWidgets import QApplication, QDesktopWidget

logger = logging.getLogger(__name__)

class WindowEventsMixin:
    
    RESIZE_BORDER_WIDTH = 8 
    
    def __init__(self, *args, **kwargs):
        # MRO гарантирует вызов super().__init__
        super().__init__(*args, **kwargs) 
        self.dragging = False
        self.resizing = False
        self.setMouseTracking(True)
        
    # --- Вспомогательные методы ---
    
    def _get_cursor_from_edge(self, edge):
        if edge in (Qt.TopEdge, Qt.BottomEdge): return Qt.SizeVerCursor
        if edge in (Qt.LeftEdge, Qt.RightEdge): return Qt.SizeHorCursor
        if edge in (Qt.TopLeftCorner, Qt.BottomRightCorner): return Qt.SizeFDiagCursor
        if edge in (Qt.TopRightCorner, Qt.BottomLeftCorner): return Qt.SizeBDiagCursor
        return None

    def _get_resize_edge(self, pos):
        if self.isMaximized() or self.windowState() & Qt.WindowMinimized: 
            return None
        
        rect = self.rect()
        width = self.RESIZE_BORDER_WIDTH
        
        # Проверка на нахождение курсора в зоне 8px от края
        is_top = rect.topLeft().y() <= pos.y() <= rect.topLeft().y() + width
        is_bottom = rect.bottomLeft().y() - width <= pos.y() <= rect.bottomLeft().y()
        is_left = rect.topLeft().x() <= pos.x() <= rect.topLeft().x() + width
        is_right = rect.topRight().x() - width <= pos.x() <= rect.topRight().x()
        
        # Определение углов
        if is_top and is_left: return Qt.TopLeftCorner
        if is_top and is_right: return Qt.TopRightCorner
        if is_bottom and is_left: return Qt.BottomLeftCorner
        if is_bottom and is_right: return Qt.BottomRightCorner
        # Определение сторон
        if is_top: return Qt.TopEdge
        if is_bottom: return Qt.BottomEdge
        if is_left: return Qt.LeftEdge
        if is_right: return Qt.RightEdge
        return None
    
    
    # --- Основные обработчики событий ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: 
            
            is_resize = self._get_resize_edge(event.pos()) is not None
            
            # 🛑 СНЯТИЕ МАСКИ ПЕРЕД НАЧАЛОМ ЛЮБОГО ДЕЙСТВИЯ (Ключ к ресайзу)
            if (is_resize or (hasattr(self, 'title_bar') and QRect(self.title_bar.geometry()).contains(event.pos()))) and not self.isMaximized():
                self.setMask(QRegion())
                self.update() # Принудительное обновление для снятия мерцания
            
            if is_resize:
                try:
                    # Начинаем нативный ресайз
                    self.windowHandle().startSystemResize(self._get_resize_edge(event.pos()))
                    self.resizing = True 
                    return
                except Exception as e:
                    logger.debug(f"startSystemResize failed: {e}")
                    
            if hasattr(self, 'title_bar'):
                title_bar_rect = QRect(self.title_bar.geometry())
                
                if title_bar_rect.contains(event.pos()):
                    try:
                        # Начинаем нативное перемещение
                        self.windowHandle().startSystemMove()
                        self.dragging = True 
                        return
                    except Exception as e:
                        logger.debug(f"startSystemMove failed: {e}")
        
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.isMaximized() or self.windowState() & Qt.WindowMinimized:
            self.unsetCursor()
            self.resizing = False
            self.dragging = False 
            
        # 🛑 КОНТРОЛЬ КУРСОРА В ГРАНИЦАХ
        if not self.dragging and not self.resizing and not self.isMaximized():
            qt_edge = self._get_resize_edge(event.pos())
            cursor_shape = self._get_cursor_from_edge(qt_edge) 
            
            if cursor_shape:
                self.setCursor(cursor_shape)
            else:
                self.unsetCursor()
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_active = self.dragging or self.resizing
        
        self.dragging = False
        self.resizing = False
        self.unsetCursor()
        
        super().mouseReleaseEvent(event)
        
        # 🛑 НЕМЕДЛЕННОЕ ВОССТАНОВЛЕНИЕ МАСКИ ПОСЛЕ ЗАВЕРШЕНИЯ (Ключ к восстановлению границ)
        if was_active and not self.isMaximized():
            self.set_rounded_window_mask(radius=10)
            self.update() 


    # --- Остальные методы ---

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
    def set_rounded_window_mask(self, radius=10):
        if self.isMaximized():
            self.setMask(QRegion())
            return
            
        path = QPainterPath()
        rect_for_mask = QRectF(self.rect())
        path.addRoundedRect(rect_for_mask, radius, radius) 
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        self.update() # Принудительное обновление для отображения маски

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Логика маски перенесена в mouseReleaseEvent
        pass 
             
    def closeEvent(self, event):
        super().closeEvent(event)