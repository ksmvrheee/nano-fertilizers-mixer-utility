from decimal import ROUND_HALF_UP
from time import sleep

import flet as ft

from config import BASIC_CONTENT_WIDTH, UNIFIED_BUTTON_STYLE
from database import create_plant, create_fertilizing_episode, db, does_plant_exist, PlantCategory
from utils.event_handlers import filter_non_negative_decimal_input, filter_non_negative_int_input
from utils.utils import get_component_masses, apply_nano_coefficients
from utils.validation import *


class FertilizingEpisodeData:
    """Dataclass for storing the specific fertilizing episode properties."""
    def __init__(self, mass: Decimal, nitrogen: Decimal, phosphorus: Decimal, potassium: Decimal,
                 magnesium_sulfate_mass: Decimal, description: str, reps: int, cleaned_data: dict):
        self.mass = mass
        self.nitrogen = nitrogen
        self.phosphorus = phosphorus
        self.potassium = potassium
        self.magnesium_sulfate_mass = magnesium_sulfate_mass
        self.description = description
        self.reps = reps
        self.cleaned_data = cleaned_data  # the data for prepopulating the fields


class PlantData:
    """Dataclass for storing the specific plant properties."""
    def __init__(self, name: str, nitrogen_percentage: Decimal, phosphorus_percentage: Decimal,
                 potassium_percentage: Decimal, category_id: int):
        self.name = name
        self.nitrogen_percentage = nitrogen_percentage
        self.phosphorus_percentage = phosphorus_percentage
        self.potassium_percentage = potassium_percentage
        self.category_id = category_id
        self.fertilizing_episodes = []

    def append_fertilizing_episode(self, fertilizing_episode: FertilizingEpisodeData) -> None:
        """Appends a new fertilizing episode to the plant's episodes collection."""
        if not isinstance(fertilizing_episode, FertilizingEpisodeData):
            raise TypeError('Wrong data format: expected a FertilizingEpisodeData instance, got '
                            f'{type(fertilizing_episode).__name__} instead.')

        self.fertilizing_episodes.append(fertilizing_episode)

    def clear_fertilizing_episodes(self):
        """Clears the plant fertilizing episodes."""
        self.fertilizing_episodes = []


class NewPlantByNPKPage(ft.Control):
    """
    A page for adding a new plant by providing the N:P:K (nitrogen:phosphorus:potassium) percentages
    as well as the data on each of the [non-nano] fertilizing episodes in a separate modal dialog window.
    """
    def __init__(self, page):
        """Initializes the plant adding page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = False

        # state-related vars
        self.plant_data_object = None
        self.current_episode_number = 0

        # named fields
        self.plant_name_field = ft.TextField(label='Название растения', width=BASIC_CONTENT_WIDTH)

        self.plant_nitrogen_field = ft.TextField(label='Процент азота в базовой смеси',
                                                 on_change=filter_non_negative_decimal_input,
                                                 enable_interactive_selection=False,
                                                 width=BASIC_CONTENT_WIDTH)

        self.plant_phosphorus_field = ft.TextField(label='Процент фосфора в базовой смеси',
                                                   on_change=filter_non_negative_decimal_input,
                                                   enable_interactive_selection=False,
                                                   width=BASIC_CONTENT_WIDTH)

        self.plant_potassium_field = ft.TextField(label='Процент калия в базовой смеси',
                                                  on_change=filter_non_negative_decimal_input,
                                                  enable_interactive_selection=False,
                                                  width=BASIC_CONTENT_WIDTH)

        self.category_dropdown = ft.Dropdown(label='Категория растения', options=[
            ft.dropdown.Option(text=category.name,
                               key=str(category.id))for category in PlantCategory.select().order_by(PlantCategory.name)
        ], width=BASIC_CONTENT_WIDTH / 1.5)

        # critical error modal
        self.error_dialog = ft.AlertDialog(
            title=ft.Text('Ошибка', color=ft.Colors.RED),
            content=None,
            modal=True,
            actions=[ft.FilledTonalButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)],
        )

        # fertilizing modal
        self.episode_column = ft.Column()  # the modal's content
        self.fertilizing_modal = ft.AlertDialog(
            title=ft.Text('Добавить подкормки'),
            content=ft.Column(
                [self.episode_column, ft.Placeholder(self.error_dialog, height=0, fallback_height=0, stroke_width=0)]
            ),
            actions=[
                ft.Row([
                    ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE, on_click=self.abort_episodes_and_close_modal),
                    ft.Row([
                        ft.TextButton('Сохранить', style=UNIFIED_BUTTON_STYLE, on_click=self.save_plant_and_episodes),
                        ft.TextButton('Далее', style=UNIFIED_BUTTON_STYLE,
                                      on_click=self.append_fertilizing_data_and_add_form),
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],
            modal=True, scrollable=True
        )
        self.page.overlay.append(self.fertilizing_modal)

        # modal fields refs
        self.fertilizing_mass_field_ref = ft.Ref[ft.TextField]()
        self.fertilizing_mass_multiplier_field_ref = ft.Ref[ft.TextField]()
        self.fertilizing_magnesium_sulfate_mass_field_ref = ft.Ref[ft.TextField]()
        self.fertilizing_life_stage_field_ref = ft.Ref[ft.TextField]()
        self.fertilizing_reps_field_ref = ft.Ref[ft.TextField]()

        # modal dialog to ask user whether they want to leave the page while there are some filled fields
        self.leaving_dialog = ft.AlertDialog(
            title=ft.Text('Покинуть страницу?'),
            content=ft.Text('Несохранённые данные будут утеряны.', size=16),
            modal=True
        )

    def build(self):
        """Constructs the page layout."""
        return ft.Container(ft.Column([
            ft.Container(ft.Text(
                'Добавление растения',
                theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                weight=ft.FontWeight.BOLD
            ), margin=ft.margin.only(bottom=2)),
            self.plant_name_field,
            self.plant_nitrogen_field,
            self.plant_phosphorus_field,
            self.plant_potassium_field,
            self.category_dropdown,
            ft.Container(ft.FilledTonalButton(
                'Добавить подкормки', style=UNIFIED_BUTTON_STYLE, on_click=self.validate_and_open_modal
            ), margin=ft.margin.only(top=4)),
            self.leaving_dialog,
        ]), alignment=ft.alignment.center, margin=ft.margin.symmetric(vertical=5, horizontal=20))

    def validate_plant_data(self):
        """
        Validates the data about a plant. Returns a tuple of a bool value indicating the
        validness of the data and the dict containing the cleaned data if the data is valid.
        """
        is_valid = True
        cleaned_data = {}

        name = self.plant_name_field.value
        validation_result = validate_string(name, 'Название растения', gender='n')
        if not validation_result['success']:
            self.plant_name_field.error_text = validation_result['error']
            self.plant_name_field.border_color = ft.Colors.RED
            is_valid = False
        else:
            if does_plant_exist(name := name.strip()):
                self.plant_name_field.error_text = f'Растение с именем {name} уже существует!'
                self.plant_name_field.border_color = ft.Colors.RED
                is_valid = False
            else:
                self.plant_name_field.error_text = None
                self.plant_name_field.border_color = None
                cleaned_data['name'] = name

        for field, value_str, field_name, key in [
            (self.plant_nitrogen_field, self.plant_nitrogen_field.value, 'Процент азота', 'nitrogen'),
            (self.plant_phosphorus_field, self.plant_phosphorus_field.value, 'Процент фосфора', 'phosphorus'),
            (self.plant_potassium_field, self.plant_potassium_field.value, 'Процент калия', 'potassium')
        ]:
            validation_result = validate_percentage_string(value_str, field_name=field_name)
            if validation_result['success']:
                field.error_text = None
                field.border_color = None
                cleaned_data[key] = validation_result['value']
            else:
                field.error_text = validation_result['error']
                field.border_color = ft.Colors.RED
                is_valid = False

        category_id = self.category_dropdown.value
        if category_id in ('', None):
            self.category_dropdown.error_text = 'Необходимо выбрать категорию растения.'
            self.category_dropdown.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.category_dropdown.error_text = None
            self.category_dropdown.border_color = None
            cleaned_data['category_id'] = int(category_id)

        self.page.update()

        return is_valid, cleaned_data if is_valid else None

    def validate_and_open_modal(self, e):
        """
        Calls the plant data validation method and opens the
        fertilizing episodes adding modal if the data is valid.
        """
        is_valid, cleaned_data = self.validate_plant_data()

        if is_valid:
            self.plant_data_object = PlantData(
                name=cleaned_data['name'],
                nitrogen_percentage=cleaned_data['nitrogen'],
                phosphorus_percentage=cleaned_data['phosphorus'],
                potassium_percentage=cleaned_data['potassium'],
                category_id=cleaned_data['category_id']
            )

            self.add_new_fertilizing_form()

            self.page.open(self.fertilizing_modal)
            self.page.update()

    def add_new_fertilizing_form(self):
        """
        Updates the form fields inside the fertilizing episode
        adding modal depending on the number of the current episode.
        """
        if not self.current_episode_number:
            new_episode_form = ft.Column([
                ft.Text('Подкормка №1', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.TextField(label='Масса подкормки (г / 10 л)', ref=self.fertilizing_mass_field_ref,
                             on_change=filter_non_negative_decimal_input, enable_interactive_selection=False,
                             width=BASIC_CONTENT_WIDTH),

                ft.TextField(label='Масса сульфата магния (г)', ref=self.fertilizing_magnesium_sulfate_mass_field_ref,
                             on_change=filter_non_negative_decimal_input, enable_interactive_selection=False,
                             width=BASIC_CONTENT_WIDTH),

                ft.TextField(label='Стадия жизненного цикла растения', ref=self.fertilizing_life_stage_field_ref,
                             width=BASIC_CONTENT_WIDTH),

                ft.TextField(label='Количество повторений', ref=self.fertilizing_reps_field_ref,
                             on_change=filter_non_negative_int_input, width=BASIC_CONTENT_WIDTH)
            ],
            width=400)

        else:
            new_episode_form = ft.Column([
                ft.Text(f'Подкормка №{self.current_episode_number + 1}', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.TextField(label='Множитель массы (отн. предыдущей)', ref=self.fertilizing_mass_multiplier_field_ref,
                             on_change=filter_non_negative_decimal_input, enable_interactive_selection=False,
                             width=BASIC_CONTENT_WIDTH),

                ft.TextField(label='Масса сульфата магния (г)', ref=self.fertilizing_magnesium_sulfate_mass_field_ref,
                             on_change=filter_non_negative_decimal_input, enable_interactive_selection=False,
                             width=BASIC_CONTENT_WIDTH),

                ft.TextField(label='Стадия жизненного цикла растения', ref=self.fertilizing_life_stage_field_ref),

                ft.TextField(label='Количество повторений', ref=self.fertilizing_reps_field_ref,
                             on_change=filter_non_negative_int_input, width=BASIC_CONTENT_WIDTH)
            ],
            width=400)

        self.episode_column.controls = [new_episode_form]
        self.fertilizing_modal.update()

    def validate_fertilizing_data(self):
        """
        Validates the data about a fertilizing episode. Returns a tuple of a bool value indicating
        the validness of the data and the dict containing the cleaned data if the data is valid.
        """
        is_valid = True
        cleaned_data = {}

        if not self.current_episode_number:
            validation_result = validate_decimal_string(
                self.fertilizing_mass_field_ref.current.value,
                field_name='Масса подкормки',
                min_value=0.01,
                max_decimals=2,
                gender='f'
            )
            if validation_result['success']:
                cleaned_data['mass'] = validation_result['value']
                self.fertilizing_mass_field_ref.current.error_text = None
                self.fertilizing_mass_field_ref.current.border_color = None
            else:
                self.fertilizing_mass_field_ref.current.error_text = validation_result['error']
                self.fertilizing_mass_field_ref.current.border_color = ft.Colors.RED
                is_valid = False
        else:
            validation_result = validate_decimal_string(
                self.fertilizing_mass_multiplier_field_ref.current.value,
                field_name='Множитель массы',
                min_value=0.01,
                max_decimals=2,
                gender='m'
            )
            if validation_result['success']:
                cleaned_data['mass_multiplier'] = validation_result['value']
                self.fertilizing_mass_multiplier_field_ref.current.error_text = None
                self.fertilizing_mass_multiplier_field_ref.current.border_color = None
            else:
                self.fertilizing_mass_multiplier_field_ref.current.error_text = validation_result['error']
                self.fertilizing_mass_multiplier_field_ref.current.border_color = ft.Colors.RED
                is_valid = False

        validation_result = validate_decimal_string(
            self.fertilizing_magnesium_sulfate_mass_field_ref.current.value,
            field_name='Масса MgS',
            min_value=0,
            max_decimals=2,
            gender='f'
        )
        if validation_result['success']:
            cleaned_data['magnesium_sulfate_mass'] = validation_result['value']
            self.fertilizing_magnesium_sulfate_mass_field_ref.current.error_text = None
            self.fertilizing_magnesium_sulfate_mass_field_ref.current.border_color = None
        else:
            self.fertilizing_magnesium_sulfate_mass_field_ref.current.error_text = validation_result['error']
            self.fertilizing_magnesium_sulfate_mass_field_ref.current.border_color = ft.Colors.RED
            is_valid = False

        validation_result = validate_string(self.fertilizing_life_stage_field_ref.current.value,
                                            'Описание стадии', gender='n')
        if validation_result['success']:
            cleaned_data['description'] = self.fertilizing_life_stage_field_ref.current.value.strip()
            self.fertilizing_life_stage_field_ref.current.error_text = None
            self.fertilizing_life_stage_field_ref.current.border_color = None
        else:
            self.fertilizing_life_stage_field_ref.current.error_text = validation_result['error']
            self.fertilizing_life_stage_field_ref.current.border_color = ft.Colors.RED
            is_valid = False

        validation_result = validate_positive_integer_string(
            self.fertilizing_reps_field_ref.current.value,
            field_name='Количество повторений',
            gender='n'
        )
        if validation_result['success']:
            cleaned_data['reps'] = int(validation_result['value'])
            self.fertilizing_reps_field_ref.current.error_text = None
            self.fertilizing_reps_field_ref.current.border_color = None
        else:
            self.fertilizing_reps_field_ref.current.error_text = validation_result['error']
            self.fertilizing_reps_field_ref.current.border_color = ft.Colors.RED
            is_valid = False

        self.fertilizing_modal.update()

        return is_valid, cleaned_data if is_valid else None

    def append_fertilizing_data(self):
        """
        Calls the fertilizing episode validation method and then calculates the absolute
        episode component masses, applies the nano-coefficients and appends the data to the
        dataclass if the data is valid. Returns a bool value indicating if the data was appended.
        """
        is_valid, cleaned_data = self.validate_fertilizing_data()

        data_appended = False

        if is_valid:
            if self.plant_data_object is None or not hasattr(self.plant_data_object, 'fertilizing_episodes'):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')

            else:
                if not self.current_episode_number:
                    total_fertilizing_mass = cleaned_data['mass']

                else:
                    last_fertilizing_mass = self.plant_data_object.fertilizing_episodes[-1].mass
                    total_fertilizing_mass = ((cleaned_data['mass_multiplier'] * last_fertilizing_mass)
                                              .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

                component_masses = get_component_masses(
                    n_percentage=self.plant_data_object.nitrogen_percentage,
                    p_percentage=self.plant_data_object.phosphorus_percentage,
                    k_percentage=self.plant_data_object.potassium_percentage,
                    total_mass=total_fertilizing_mass
                )

                apply_nano_coefficients(component_masses)

                fertilizing_episode = FertilizingEpisodeData(
                    mass=total_fertilizing_mass,
                    nitrogen=component_masses['N'],
                    phosphorus=component_masses['P'],
                    potassium=component_masses['K'],
                    magnesium_sulfate_mass=cleaned_data['magnesium_sulfate_mass'],
                    description=cleaned_data['description'],
                    reps=cleaned_data['reps'],
                    cleaned_data=cleaned_data
                )

                self.plant_data_object.append_fertilizing_episode(fertilizing_episode)
                data_appended = True

        return data_appended

    def append_fertilizing_data_and_add_form(self, e):
        """Calls the fertilizing episode data appending method and adds a new form if the data was appended."""
        result = self.append_fertilizing_data()

        if result:
            self.fertilizing_modal.actions[0].controls[0] = ft.Row([
                ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE, on_click=self.abort_episodes_and_close_modal),
                ft.TextButton('Назад', style=UNIFIED_BUTTON_STYLE, on_click=self.undo_episode_appending)
            ])

            self.current_episode_number += 1
            self.add_new_fertilizing_form()

    def save_plant_and_episodes(self, e):
        """Saves the plant and it's fertilizing episodes to the db using a singular transaction."""
        if self.append_fertilizing_data():
            with db.atomic() as transaction:
                plant_creation_result = create_plant(
                    name=self.plant_data_object.name,
                    category_id=self.plant_data_object.category_id
                )

                if not plant_creation_result['success']:
                    self.show_error_dialog(text=plant_creation_result['error'])
                    transaction.rollback()
                    return

                plant_id = plant_creation_result['plant_id']

                for episode in self.plant_data_object.fertilizing_episodes:
                    fertilizing_creation_result = create_fertilizing_episode(
                        plant_id=plant_id,
                        nitrogen_mass=episode.nitrogen,
                        phosphorus_mass=episode.phosphorus,
                        potassium_mass=episode.potassium,
                        magnesium_sulfate_mass=episode.magnesium_sulfate_mass,
                        plant_life_stage_description=episode.description,
                        total_repetitions=episode.reps
                    )

                    if not fertilizing_creation_result['success']:
                        self.plant_data_object.fertilizing_episodes.pop()
                        self.show_error_dialog(text=fertilizing_creation_result['error'])
                        transaction.rollback()
                        return

            self.abort_episodes_and_close_modal(e)
            self.clear_plant_state()

            snackbar = ft.SnackBar(ft.Text('Растение и подкормки успешно сохранены в БД.'))
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
            
    def undo_episode_appending(self, e):
        """
        Restores the previous episode data in the input fields depending on the episode number.
        Completely wipes the current populated episode data from the fields and the data object.
        """
        if self.plant_data_object is None or not len(self.plant_data_object.fertilizing_episodes):
            self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
            return

        restoring_episode = self.plant_data_object.fertilizing_episodes.pop()

        self.current_episode_number -= 1
        first_episode_reached = not self.current_episode_number
        self.add_new_fertilizing_form()

        if first_episode_reached:
            self.fertilizing_mass_field_ref.current.value = str(restoring_episode.cleaned_data['mass'])
        else:
            self.fertilizing_mass_multiplier_field_ref.current.value = str(
                restoring_episode.cleaned_data['mass_multiplier']
            )

        self.fertilizing_magnesium_sulfate_mass_field_ref.current.value = str(
            restoring_episode.cleaned_data['magnesium_sulfate_mass']
        )
        self.fertilizing_life_stage_field_ref.current.value = str(
            restoring_episode.cleaned_data['description']
        )
        self.fertilizing_reps_field_ref.current.value =str(restoring_episode.cleaned_data['reps'])

        if first_episode_reached:
            self.fertilizing_modal.actions[0].controls[0] = ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE,
                                                                          on_click=self.abort_episodes_and_close_modal)
        self.fertilizing_modal.update()

    def clear_plant_state(self):
        """Clears the states of the plant and the page."""
        self.current_episode_number = 0
        self.plant_data_object = None
        self.plant_name_field.value = None
        self.plant_nitrogen_field.value = None
        self.plant_phosphorus_field.value = None
        self.plant_potassium_field.value = None
        self.category_dropdown.value = None

        self.page.update()

    def abort_episodes_and_close_modal(self, e):
        """Aborts the added fertilizing episodes and closes the modal dialog."""
        if self.plant_data_object is not None:
            self.plant_data_object.clear_fertilizing_episodes()

        self.current_episode_number = 0
        self.fertilizing_modal.actions[0].controls[0] = ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE,
                                                                      on_click=self.abort_episodes_and_close_modal)

        self.page.close(self.fertilizing_modal)
        self.page.update()

    def prevent_leaving(self, navigate_to_leaving_destination):
        """
        Prevents the user from leaving if there are unsaved changes.
        If no unsaved changes exist, navigation proceeds normally. Otherwise, a
        confirmation dialog is shown to prompt the user for confirmation before leaving.
        """
        if not any(field.value for field in (self.plant_name_field, self.plant_nitrogen_field,
                                             self.plant_phosphorus_field, self.plant_potassium_field)):
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
