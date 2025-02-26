from decimal import Decimal, ROUND_HALF_UP
from time import sleep

import flet as ft

from config import BASIC_CONTENT_WIDTH, UNIFIED_BUTTON_STYLE
from database import PlantCategory, FertilizingMixture, does_plant_exist, db, create_plant, create_fertilizing_episode
from utils.event_handlers import filter_non_negative_int_input, filter_non_negative_decimal_input
from utils.utils import get_component_masses, apply_nano_coefficients
from utils.validation import validate_string, validate_decimal_string, validate_positive_integer_string


class ComponentData:
    """Dataclass for storing the specific mixture component properties."""
    def __init__(self, fertilizing_mixture_id: int, mass: Decimal):
        self.fertilizing_mixture_id = fertilizing_mixture_id
        self.mass = mass


class FertilizingEpisodeData:
    """Dataclass for storing the specific fertilizing episode properties."""
    def __init__(self, description: str, magnesium_sulfate_mass: Decimal, reps: int):
        self.description = description
        self.magnesium_sulfate_mass = magnesium_sulfate_mass
        self.reps = reps
        self.components = []

    def append_component(self, component: ComponentData) -> None:
        """Appends a new component to the episode's components collection."""
        if not isinstance(component, ComponentData):
            raise TypeError('Wrong data format: expected a ComponentData instance, got '
                            f'{type(component).__name__} instead.')

        self.components.append(component)


class PlantData:
    """Dataclass for storing the specific plant properties."""
    def __init__(self, name: str, category_id: int):
        self.name = name
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


class NewPlantByMixturePage(ft.Control):
    """
    A page for adding a new plant by providing the composition of the predefined fertilizing
    mixtures and their masses in the desired [non-nano-capsuled] fertilizing mixture for the
    plant. Includes adding the plant's fertilizing episodes and their metadata separately.
    """
    def __init__(self, page):
        """Initializes the plant adding page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = False

        # state-related vars
        self.plant_data_object = None
        self.current_episode_number = None
        self.current_component_number = None

        # named labels
        self.heading_label = ft.Text('Добавление растения',
                                     theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD)

        self.plant_name_label = ft.Text(theme_style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD)

        self.subheading_label = ft.Text(theme_style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)

        # named fields
        self.plant_name_field = ft.TextField(label='Название растения', width=BASIC_CONTENT_WIDTH)

        self.plant_category_dropdown = ft.Dropdown(label='Категория растения', options=[
            ft.dropdown.Option(text=category.name,
                               key=str(category.id)) for category in PlantCategory.select().order_by(PlantCategory.name)
        ], width=BASIC_CONTENT_WIDTH / 1.5)

        self.fertilizing_life_stage_description_field = ft.TextField(label='Стадия жизненного цикла растения',
                                                                     width=BASIC_CONTENT_WIDTH)

        self.fertilizing_reps_field = ft.TextField(label='Количество повторений',
                                                   on_change=filter_non_negative_int_input, width=BASIC_CONTENT_WIDTH)

        self.fertilizing_magnesium_sulfate_mass_field = ft.TextField(label='Масса сульфата магния (г)',
                                                                     on_change=filter_non_negative_decimal_input,
                                                                     enable_interactive_selection=False,
                                                                     width=BASIC_CONTENT_WIDTH)

        self.component_mass_field = ft.TextField(label='Масса удобрения (г)',
                                                 on_change=filter_non_negative_decimal_input,
                                                 enable_interactive_selection=False,
                                                 width=BASIC_CONTENT_WIDTH / 2.3)

        self.component_dropdown = ft.Dropdown(label='Удобрение', options=[ft.dropdown.Option(
            text=mixture_unit.name, key=str(mixture_unit.id))
            for mixture_unit in (FertilizingMixture.select()
                                 .where(FertilizingMixture.name != 'Сульфат магния')
                                 .order_by(FertilizingMixture.name))], width=BASIC_CONTENT_WIDTH / 2)

        # named buttons
        self.add_fertilizing_episodes_button = ft.FilledTonalButton(
            'Добавить подкормки', style=UNIFIED_BUTTON_STYLE, on_click=self.append_plant_metadata_and_update_layout
        )
        self.proceed_to_adding_components_button = ft.FilledTonalButton(
            'Далее', style=UNIFIED_BUTTON_STYLE, on_click=self.append_fertilizing_metadata_and_update_layout
        )
        self.add_next_fertilizing_episode_button = ft.FilledTonalButton(
            'Следующая подкормка', style=UNIFIED_BUTTON_STYLE, on_click=self.append_last_component_and_update_layout
        )
        self.add_next_component_button = ft.FilledTonalButton(
            'Следующее удобрение', style=UNIFIED_BUTTON_STYLE, on_click=self.append_component_and_update_layout
        )
        self.save_button = ft.FilledTonalButton('Сохранить', style=UNIFIED_BUTTON_STYLE, on_click=self.save_all_data)
        self.back_button = ft.FilledTonalButton('Назад', style=UNIFIED_BUTTON_STYLE, on_click=self.go_back)

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
            actions=[ft.FilledTonalButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)],
        )

        # pre-defined views
        self.plant_metadata_view = (
            ft.Container(self.heading_label, margin=ft.margin.only(bottom=2)),
            self.plant_name_field,
            self.plant_category_dropdown,
            ft.Container(self.add_fertilizing_episodes_button, margin=ft.margin.only(top=4)),
            self.error_dialog,
            self.leaving_dialog
        )

        self.fertilizing_metadata_view = (
            self.heading_label,
            self.plant_name_label,
            ft.Container(self.subheading_label, margin=ft.margin.only(bottom=2)),
            self.fertilizing_life_stage_description_field,
            self.fertilizing_magnesium_sulfate_mass_field,
            self.fertilizing_reps_field,
            ft.Container(
                ft.Row([
                    self.back_button,
                    self.proceed_to_adding_components_button
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                width=BASIC_CONTENT_WIDTH, margin=ft.margin.only(top=4)
            ),
            self.error_dialog,
            self.leaving_dialog
        )

        self.components_adding_view = (
            self.heading_label,
            self.plant_name_label,
            self.subheading_label,
            ft.Container(
                ft.Row([
                    ft.Row([
                        self.component_dropdown,
                        ft.Text(',', theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.W_500)
                    ], spacing=4),
                    self.component_mass_field,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                width=BASIC_CONTENT_WIDTH, margin=ft.margin.only(top=2, bottom=4)
            ),
            ft.Container(
                ft.Row([self.add_next_fertilizing_episode_button, self.add_next_component_button],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                width=BASIC_CONTENT_WIDTH, margin=ft.margin.only(bottom=4)
            ),
            ft.Container(
                ft.Row([self.back_button, self.save_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                width=BASIC_CONTENT_WIDTH
            ),
            self.error_dialog,
            self.leaving_dialog
        )

        # main content container with the initial view's content
        self.content_container = ft.Container(
            ft.Column(controls=self.plant_metadata_view),
            margin=ft.margin.symmetric(vertical=5)
        )

    def build(self):
        """Constructs the page layout."""
        # (this atrocity is needed to ensure the central positioning with a complex layout)
        return ft.Column([ft.Row([self.content_container], alignment=ft.MainAxisAlignment.CENTER)])

    def validate_plant_metadata(self):
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
                cleaned_data['name'] = name.capitalize()

        category_id = self.plant_category_dropdown.value
        if category_id in ('', None):
            self.plant_category_dropdown.error_text = 'Необходимо выбрать категорию растения.'
            self.plant_category_dropdown.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.plant_category_dropdown.error_text = None
            self.plant_category_dropdown.border_color = None
            cleaned_data['category_id'] = int(category_id)

        self.content_container.update()

        return is_valid, cleaned_data if is_valid else None

    def append_plant_metadata_and_update_layout(self, e):
        """
        Calls the plant validation method and appends the data to the dataclass if the data is
        valid, then updates the layout. Returns a bool value indicating if the data was appended.
        """
        is_valid, cleaned_data = self.validate_plant_metadata()

        if is_valid:
            self.plant_data_object = PlantData(
                name=cleaned_data['name'],
                category_id=cleaned_data['category_id']
            )

            self.heading_label.value += ':'
            self.plant_name_label.value = f'"{cleaned_data["name"]}"'

            self.current_episode_number = 1
            self._compose_subheading_label()

            self.plant_name_field.value = None
            self.plant_category_dropdown.value = ''

            self.content_container.content.controls = self.fertilizing_metadata_view
            self.content_container.update()

    def validate_fertilizing_metadata(self):
        """
        Validates the data about a fertilizing episode. Returns a tuple of a bool value indicating
        the validness of the data and the dict containing the cleaned data if the data is valid.
        """
        is_valid = True
        cleaned_data = {}

        description = self.fertilizing_life_stage_description_field.value
        validation_result = validate_string(description, 'Описание стадии', gender='n')
        if not validation_result['success']:
            self.fertilizing_life_stage_description_field.error_text = validation_result['error']
            self.fertilizing_life_stage_description_field.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.fertilizing_life_stage_description_field.error_text = None
            self.fertilizing_life_stage_description_field.border_color = None
            cleaned_data['description'] = description.strip()

        magnesium_sulfate_mass = self.fertilizing_magnesium_sulfate_mass_field.value
        validation_result = validate_decimal_string(
            magnesium_sulfate_mass,
            field_name='Масса MgS',
            min_value=0,
            max_decimals=2,
            gender='f'
        )
        if not validation_result['success']:
            self.fertilizing_magnesium_sulfate_mass_field.error_text = validation_result['error']
            self.fertilizing_magnesium_sulfate_mass_field.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.fertilizing_magnesium_sulfate_mass_field.error_text = None
            self.fertilizing_magnesium_sulfate_mass_field.border_color = None
            cleaned_data['magnesium_sulfate_mass'] = validation_result['value']

        reps = self.fertilizing_reps_field.value
        validation_result = validate_positive_integer_string(reps, field_name='Количество повторений', gender='n')
        if not validation_result['success']:
            self.fertilizing_reps_field.error_text = validation_result['error']
            self.fertilizing_reps_field.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.fertilizing_reps_field.error_text = None
            self.fertilizing_reps_field.border_color = None
            cleaned_data['reps'] = validation_result['value']

        self.content_container.update()

        return is_valid, cleaned_data if is_valid else None

    def _compose_subheading_label(self):
        """Composes the subheading label depending on a context."""
        if self.current_episode_number is not None:
            self.subheading_label.value = f'Подкормка №{self.current_episode_number}'

        if self.current_component_number is not None:
            self.subheading_label.value += f',  удобрение №{self.current_component_number}'

    def append_fertilizing_metadata_and_update_layout(self, e):
        """
        Calls the fertilizing episode validation method and then appends the data to the dataclass if the
        data is valid, then updates the layout. Returns a bool value indicating if the data was appended.
        """
        is_valid, cleaned_data = self.validate_fertilizing_metadata()

        if is_valid:
            if self.plant_data_object is None or not hasattr(self.plant_data_object, 'fertilizing_episodes'):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
                return
            
            self.plant_data_object.append_fertilizing_episode(
                FertilizingEpisodeData(
                    description=cleaned_data['description'],
                    magnesium_sulfate_mass=cleaned_data['magnesium_sulfate_mass'],
                    reps=cleaned_data['reps']
                )
            )

            self.current_component_number = 1
            self._compose_subheading_label()

            self.fertilizing_life_stage_description_field.value = None
            self.fertilizing_magnesium_sulfate_mass_field.value = None
            self.fertilizing_reps_field.value = None

            self.content_container.content.controls = self.components_adding_view
            self.content_container.update()

    def validate_component_data(self):
        """
        Validates the data about a component of the mixture. Returns a tuple of a bool value indicating
        the validness of the data and the dict containing the cleaned data if the data is valid.
        """
        is_valid = True
        cleaned_data = {}

        component_id = self.component_dropdown.value
        if component_id in ('', None):
            self.component_dropdown.error_text = 'Необходимо выбрать удобрение.'
            self.component_dropdown.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.component_dropdown.error_text = None
            self.component_dropdown.border_color = None
            cleaned_data['component_id'] = int(component_id)

        component_mass = self.component_mass_field.value
        validation_result = validate_decimal_string(
            component_mass,
            field_name='Масса',
            min_value=0.1,
            max_decimals=2,
            gender='f'
        )
        if not validation_result['success']:
            self.component_mass_field.error_text = validation_result['error']
            self.component_mass_field.border_color = ft.Colors.RED
            is_valid = False
        else:
            self.component_mass_field.error_text = None
            self.component_mass_field.border_color = None
            cleaned_data['mass'] = validation_result['value']

        self.content_container.update()

        return is_valid, cleaned_data if is_valid else None

    def append_component(self):
        """
        Calls the component validation method and appends the data to the dataclass
        if the data is valid. Returns a bool value indicating if the data was appended.
        """
        is_valid, cleaned_data = self.validate_component_data()

        component_appended = False

        if is_valid:
            if self.plant_data_object is None or not hasattr(self.plant_data_object, 'fertilizing_episodes') \
                    or not len(self.plant_data_object.fertilizing_episodes):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
                return

            target_episode = self.plant_data_object.fertilizing_episodes[-1]

            if not hasattr(target_episode, 'components'):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
                return

            target_episode.append_component(
                ComponentData(
                    fertilizing_mixture_id=cleaned_data['component_id'],
                    mass=cleaned_data['mass']
                )
            )
            component_appended = True

        return component_appended

    def append_component_and_update_layout(self, e):
        """
        Calls the component appending method and updates the
        layout if the validation and appending were successful.
        """
        result = self.append_component()

        if result:
            self.current_component_number += 1
            self._compose_subheading_label()

            self.component_dropdown.value = ''
            self.component_mass_field.value = None

            self.content_container.update()

    def append_last_component_and_update_layout(self, e):
        """
        Calls the component appending method for the last component and updates the layout to
        the fertilizing metadata adding view if the validation and appending were successful.
        """
        is_valid, cleaned_data = self.validate_component_data()

        if is_valid:
            if self.plant_data_object is None or not hasattr(self.plant_data_object, 'fertilizing_episodes') \
                    or not len(self.plant_data_object.fertilizing_episodes):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
                return

            target_episode = self.plant_data_object.fertilizing_episodes[-1]

            if not hasattr(target_episode, 'components'):
                self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')
                return

            target_episode.append_component(
                ComponentData(
                    fertilizing_mixture_id=cleaned_data['component_id'],
                    mass=cleaned_data['mass']
                )
            )

            self.current_episode_number += 1
            self.current_component_number = None
            self._compose_subheading_label()

            self.component_dropdown.value = ''
            self.component_mass_field.value = None

            self.content_container.content.controls = self.fertilizing_metadata_view
            self.content_container.update()

    @staticmethod
    def _clean_values_and_remove_errors(controls):
        """Clears the values and errors in the TextField controls of the page."""
        for control in controls:
            if isinstance(control, ft.Dropdown):
                control.value = ''
            else:
                control.value = None

            control.error_text = None
            control.border_color = None

    def go_back(self, e):
        """
        Maintains the returning to the previous view depending on
        a context. Completely wipes entered but unsubmitted data.
        """
        if self.current_component_number is not None:
            self._clean_values_and_remove_errors((self.component_mass_field, self.component_dropdown))

            if self.current_component_number == 1:
                restoring_object = self.plant_data_object.fertilizing_episodes.pop()

                self.fertilizing_life_stage_description_field.value = str(restoring_object.description)
                self.fertilizing_magnesium_sulfate_mass_field.value = str(restoring_object.magnesium_sulfate_mass)
                self.fertilizing_reps_field.value = str(restoring_object.reps)

                self.current_component_number = None
                self._compose_subheading_label()

                self.content_container.content.controls = self.fertilizing_metadata_view
                self.content_container.update()

            else:
                restoring_object = self.plant_data_object.fertilizing_episodes[-1].components.pop()

                self.component_dropdown.value = str(restoring_object.fertilizing_mixture_id)
                self.component_mass_field.value = str(restoring_object.mass)

                self.current_component_number -= 1
                self._compose_subheading_label()

                self.content_container.content.controls = self.components_adding_view
                self.content_container.update()

        elif self.current_episode_number is not None:
            self._clean_values_and_remove_errors((self.fertilizing_life_stage_description_field,
                                                  self.fertilizing_magnesium_sulfate_mass_field,
                                                  self.fertilizing_reps_field))
            if self.current_episode_number == 1:
                self.plant_name_field.value = self.plant_data_object.name
                self.plant_category_dropdown.value = str(self.plant_data_object.category_id)

                self.heading_label.value = self.heading_label.value.rstrip(':')
                self.plant_data_object = None
                self.current_episode_number = None

                self.content_container.content.controls = self.plant_metadata_view
                self.content_container.update()

            else:
                target_episode = self.plant_data_object.fertilizing_episodes[-1]

                self.current_component_number = len(target_episode.components)
                restoring_object = target_episode.components.pop()

                self.component_dropdown.value = str(restoring_object.fertilizing_mixture_id)
                self.component_mass_field.value = str(restoring_object.mass)

                self.current_episode_number -= 1
                self._compose_subheading_label()

                self.content_container.content.controls = self.components_adding_view
                self.content_container.update()

        else:
            self.show_error_dialog(text='Произошла критическая ошибка. Пожалуйста, перезапустите приложение.')

    def save_all_data(self, e):
        """
        Calculates and saves the plant and it's fertilizing episodes to the db using a singular transaction.
        Uses data about the fertilizing mixtures from the db to calculate the exact masses of the elements.
        Then calls the state clearing method for a user to continue entering a further data.
        """
        last_component_appended = self.append_component()

        if not last_component_appended:
            return

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
                episode_composition = {'N': 0, 'P': 0, 'K': 0}

                for component in episode.components:
                    fertilizing_mixture_object = FertilizingMixture.get_by_id(component.fertilizing_mixture_id)

                    component_composition = get_component_masses(
                        n_percentage=fertilizing_mixture_object.nitrogen_percentage,
                        p_percentage=fertilizing_mixture_object.phosphorus_percentage,
                        k_percentage=fertilizing_mixture_object.potassium_percentage,
                        total_mass=component.mass
                    )

                    apply_nano_coefficients(component_composition)

                    for key in component_composition.keys():
                        episode_composition[key] = ((episode_composition[key] + component_composition[key])
                                                    .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

                fertilizing_creation_result = create_fertilizing_episode(
                    plant_id=plant_id,
                    nitrogen_mass=episode_composition['N'],
                    phosphorus_mass=episode_composition['P'],
                    potassium_mass=episode_composition['K'],
                    magnesium_sulfate_mass=episode.magnesium_sulfate_mass,
                    plant_life_stage_description=episode.description,
                    total_repetitions=episode.reps
                )

                if not fertilizing_creation_result['success']:
                    self.plant_data_object.fertilizing_episodes[-1].components.pop()
                    self.show_error_dialog(text=fertilizing_creation_result['error'])
                    transaction.rollback()
                    return

        self.clear_state()

        snackbar = ft.SnackBar(ft.Text('Растение и подкормки успешно сохранены в БД.'))
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

    def clear_state(self):
        """Clears the state of the page."""
        self.plant_data_object = None
        self.current_episode_number = None
        self.current_component_number = None

        self.heading_label.value = self.heading_label.value[:-1]  # trimming the ":"

        for field in (self.plant_name_field, self.fertilizing_life_stage_description_field, self.fertilizing_reps_field,
                      self.fertilizing_magnesium_sulfate_mass_field, self.component_mass_field):
            field.value = None

        for dropdown in (self.plant_category_dropdown, self.component_dropdown):
            dropdown.value = ''

        self.content_container.content.controls = self.plant_metadata_view
        self.content_container.update()

    def prevent_leaving(self, navigate_to_leaving_destination):
        """
        Prevents the user from leaving if there are unsaved changes.
        If no unsaved changes exist, navigation proceeds normally. Otherwise, a
        confirmation dialog is shown to prompt the user for confirmation before leaving.
        """
        if self.plant_data_object is None:
            if not self.plant_name_field.value:
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
