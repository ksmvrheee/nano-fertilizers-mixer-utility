from time import sleep

import flet as ft
from peewee import IntegrityError, OperationalError, DatabaseError

from config import PAGE_MIN_HEIGHT, UNIFIED_BUTTON_STYLE
from database import FertilizingMixture, db


class MixturesPricesPage(ft.Control):
    """
    A page for viewing and modifying the prices of the fertilizing mixtures.
    User can increase, decrease, or manually edit the price per gram of each mixture.
    Changes are saved to the database in batch mode, and users are prompted to confirm
    or discard modifications before leaving the page.
    """
    def __init__(self, page):
        """Initializes the mixtures prices management page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = False

        # collection representing the actual data that was loaded or saved
        self.actual_data = {}

        # collection representing the mixtures and changes in their prices to be commited to the db
        self.prices_changes_to_commit = {}

        # gradation of the price change (up and down)
        self.price_step = 0.01

        # flag that shows whether the save/discard buttons are shown atm
        self.buttons_emerged = False

        # main container to display the elements
        self.list_view_height_offset = 195
        self.list_view = ft.ListView(spacing=10, expand=True, expand_loose=True)

        # container to display the Save/Discard buttons
        self.buttons_container_ref = ft.Ref[ft.Container]()
        self.buttons_container_height = 60

        # indentation to maintain from the left and right edges
        self.gutter_width = 35

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
            modal=True,
            scrollable=True,
            actions=[ft.ElevatedButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)]
        )

        self.load_mixtures()

    def build(self):
        """Constructs the initial page layout."""
        return ft.Container(ft.Column([
            ft.Container(
                ft.Text(value='Изменение цены за грамм удобрения',
                        theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD),
                alignment=ft.alignment.center, margin=ft.margin.only(top=2)
            ),
            ft.Container(
                content=self.list_view,
                height=self.page.window.height - self.list_view_height_offset,
                margin=ft.margin.symmetric(horizontal=self.gutter_width),
                alignment=ft.alignment.center
            ),
            ft.Container(height=0, visible=False, ref=self.buttons_container_ref),
            self.leaving_dialog,
            self.error_dialog
        ]), alignment=ft.alignment.center, margin=ft.margin.symmetric(vertical=5, horizontal=20))

    def load_mixtures(self):
        """Loads the list of fertilizing mixtures from the database and updates the UI."""
        self.actual_data = {}
        self.prices_changes_to_commit = {}
        self.list_view.controls.clear()

        mixtures = FertilizingMixture.select(FertilizingMixture.id, FertilizingMixture.name,
                                             FertilizingMixture.price_per_gram).order_by(FertilizingMixture.name)

        if not len(mixtures):
            self.list_view.controls.append(
                ft.Container(
                    ft.Text('Данные не найдены', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    margin=ft.margin.only(top=PAGE_MIN_HEIGHT//3),
                    alignment=ft.alignment.center
                )
            )

        else:
            for mixture in mixtures:
                self.actual_data[mixture.id] = float(mixture.price_per_gram)
                self.list_view.controls.append(self.create_mixture_card(mixture))

        self.page.update()

    def create_mixture_card(self, mixture):
        """Creates a UI card for a single mixture with price modification controls."""
        return ft.Container(ft.Row([
            ft.Text(mixture.name, theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
            ft.Row([
                ft.Container(
                    ft.IconButton(icon=ft.Icons.ADD, on_click=lambda e: self.increase_price(e, mixture_id=mixture.id)),
                    margin=ft.margin.symmetric(horizontal=5)
                ),
                ft.TextField(
                    value=mixture.price_per_gram, text_align=ft.TextAlign.CENTER, width=75,
                    on_change=lambda e: self.manually_change_price(e, mixture_id=mixture.id)
                ),
                ft.Container(
                    ft.IconButton(icon=ft.Icons.REMOVE,
                                  on_click=lambda e: self.decrease_price(e, mixture_id=mixture.id)),
                    margin=ft.margin.symmetric(horizontal=5)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

    def increase_price(self, e, *, mixture_id):
        """Increases the price of a mixture by `price_step`."""
        price_input_field = e.control.parent.parent.controls[1]

        try:
            increased_price = round(float(price_input_field.value) + self.price_step, 2)
            price_input_field.value = increased_price
            price_input_field.update()

        except ValueError:
            return

        current_price_delta = self.prices_changes_to_commit.get(mixture_id, None)
        price_was_changed_before = current_price_delta is not None

        if price_was_changed_before:
            new_price_delta = round(current_price_delta + self.price_step, 2)

            if not new_price_delta:
                del self.prices_changes_to_commit[mixture_id]
                if not self.prices_changes_to_commit and self.buttons_emerged:
                    self.conceal_control_buttons()

            else:
                self.prices_changes_to_commit[mixture_id] = new_price_delta
                if not self.buttons_emerged:
                    self.emerge_control_buttons()

        else:
            self.prices_changes_to_commit[mixture_id] = round(self.price_step, 2)
            if not self.buttons_emerged:
                self.emerge_control_buttons()

    def decrease_price(self, e, *, mixture_id):
        """Decreases the price of a mixture by `price_step`, ensuring it doesn't go below zero."""
        price_input_field = e.control.parent.parent.controls[1]

        try:
            decreased_price = round(float(price_input_field.value) - self.price_step, 2)
            if decreased_price < 0:
                return

            price_input_field.value = decreased_price
            price_input_field.update()

        except ValueError:
            return

        current_price_delta = self.prices_changes_to_commit.get(mixture_id, None)
        price_was_changed_before = current_price_delta is not None

        if price_was_changed_before:
            new_price_delta = round(current_price_delta - self.price_step, 2)

            if not new_price_delta:
                del self.prices_changes_to_commit[mixture_id]
                if not self.prices_changes_to_commit and self.buttons_emerged:
                    self.conceal_control_buttons()

            else:
                self.prices_changes_to_commit[mixture_id] = new_price_delta
                if not self.buttons_emerged:
                    self.emerge_control_buttons()

        else:
            self.prices_changes_to_commit[mixture_id] = round(0 - self.price_step, 2)
            if not self.buttons_emerged:
                self.emerge_control_buttons()

    def manually_change_price(self, e, *, mixture_id):
        """Handles manual user input in the price field, ensuring valid formatting."""
        # cleaning the value up first to get a convertable string
        old_value = e.control.value
        new_value = []
        digit_encountered = False
        point_encountered = False
        decimal_part_length = 0

        for char in old_value:
            if char.isdigit():
                digit_encountered = True

                if not point_encountered:
                    new_value.append(char)

                elif decimal_part_length < 2:
                    decimal_part_length += 1
                    new_value.append(char)

            elif char in ('.', ',') and not point_encountered:
                point_encountered = True
                new_value.append('.')

        clean_value_str = ''.join(new_value)
        e.control.value = clean_value_str
        e.control.update()
        
        # exiting if cannot convert
        if not digit_encountered:
            return

        # converting the value
        clean_value =  float(clean_value_str)

        actual_price = self.actual_data[mixture_id]
        price_delta = round(clean_value - actual_price, 2)
        price_was_changed_before = mixture_id in self.prices_changes_to_commit

        if not price_delta and price_was_changed_before:
            del self.prices_changes_to_commit[mixture_id]
            if not self.prices_changes_to_commit and self.buttons_emerged:
                self.conceal_control_buttons()

        elif price_delta:
            self.prices_changes_to_commit[mixture_id] = price_delta
            if not self.buttons_emerged:
                self.emerge_control_buttons()

    def emerge_control_buttons(self):
        """Displays the Save and Discard buttons when there are pending changes."""
        list_view_container = self.list_view.parent
        list_view_container.height -= self.buttons_container_height
        list_view_container.margin = ft.margin.only(left=self.gutter_width, right=self.gutter_width, bottom=-5)

        self.buttons_container_ref.current.content = ft.Row(
            controls=[
                ft.FilledTonalButton('Сохранить', style=UNIFIED_BUTTON_STYLE, on_click=self.save_changes),
                ft.FilledTonalButton('Отменить', style=UNIFIED_BUTTON_STYLE, on_click=self.discard_changes)
            ], spacing=15,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.buttons_container_ref.current.height = self.buttons_container_height
        self.buttons_container_ref.current.margin = ft.margin.only(right=self.gutter_width)
        self.buttons_container_ref.current.visible = True

        self.buttons_emerged = True

        self.page.update()

    def conceal_control_buttons(self):
        """Hides the Save and Discard buttons when there are no pending changes."""
        list_view_container = self.list_view.parent
        list_view_container.height += self.buttons_container_height
        list_view_container.margin = ft.margin.symmetric(horizontal=self.gutter_width)

        self.buttons_container_ref.current.height = 0
        self.buttons_container_ref.current.content = None
        self.buttons_container_ref.current.margin = None
        self.buttons_container_ref.current.visible = False

        self.buttons_emerged = False

        self.page.update()

    def discard_changes(self, e):
        """Discards all unsaved changes and reloads the mixture data."""
        self.conceal_control_buttons()
        self.load_mixtures()

    def save_changes(self, e):
        """
        Saves the modified mixture prices to the database.
        Handles potential database errors and provides user feedback via dialogs.
        """
        try:
            with db.atomic():
                for mixture_id in self.prices_changes_to_commit:
                    past_price = self.actual_data[mixture_id]
                    price_delta = self.prices_changes_to_commit[mixture_id]
                    actual_price = round(past_price + price_delta, 2)

                    FertilizingMixture.update(
                        price_per_gram=actual_price
                    ).where(FertilizingMixture.id == mixture_id).execute()

            self.conceal_control_buttons()
            self.load_mixtures()

            snackbar = ft.SnackBar(ft.Text('Цены успешно обновлены в БД.'), duration=1500)
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

        except IntegrityError as e:
            self.show_error_dialog(text=f'Ошибка целостности данных: {e}')

        except OperationalError as e:
            self.show_error_dialog(text=f'Ошибка выполнения операции: {e}')

        except DatabaseError as e:
            self.show_error_dialog(text=f'Общая ошибка базы данных: {e}')

    def prevent_leaving(self, navigate_to_leaving_destination):
        """
        Prevents the user from leaving if there are unsaved changes.
        If no unsaved changes exist, navigation proceeds normally. Otherwise, a
        confirmation dialog is shown to prompt the user for confirmation before leaving.
        """
        if not self.prices_changes_to_commit:
            self.ready_to_leave = True
            navigate_to_leaving_destination()
            return

        self.show_leaving_dialog(navigate_to_leaving_destination)

    def show_leaving_dialog(self, navigate_to_leaving_destination):
        """Displays a confirmation dialog when the user attempts to leave with unsaved changes."""
        self.leaving_dialog.actions = [
            ft.TextButton('Да', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.abandon_inputs_and_leave(navigate_to_leaving_destination)),
            ft.TextButton('Нет', style=UNIFIED_BUTTON_STYLE, on_click=self.close_leaving_dialog)
        ]
        self.leaving_dialog.open = True
        self.leaving_dialog.update()

    def close_leaving_dialog(self, e=None):
        """Closes the leaving confirmation dialog."""
        self.page.close(self.leaving_dialog)
        sleep(0.1)

    def abandon_inputs_and_leave(self, navigate_to_leaving_destination):
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