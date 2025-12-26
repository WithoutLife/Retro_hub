import os
import subprocess
import logging

from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt, QRectF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPainterPath, QColor

logger = logging.getLogger(__name__)

class EmulatorMonitorThread(QThread):
    """Отдельный поток для запуска эмулятора и отслеживания его завершения."""
    emulator_closed = pyqtSignal() 

    def __init__(self, emulator_path, rom_path):
        super().__init__()
        self.emulator_path = emulator_path
        self.rom_path = rom_path
        self.emulator_dir = os.path.dirname(emulator_path) 
        
    def run(self):
        try:
            process = subprocess.Popen([self.emulator_path, self.rom_path], 
                                       shell=False,
                                       cwd=self.emulator_dir) 
            process.wait() 
        except Exception:
            logger.error("Ошибка при запуске/мониторинге эмулятора:", exc_info=True)
        finally:
            self.emulator_closed.emit()


class ImageLoaderThread(QThread):
    """Отдельный поток для загрузки, масштабирования и скругления обложки (оптимизация UI)."""
    image_ready = pyqtSignal(QPixmap, object) 

    def __init__(self, item_widget, icon_size, game_folder, allowed_cover_extensions):
        super().__init__()
        self.item_widget = item_widget
        self.game_folder = game_folder
        self.allowed_cover_extensions = allowed_cover_extensions
        
        # !!! ИСПРАВЛЕНИЕ: Используем размер image_label, а не icon_size !!!
        # ЭТО ГАРАНТИРУЕТ, что масштабирование в _load_and_process_cover будет точным.
        self.icon_size = item_widget.image_label.size()
        
    def run(self):
        pixmap = self._load_and_process_cover()
        if self.item_widget: 
             self.image_ready.emit(pixmap, self.item_widget)

    @staticmethod
    def _create_placeholder_pixmap(size: QSize):
        """Создает QPixmap-заглушку."""
        pixmap = QPixmap(size)
        pixmap.fill(QColor("#404040")) 
        return pixmap
        
    @staticmethod
    def _get_rounded_pixmap(source_pixmap: QPixmap, radius=8):
        """Применяет скругление к QPixmap."""
        if source_pixmap.isNull(): return source_pixmap
            
        target = QPixmap(source_pixmap.size())
        target.fill(Qt.transparent) 
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        rect = source_pixmap.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, source_pixmap)
        painter.end()
        
        return target

    def _load_and_process_cover(self):
        """Ищет обложку, загружает ее, масштабирует и скругляет."""
        cover_path = None
        image_dir = os.path.join(self.game_folder, "images")
        
        if os.path.isdir(image_dir):
            allowed_lowercased_extensions = [e.lower() for e in self.allowed_cover_extensions]
            
            for filename in os.listdir(image_dir):
                name, ext = os.path.splitext(filename)
                
                if name.lower() == 'cartridge' and ext.lower() in allowed_lowercased_extensions:
                    cover_path = os.path.join(image_dir, filename)
                    break 
        
        if cover_path:
            # Оптимизация: Используем QImage для загрузки вне потока UI
            temp_image = QImage(os.path.normpath(cover_path)) 

            if not temp_image.isNull():
                temp_pixmap = QPixmap.fromImage(temp_image)
                
                scaled_pixmap = temp_pixmap.scaled(
                    self.icon_size, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation 
                )
                return self._get_rounded_pixmap(scaled_pixmap)
        
        return self._get_rounded_pixmap(self._create_placeholder_pixmap(self.icon_size))