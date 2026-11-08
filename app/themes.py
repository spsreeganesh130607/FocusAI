"""Shared FocusAI theme palettes and Qt stylesheet generation."""

from pathlib import Path

PALETTES = {
    "Arctic Light": {
        "window": "#F6F8FC", "surface": "#FFFFFF", "surface_alt": "#EDF3FC",
        "text": "#25334A", "muted": "#59677B", "border": "#E1E7F0",
        "primary": "#3F6DB1", "primary_hover": "#3D6FBF",
        "primary_text": "#FFFFFF", "selection": "#DDE9F9",
        "input": "#FFFFFF", "input_text": "#34445B", "scroll": "#EDF1F6",
        "scroll_handle": "#C4CFDD", "status": "#348568", "productive": "#49A887",
        "neutral": "#9AA6B5", "distracting": "#E78C83",
    },
    "Midnight": {
        "window": "#171C27", "surface": "#222A38", "surface_alt": "#2C3749",
        "text": "#EEF3FA", "muted": "#B2BED0", "border": "#3B475A",
        "primary": "#6FA4F5", "primary_hover": "#8AB6FA",
        "primary_text": "#111A29", "selection": "#344968",
        "input": "#202938", "input_text": "#F0F4FA", "scroll": "#202938",
        "scroll_handle": "#53627A", "status": "#78C9A5", "productive": "#5BC39D",
        "neutral": "#A8B3C2", "distracting": "#F08E8A",
    },
    "Forest": {
        "window": "#E9EFE5", "surface": "#FBFCF7", "surface_alt": "#E1EBDD",
        "text": "#26382D", "muted": "#586B5C", "border": "#D2DDCF",
        "primary": "#4D8060", "primary_hover": "#416F52",
        "primary_text": "#FFFFFF", "selection": "#D7E8D8",
        "input": "#FFFFFF", "input_text": "#293B30", "scroll": "#E1EBDD",
        "scroll_handle": "#AABBAA", "status": "#397551", "productive": "#4D9A70",
        "neutral": "#929F93", "distracting": "#D77F72",
    },
    "Lavender": {
        "window": "#F2EFF9", "surface": "#FFFFFF", "surface_alt": "#EAE4F7",
        "text": "#332D48", "muted": "#625A76", "border": "#DDD6EF",
        "primary": "#765DBF", "primary_hover": "#7058B5",
        "primary_text": "#FFFFFF", "selection": "#E4DCF8",
        "input": "#FFFFFF", "input_text": "#3A3450", "scroll": "#EAE6F2",
        "scroll_handle": "#BDB3D3", "status": "#4D8B6B", "productive": "#52A27D",
        "neutral": "#A19BAE", "distracting": "#D98291",
    },
    "Warm Sand": {
        "window": "#F5F0E6", "surface": "#FFFCF6", "surface_alt": "#EEE5D4",
        "text": "#403729", "muted": "#685E4C", "border": "#E5DCCB",
        "primary": "#985C16", "primary_hover": "#9F6625",
        "primary_text": "#FFFFFF", "selection": "#F2E2C6",
        "input": "#FFFEFA", "input_text": "#453B2D", "scroll": "#EDE5D7",
        "scroll_handle": "#C5B79E", "status": "#55805D", "productive": "#5B9A72",
        "neutral": "#A69A85", "distracting": "#D47F6E",
    },
}


def stylesheet(theme_name, asset_directory):
    palette = PALETTES.get(theme_name, PALETTES["Arctic Light"])
    arrow_variant = "-light" if theme_name == "Midnight" else ""
    up_arrow = (Path(asset_directory) / f"spin-up{arrow_variant}.svg").as_posix()
    down_arrow = (Path(asset_directory) / f"spin-down{arrow_variant}.svg").as_posix()
    return f"""
        QMainWindow, QWidget {{ background: {palette['window']}; color: {palette['text']};
                               font-family: Segoe UI; }}
        QLabel {{ background: transparent; border: none; }}
        #Page, #Pages {{ background: {palette['window']}; }}
        #Sidebar {{ background: {palette['surface']}; border-right: 1px solid {palette['border']}; }}
        #Logo {{ font-size: 28px; font-weight: 750; color: {palette['text']}; }}
        #SidebarSub, #Description, #Muted {{ color: {palette['muted']}; font-size: 13px; }}
        #SidebarSub {{ font-size: 12px; }}
        #Status, #SettingsStatus {{ color: {palette['status']}; font-size: 12px; padding: 8px 0; }}
        QPushButton {{ background: {palette['surface']}; color: {palette['text']};
                       border: 1px solid {palette['border']}; border-radius: 9px;
                       padding: 10px 14px; text-align: left; font-size: 14px; }}
        QPushButton:hover {{ background: {palette['surface_alt']}; }}
        QPushButton:pressed {{ background: {palette['selection']}; }}
        QPushButton:checked {{ background: {palette['selection']}; border-color: {palette['primary']};
                               color: {palette['text']}; }}
        QPushButton:disabled {{ background: {palette['surface_alt']}; color: {palette['muted']}; }}
        #StartButton, #SettingsSaveButton, #PrimaryButton {{
            background: {palette['primary']}; color: {palette['primary_text']};
            border: none; font-size: 15px; font-weight: 700; text-align: center;
            border-radius: 9px;
        }}
        #StartButton:hover, #SettingsSaveButton:hover, #PrimaryButton:hover {{
            background: {palette['primary_hover']};
        }}
        #StartButton {{ margin-top: 8px; }}
        #SmallButton {{ padding: 8px 13px; text-align: center; }}
        #Heading {{ font-size: 28px; font-weight: 700; color: {palette['text']}; }}
        #Card {{ background: {palette['surface']}; border: 1px solid {palette['border']};
                 border-radius: 14px; }}
        #Card[tone="productive"] {{ border-bottom: 3px solid {palette['productive']}; }}
        #Card[tone="neutral"] {{ border-bottom: 3px solid {palette['neutral']}; }}
        #Card[tone="distracting"] {{ border-bottom: 3px solid {palette['distracting']}; }}
        #CardTitle, #StatTitle, #PresetHeader {{ color: {palette['muted']}; font-size: 11px;
            font-weight: 700; letter-spacing: 1px; }}
        #BigScore {{ font-size: 48px; font-weight: 750; color: {palette['primary']}; padding: 2px; }}
        #StatValue {{ font-size: 23px; font-weight: 650; color: {palette['text']}; }}
        #SectionTitle {{ font-size: 17px; font-weight: 650; color: {palette['text']}; }}
        #Timer {{ font-size: 30px; font-weight: 750; color: {palette['primary']}; }}
        QProgressBar {{ background: {palette['surface_alt']}; color: {palette['text']};
                        border: none; border-radius: 5px; }}
        QProgressBar::chunk {{ background: {palette['primary']}; border-radius: 5px; }}
        #ProductiveBar::chunk {{ background: {palette['productive']}; }}
        #NeutralBar::chunk {{ background: {palette['neutral']}; }}
        #DistractingBar::chunk {{ background: {palette['distracting']}; }}
        QSpinBox, QComboBox, QDateEdit, QLineEdit {{ background: {palette['input']}; color: {palette['input_text']};
            border: 1px solid {palette['border']}; border-radius: 9px;
            padding: 4px 12px; font-size: 14px; min-height: 42px; }}
        QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
            border: 1px solid {palette['primary']};
        }}
        QSpinBox {{ selection-background-color: {palette['primary']};
            padding: 4px 38px 4px 12px; min-height: 52px; }}
        QSpinBox QLineEdit {{ background: transparent; border: none; padding: 0;
            min-height: 40px; }}
        QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
            width: 30px; height: 24px; background: {palette['surface_alt']};
            border: 1px solid {palette['border']}; border-top-right-radius: 8px; }}
        QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
            width: 30px; height: 24px; background: {palette['surface_alt']};
            border: 1px solid {palette['border']}; border-bottom-right-radius: 8px; }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {palette['selection']};
        }}
        QSpinBox::up-arrow {{ image: url("{up_arrow}"); width: 10px; height: 8px; }}
        QSpinBox::down-arrow {{ image: url("{down_arrow}"); width: 10px; height: 8px; }}
        QComboBox {{ combobox-popup: 0; padding-right: 34px; min-width: 110px; }}
        QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;
            width: 28px; border-left: 1px solid {palette['border']}; }}
        QComboBox::down-arrow, QDateEdit::down-arrow {{
            image: url("{down_arrow}"); width: 10px; height: 8px;
        }}
        QDateEdit {{ min-width: 132px; padding-right: 32px; }}
        QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;
            width: 27px; border-left: 1px solid {palette['border']}; }}
        QComboBox QAbstractItemView {{ background: {palette['surface']}; color: {palette['text']};
            border: 1px solid {palette['border']}; selection-background-color: {palette['selection']};
            selection-color: {palette['text']}; padding: 4px; }}
        QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 6px 10px; }}
        QCalendarWidget QWidget {{ background: {palette['surface']}; color: {palette['text']}; }}
        QCalendarWidget QToolButton {{ background: {palette['surface_alt']}; color: {palette['text']};
            border: 1px solid {palette['border']}; border-radius: 5px; padding: 5px; }}
        QCalendarWidget QAbstractItemView {{ background: {palette['surface']}; color: {palette['text']};
            selection-background-color: {palette['primary']}; selection-color: {palette['primary_text']}; }}
        #DurationBadge {{ background: {palette['surface_alt']}; color: {palette['primary']};
            border: 1px solid {palette['border']}; border-radius: 10px; padding: 6px 10px;
            font-size: 11px; font-weight: 700; }}
        #SettingsHint, #ThemePreview {{ background: {palette['surface_alt']}; color: {palette['text']};
            border: 1px solid {palette['border']}; border-radius: 9px; padding: 11px; }}
        QListWidget, QTableWidget {{ background: {palette['surface']}; color: {palette['text']};
            border: 1px solid {palette['border']}; border-radius: 10px; outline: none;
            gridline-color: {palette['border']}; selection-background-color: {palette['selection']};
            selection-color: {palette['text']}; }}
        QListWidget {{ padding: 7px; }}
        QListWidget::item {{ padding: 12px; border-radius: 7px; }}
        QListWidget::item:hover {{ background: {palette['surface_alt']}; }}
        QListWidget::item:selected {{ background: {palette['selection']}; }}
        QTableWidget::item {{ padding: 6px; }}
        QHeaderView::section {{ background: {palette['surface_alt']}; color: {palette['muted']};
            border: none; border-bottom: 1px solid {palette['border']}; padding: 8px;
            font-weight: 700; }}
        QCheckBox {{ spacing: 7px; color: {palette['text']}; }}
        QCheckBox::indicator {{ width: 17px; height: 17px; }}
        QCheckBox::indicator:unchecked {{ border: 1px solid {palette['muted']};
            background: {palette['surface']}; border-radius: 4px; }}
        QCheckBox::indicator:checked {{ border: 1px solid {palette['primary']};
            background: {palette['primary']}; border-radius: 4px; }}
        QToolTip {{ background: {palette['surface']}; color: {palette['text']};
            border: 1px solid {palette['border']}; padding: 5px; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ background: {palette['scroll']}; width: 10px; margin: 2px; border: none; }}
        QScrollBar::handle:vertical {{ background: {palette['scroll_handle']};
            min-height: 28px; border-radius: 5px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QDialog {{ background: {palette['surface']}; color: {palette['text']}; }}
    """
