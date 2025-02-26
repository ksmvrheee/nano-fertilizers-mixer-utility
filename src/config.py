import flet as ft


PAGE_BASIC_WIDTH = 650
PAGE_BASIC_HEIGHT = 715
PAGE_MIN_WIDTH = 600
PAGE_MIN_HEIGHT = 715
PAGE_MAX_WIDTH = 750
PAGE_MAX_HEIGHT = 715
BASIC_CONTENT_WIDTH = 475
COLOR_THEME_SEED = ft.Colors.GREEN_ACCENT

NAVIGATION_MENU_BUTTON_STYLE = ft.ButtonStyle(padding=ft.padding.symmetric(vertical=20, horizontal=10),
                                              shape=ft.ContinuousRectangleBorder())

UNIFIED_BUTTON_STYLE = ft.ButtonStyle(padding=ft.padding.symmetric(vertical=15, horizontal=18),
                                      text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_500))
VERSION = '1.0.2'