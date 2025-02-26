import flet as ft

from config import NAVIGATION_MENU_BUTTON_STYLE


class NavigationMenu(ft.MenuBar):
    """
    A navigation menu for the application.
    Provides buttons and submenus for navigating between different sections.
    Calls the `on_navigate` function with the corresponding route when an item is clicked.
    """
    def __init__(self, on_navigate, **kwargs):
        """
        Initializes the navigation menu providing the set of controls.

        :param on_navigate: a function to handle navigation.
        """
        super().__init__(
            expand=True,
            controls=[
                ft.MenuItemButton(content=ft.Text('Домой', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                                  on_click=lambda _: on_navigate('home'), style=NAVIGATION_MENU_BUTTON_STYLE),
                ft.SubmenuButton(
                    content=ft.Text('Добавить', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    style=NAVIGATION_MENU_BUTTON_STYLE,
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text('Категорию растений', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                            on_click=lambda _: on_navigate('category'), style=NAVIGATION_MENU_BUTTON_STYLE
                        ),
                        ft.SubmenuButton(
                            content=ft.Text('Растение', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                            style=NAVIGATION_MENU_BUTTON_STYLE,
                            controls=[
                                ft.MenuItemButton(
                                    content=ft.Text('через соотношение N:P:K',
                                                    theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                                    style=NAVIGATION_MENU_BUTTON_STYLE,
                                    on_click=lambda _: on_navigate('plant_by_npk')
                                ),
                                ft.MenuItemButton(
                                    content=ft.Text('через совокупность удобрений',
                                                    theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                                    style=NAVIGATION_MENU_BUTTON_STYLE,
                                    on_click=lambda _: on_navigate('plant_by_mixture')
                                )
                            ]
                        )
                    ],
                ),
                ft.MenuItemButton(
                    content=ft.Text('Цены смесей', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    style=NAVIGATION_MENU_BUTTON_STYLE,
                    on_click=lambda _: on_navigate('mixtures_prices')
                ),
                ft.MenuItemButton(
                    content=ft.Text('Полный отчёт', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    style=NAVIGATION_MENU_BUTTON_STYLE,
                    on_click=lambda _: on_navigate('general_report')
                ),
                ft.SubmenuButton(
                    content=ft.Text('База данных', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    style=NAVIGATION_MENU_BUTTON_STYLE,
                    controls=[
                        ft.MenuItemButton(content=ft.Text('Импорт', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                                          style=NAVIGATION_MENU_BUTTON_STYLE,
                                          on_click=lambda _: on_navigate('json_db_import')),
                        ft.MenuItemButton(content=ft.Text('Экспорт', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                                          style=NAVIGATION_MENU_BUTTON_STYLE,
                                          on_click=lambda _: on_navigate('json_db_export'))
                    ]
                )
            ],
            **kwargs
        )
