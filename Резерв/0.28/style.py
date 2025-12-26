# style.py (ОБНОВЛЕННЫЙ КОД - ИСПРАВЛЕНЫ СТИЛИ QSS)

from PyQt5.QtWidgets import QApplication

def apply_dark_theme(app):
    """Применяет ультра-тёмную таблицу стилей QSS к приложению, включая стили для окна описания."""
    
    # Цвет, который используется для акцентов (неоновый/пурпурный)
    NEON_COLOR = "#8A2BE2" 
    ACCENT_COLOR = "#00FFFF" # Неоново-синий для текста

    dark_stylesheet = f"""
    /* --- ОСНОВНЫЕ ЦВЕТА И ОКНО --- */
    QMainWindow {{ 
        /* !!! ГРАДИЕНТ будет задан в main_app.py для centralwidget !!! */
        border: 1px solid #0f0f0f; 
        border-radius: 10px; 
    }} 
    
    QWidget, QFrame {{ border: none; }}
    
    QWidget#titleBar {{ 
        background-color: #1a1a1a; 
        border-top-left-radius: 10px; 
        border-top-right-radius: 10px;
        color: none; 
    }} 
    
    /* СТИЛЬ ЛОГОТИПА */
    QLabel#logoLabel {{
        background-color: transparent; 
        color: #FFFFFF; 
        padding: 5px 0px 5px 0px;
    }}
    
    /* СТИЛЬ КНОПКИ ПЕРЕКЛЮЧЕНИЯ */
    QPushButton#switchButton {{
        background-color: #303030;
        border: 2px solid #505050;
        border-radius: 5px;
        color: #ffffff;
        padding: 6px 12px;
        margin: 5px;
        font-weight: bold;
    }}

    /* --- СТИЛЬ ОБЩИХ КНОПОК --- */
    QPushButton {{
        background-color: #303030;
        border: 2px solid #505050;
        border-radius: 5px;
        color: #ffffff;
        padding: 6px 12px;
        margin: 5px;
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: #404040;
        border-color: {NEON_COLOR};
    }}
    
    QPushButton:pressed {{
        background-color: #202020;
    }}
    
    /* --- СТИЛЬ ЭЛЕМЕНТОВ СЕТКИ ИГР --- */
    
    QFrame#GameItem {{
        background-color: transparent;
    }}

    QFrame#GameItem QLabel {{
        background-color: transparent; 
        border-radius: 8px;
        padding: 0; 
    }}

    QLabel#GameItemTitle {{
        color: #cccccc;
        font-size: 10pt;
        background-color: transparent; 
        padding: 0;
        margin: 0;
    }}

    /* --- СТИЛЬ ПОЛЯ ПОИСКА --- */
    QLineEdit#searchLineEdit {{
        background-color: #1a1a1a; 
        border: 1px solid #303030; 
        border-radius: 5px; 
        color: #ffffff;
        padding: 5px;
        font-size: 12pt;
        selection-background-color: {NEON_COLOR}; 
        margin-right: 0px; 
    }}
    
    QScrollArea#gameScrollArea {{ background-color: transparent; border: none; }}
    
    /* Общий стиль для QLabel */
    QLabel {{ color: #ffffff; font-size: 12pt; }}
    
    /* --- СТИЛЬ ФУТЕРА --- */
    QLabel#footerLabel {{
        color: #555555; 
        font-size: 7pt;
        margin: 0px; 
        padding: 0px 0px 0px 0px;
        padding-bottom: -4px; 
    }}
    
    QWidget#footer_widget {{ background-color: #1a1a1a; }}
    
    /* --- СКРОЛЛБАРЫ --- */
    QScrollBar:vertical, QScrollBar:horizontal {{
        border: none; 
        background: transparent; 
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: #303030; 
        border-radius: 4px; 
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: #404040; 
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        height: 0px;
        width: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}
    
    /* --- СТИЛИ ОКНА ОПИСАНИЯ (DescriptionWindow) --- */
    
    QDialog {{ 
        background-color: #1a1a1a; 
        color: #EAEAEA; 
    }}
    
    /* Стиль кнопки "Закрыть" в окне описания */
    DescriptionWindow QPushButton {{ 
        background-color: #383838;
        border: 2px solid #606060;
        color: #EAEAEA;
    }}
    
    DescriptionWindow QPushButton:hover {{ 
        background-color: #484848;
        border-color: {NEON_COLOR};
        color: {ACCENT_COLOR}; 
    }}
    
    /* Стили для QTextBrowser, который рендерит HTML */
    QTextBrowser {{
        background-color: #1c1c1c; 
        color: #EAEAEA; 
        font-size: 11.5pt;
        padding: 15px;
        border: none;
    }}

    /* Заголовок H1 - Неоновый акцент */
    QTextBrowser h1 {{
        color: {ACCENT_COLOR}; 
        font-size: 24pt;
        font-weight: bold;
        padding-bottom: 5px;
        text-align: center;
    }}

    /* Заголовок H2 - Теплый контрастный цвет */
    QTextBrowser h2 {{
        color: #FF8C00; /* Dark Orange */
        font-size: 16pt;
        border-bottom: 2px solid #555;
        padding-bottom: 5px;
        margin-top: 20px;
    }}
    
    /* Выделение жирного текста */
    QTextBrowser b {{
        color: #FFFF00; /* Ярко-желтый */
        font-weight: bold;
    }}

    /* Стиль для блока деталей (.details-box) */
    QTextBrowser div.details-box {{
        background-color: #2a2a2a; 
        padding: 15px;
        border-left: 5px solid {ACCENT_COLOR};
        border-radius: 4px;
        margin-bottom: 25px;
    }}

    /* Стиль для галереи скриншотов (.image-gallery) */
    QTextBrowser div.image-gallery {{
        margin-top: 0px; 
        border-top: 2px dashed #444; 
        padding-top: 0px; 
    }}

    QTextBrowser img {{
        /* Здесь задаем только оформление: рамку и скругление */
        border: 1px solid #FF8C00; 
        border-radius: 4px;
        margin-right: 5px; 
        
        /* СТИЛИ ДЛЯ РАЗМЕРА И ВЫРАВНИВАНИЯ (поддерживаются Qt) */
        height: 100px; /* Фиксированная высота для всех превью */
        width: auto;   /* Автоматическое масштабирование ширины */
    }}
    """
    app.setStyleSheet(dark_stylesheet)