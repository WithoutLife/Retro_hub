# style.py (ИСПРАВЛЕННАЯ ВЕРСИЯ: Удален конфликтный фон)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

def apply_dark_theme(app):
    """Применяет ультра-тёмную таблицу стилей QSS к приложению, включая стили для окна описания."""
    
    NEON_COLOR = "#8A2BE2"  
    ACCENT_COLOR = "#1a1a1a"  

    dark_stylesheet = f"""
    /* --- ОСНОВНЫЕ ЦВЕТА И ОКНО --- */
    QMainWindow {{ 
        border: none; 
        border-radius: 10px; 
    }} 
    
    QWidget#centralwidget {{
        border: 1px solid #0f0f0f;
        /* 💡 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Удален background-color, чтобы его мог задать градиент в app_logic.py */
        /* Радиус скругления для центральной части (под отступ 10px) */
        border-radius: 9px; 
    }}
    
    QWidget, QFrame {{ border: none; }}
    
    QWidget#titleBar {{ 
        background-color: #1a1a1a; 
        /* Углы на 1px меньше, чем centralwidget (9-1=8) */
        border-top-left-radius: 8px; 
        border-top-right-radius: 8px;
        color: none; 
    }} 
    
    /* СТИЛЬ ЛОГОТИПА */
    QLabel#logoLabel {{
        background-color: transparent; 
        color: #FFFFFF; 
        padding: 0px; 
    }}
    
    /* КНОПКИ УПРАВЛЕНИЯ ОКНОМ */
    QPushButton#windowControlButton {{
        background-color: transparent; 
        border: none;
        color: #8A2BE2;
        font-size: 14pt; 
        line-height: 10pt;
        padding: 0;
        min-width: 40px; 
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
    }}
    QPushButton#windowControlButton:hover {{
        background-color: #333333;
    }}
    QPushButton#windowControlButton:last:hover {{ 
        background-color: #FF0000;
    }}
    
    /* --- КНОПКИ-ИКОНКИ КОНСОЛЕЙ (40x40) --- */
    QPushButton#simpleConsoleButton {{
        background-color: #1a1a1a; 
        border: 2px solid #1a1a1a;
        color: #FFFFFF; 
        padding: 0;
        border-radius: 8px; 
        min-width: 40px; 
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
    }}

    QPushButton#simpleConsoleButton:hover:!checked {{
        background-color: #444444; 
        border-color: #AAAAAA;
    }}
    
    QPushButton#simpleConsoleButton:checked {{
        background-color: transparent; 
        border: 2px solid {ACCENT_COLOR}; 
        color: {ACCENT_COLOR};
        font-weight: bold;
    }}
    
    /* СКРОЛЛБАРЫ */
   QScrollArea {{ 
        background-color: transparent; 
        border: none;
    }}
    QWidget#gridWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        border: none;
        background: #1a1a1a; 
        width: 10px;
        /* 🟢 Убираем маржины, чтобы скроллбар прилегал к Title Bar и Footer */
        margin: 0px 0 0px 0; 
    }}
    QScrollBar::handle:vertical {{
        background: #444444; 
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    
    /* КНОПКИ (ОБЩИЙ СТИЛЬ) */
    QPushButton {{
        background-color: #333333; 
        color: #FFFFFF;
        border: 1px solid #555555;
        padding: 5px 10px;
        border-radius: 5px;
    }}
    QPushButton:hover {{
        background-color: #444444;
    }}
    QPushButton:pressed {{
        background-color: #555555;
    }}

    /* ПОЛЕ ПОИСКА */
    QLineEdit#searchBox {{
        background-color: #1a1a1a; 
        border: 1px solid #555555;
        padding: 0 5px; 
        border-radius: 5px;
        color: #FFFFFF;
        font-size: 14pt;
    }}
    QLineEdit#searchBox:focus {{
        border: 1px solid #777777; 
    }}

    /* --- СТИЛИ DescriptionWindow --- */
    QDialog#DescriptionWindow {{
        background-color: #1a1a1a; 
        border: 1px solid #0f0f0f; 
        border-radius: 10px;
    }}
    
    QTextBrowser {{
        background-color: #1a1a1a;
        color: #DDDDDD; 
        border: none;
        padding: 10px;
    }}
    
    QTextBrowser h1 {{
        color: {ACCENT_COLOR}; 
        font-size: 24pt;
        font-weight: bold;
        padding-bottom: 5px;
        text-align: center;
    }}

    QTextBrowser h2 {{
        color: #FF8C00; 
        font-size: 16pt;
        border-bottom: 2px solid #555;
        padding-bottom: 5px;
        margin-top: 20px;
    }}
    
    QTextBrowser h3 {{
        color: {NEON_COLOR}; 
        font-size: 13pt;
        margin-top: 10px;
    }}

    QTextBrowser b {{
        color: #FFFF00; 
        font-weight: bold;
    }}

    QTextBrowser div.details-box {{
        background-color: #2a2a2a; 
        padding: 15px;
        border-left: 5px solid {ACCENT_COLOR};
        border-radius: 4px;
        margin-bottom: 25px;
    }}

    QTextBrowser div.image-gallery {{
        margin-top: 0px; 
        border-top: 2px dashed #444;
        padding-top: 10px;
        margin-bottom: 20px;
        white-space: nowrap; 
    }}

    QTextBrowser img {{
        margin-right: 5px;
        border: 1px solid #444;
        border-radius: 5px;
    }}
    
    QPushButton#runButton {{
        background-color: #008000;
        border: 1px solid #00FF00;
        color: #FFFFFF;
        font-size: 12pt;
        font-weight: bold;
        padding: 10px;
    }}
    QPushButton#runButton:hover {{
        background-color: #00A000;
    }}
    
    QLabel#gameTitleLabel {{
        color: #FFFFFF;
        background-color: rgba(0, 0, 0, 150);
        padding: 3px 5px;
        border-radius: 3px;
    }}
    
    QLabel#footerLabel {{
        color: #AAAAAA;
        font-size: 8pt;
    }}
    
    QWidget#footerWidget {{
        background-color: #1a1a1a;
        border-top: 1px solid #333333; 
        /* Углы на 1px меньше, чем centralwidget (9-1=8) */
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
    }}

    """
    app.setStyleSheet(dark_stylesheet)