from time import sleep

import flet as ft

from config import BASIC_CONTENT_WIDTH, UNIFIED_BUTTON_STYLE
from database import create_plant_category, db, does_category_exit
from utils.validation import validate_string


class NewCategoryPage(ft.Control):
    """
    A page for adding a new plant category to the database. Validates the
    entered name, checks the uniqueness and saves the instance to the database.
    """
    def __init__(self, page):
        """Initializes the new category creation page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = False

        # named field
        self.category_name_field = ft.TextField(label='Название категории растений', width=BASIC_CONTENT_WIDTH)

        # modal dialog to ask user whether they want to leave the page while there are some filled fields
        self.leaving_dialog = ft.AlertDialog(
            title=ft.Text('Покинуть страницу?'),
            content=ft.Text('Несохранённые данные будут утеряны.', size=16),
            modal=True
        )

        # critical error modal
        self.error_dialog = ft.AlertDialog(
            title=ft.Text('Ошибка', color=ft.Colors.RED),
            content=None,
            modal=True, scrollable=True,
            actions=[ft.ElevatedButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)],
        )

    def build(self):
        """Constructs the page layout."""
        return ft.Container(
            ft.Column([
            ft.Container(ft.Text(
                value='Добавление категории растений',
                theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD
            ), margin=ft.margin.only(bottom=2)),
            self.category_name_field,
            ft.Container(ft.FilledTonalButton(
                'Сохранить', style=UNIFIED_BUTTON_STYLE, on_click=self.validate_and_save_category
            ), margin=ft.margin.only(top=4)),
            self.leaving_dialog,
            ft.Placeholder(self.error_dialog, height=0, fallback_height=0, stroke_width=0)
        ]), alignment=ft.alignment.center, margin=ft.margin.symmetric(vertical=5, horizontal=20))

    def validate_category(self):
        """Validates the entered category name and checks whether it already exists."""
        is_valid = True
        name = self.category_name_field.value

        validation_result = validate_string(name, 'Название категории')

        if not validation_result['success']:
            self.category_name_field.error_text = validation_result['error']
            self.category_name_field.border_color = ft.Colors.RED
            is_valid = False

        else:
            if does_category_exit(name:=name.strip()):
                self.category_name_field.error_text = f'Категория с названием {name} уже существует!'
                self.category_name_field.border_color = ft.Colors.RED
                is_valid = False

            else:
                self.category_name_field.error_text = None
                self.category_name_field.border_color = None

        self.page.update()

        return is_valid, name if is_valid else None

    def validate_and_save_category(self, e):
        """Validates and saves the category instance to the db."""
        is_valid, category_name = self.validate_category()

        if is_valid:
            with db.atomic() as transaction:
                category_creation_result = create_plant_category(name=category_name)

                if not category_creation_result['success']:
                    self.show_error_dialog(text=category_creation_result['error'])
                    transaction.rollback()
                    return

            self.category_name_field.value = None

            snackbar = ft.SnackBar(ft.Text('Категория успешно сохранена в БД.'))
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

    def prevent_leaving(self, navigate_to_leaving_destination):
        """
        Prevents the user from leaving if there are unsaved changes.
        If no unsaved changes exist, navigation proceeds normally. Otherwise, a
        confirmation dialog is shown to prompt the user for confirmation before leaving.
        """
        if not self.category_name_field.value:
            self.ready_to_leave = True
            navigate_to_leaving_destination()
            return

        self.show_leaving_dialog(navigate_to_leaving_destination)

    def show_leaving_dialog(self, navigate_to_leaving_destination):
        """Displays a confirmation dialog when the user attempts to leave with unsaved changes."""
        self.leaving_dialog.actions = [
            ft.TextButton('Да', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.abandon_input_and_leave(navigate_to_leaving_destination)),
            ft.TextButton('Нет', style=UNIFIED_BUTTON_STYLE, on_click=self.close_leaving_dialog)
        ]
        self.leaving_dialog.open = True
        self.leaving_dialog.update()

    def close_leaving_dialog(self, e=None):
        """Closes the leaving confirmation dialog."""
        self.page.close(self.leaving_dialog)
        sleep(0.1)

    def abandon_input_and_leave(self, navigate_to_leaving_destination):
        """
        Discards unsaved changes and proceeds with navigation
        by executing the given navigational function.
        """
        self.ready_to_leave = True
        self.close_leaving_dialog()
        navigate_to_leaving_destination()

    def show_error_dialog(self, text):
        """Displays an error dialog with the given text."""
        self.error_dialog.content = ft.Text(text, size=16)
        self.error_dialog.open = True
        self.error_dialog.update()

    def close_error_dialog(self, e=None):
        """Closes the error dialog."""
        self.error_dialog.open = False
        self.error_dialog.update()
