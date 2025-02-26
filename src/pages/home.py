import asyncio
from decimal import ROUND_HALF_UP
from time import sleep

import flet as ft
from peewee import fn

from config import BASIC_CONTENT_WIDTH, PAGE_MIN_HEIGHT, UNIFIED_BUTTON_STYLE
from core.mixture_calculation import calculate_best_mixture
from database import *
from utils.validation import validate_string


class HomePage(ft.Control):
    """
    An app's home page which is dedicated to displaying all the available elements
    from the db (plant categories, plants and calculated fertilizing episodes) and
    actually executing the calculation of the best possible mixture for each episode.
    """
    def __init__(self, page):
        """Initializes the home page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = True

        # state-related vars
        self.selected_category = None
        self.selected_plant = None
        self.selected_episode = None

        # refs for managing the back button layout
        self.header_text_ref = ft.Ref[ft.Container]()
        self.back_button_ref = ft.Ref[ft.IconButton]()

        # main container to display the elements
        self.list_view = ft.ListView(spacing=10, expand=True, expand_loose=True)

        # offset to align the main container's height correctly
        self.list_view_height_offset = 195

        # renaming modal
        self.new_element_name_field = ft.TextField(label='Новое название', width=BASIC_CONTENT_WIDTH)
        self.renaming_dialog = ft.AlertDialog(
            title=ft.Text('Переименовать элемент'),
            content=ft.Column(controls=[self.new_element_name_field], height=50),
            modal=True
        )

        # deletion modal
        self.deletion_dialog = ft.AlertDialog(
            title=ft.Text('Удалить элемент'),
            content=ft.Text('Вы действительно хотите удалить данный элемент?', size=16)
        )

        # critical error modal
        self.error_dialog = ft.AlertDialog(
            title=ft.Text('Ошибка', color=ft.Colors.RED),
            content=None,
            modal=True,
            scrollable=True,
            actions=[ft.ElevatedButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)]
        )

        # initial populating of the list view
        self.load_categories()

    def build(self):
        """Returns the main container with the initial view."""
        return ft.Container(ft.Column([
            ft.Row([
                ft.Container(  # placeholder for the back button which is inactive at first
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, ref=self.back_button_ref, visible=False),
                    alignment=ft.alignment.center, margin=ft.margin.only(left=-15)
                ),
                ft.Container(
                    ft.Text('Просмотр информации', theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                            weight=ft.FontWeight.BOLD),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(bottom=4),
                    margin=ft.margin.only(left=25),  # offset for the back button's placeholder
                    ref=self.header_text_ref
                    # idk that's just how it's evenly aligned with the button
                )
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(
                content=self.list_view,
                height=self.page.window.height - self.list_view_height_offset,
                margin=ft.margin.symmetric(horizontal=35),
                alignment=ft.alignment.center
            ),
            self.renaming_dialog,
            self.deletion_dialog,
            self.error_dialog
        ]), alignment=ft.alignment.center, margin=ft.margin.symmetric(vertical=5, horizontal=20))

    def load_categories(self):
        """
        Loads and displays all categories from the db that
        contain plants. If there are none, displays a message.
        """
        self.selected_category = None
        self.selected_plant = None
        self.selected_episode = None

        if self.back_button_ref.current is not None and self.back_button_ref.current.visible:
            self.header_text_ref.current.content.value = 'Просмотр информации'
            self.hide_back_button()

        self.list_view.controls.clear()

        categories = ((PlantCategory
                       .select()
                       .join(Plant, on=(PlantCategory.id == Plant.category))
                       .group_by(PlantCategory))
                      .having(fn.COUNT(Plant.id) > 0)
                      .order_by(PlantCategory.name))

        if not len(categories):
            self.list_view.controls.append(
                ft.Container(
                    ft.Text('Данные не найдены', theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                    margin=ft.margin.only(top=PAGE_MIN_HEIGHT / 3.5),
                    alignment=ft.alignment.center
                )
            )

        else:
            for category in categories:
                self.list_view.controls.append(self.create_category_card(category))

        self.page.update()

    def load_plants_for_category(self, category):
        """
        Loads and displays all plants for the selected category.
        If there are none, redirects to the categories loading and displaying.
        """
        self.selected_plant = None
        self.selected_episode = None
        self.selected_category = category

        self.show_back_button(target=lambda e: self.load_categories())
        self.list_view.controls.clear()

        plants = category.plants

        if not len(plants):
            self.load_categories()

        else:
            self.header_text_ref.current.content.value = category.name

            for plant in plants.order_by(Plant.name):
                self.list_view.controls.append(self.create_plant_card(plant))

            self.page.update()
        
    def load_episodes_for_plant(self, plant):
        """Loads and displays all fertilizing episodes for the selected plant."""
        self.selected_plant = plant

        self.header_text_ref.current.content.value = plant.name

        self.show_back_button(target=lambda e: self.load_plants_for_category(self.selected_category))
        self.list_view.controls.clear()

        for index, episode in enumerate(plant.fertilizing_episodes):
            episode.index = index
            self.list_view.controls.append(self.create_episode_card(episode))

        self.list_view.update()

    def create_category_card(self, category):
        """Creates a card for the category to display a data unit."""
        return ft.ListTile(
            title=ft.Text(category.name, theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
            trailing=ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                items=[
                    ft.PopupMenuItem(
                        text='Переименовать', icon=ft.Icons.EDIT,
                        on_click=lambda e: self.open_renaming_dialog(mode='category', element_id=category.id)
                    ),
                    ft.PopupMenuItem(
                        text='Удалить', icon=ft.Icons.DELETE,
                        on_click=lambda e: self.open_deletion_dialog(mode='category', element_id=category.id)
                    )
                ],
                tooltip=''
            ),
            hover_color=ft.Colors.SURFACE,
            bgcolor_activated=ft.Colors.SURFACE,
            on_click=lambda e: self.load_plants_for_category(category)
        )

    def create_plant_card(self, plant):
        """Creates a card for the plant to display a data unit"""
        return ft.ListTile(
            title=ft.Text(plant.name, theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
            trailing=ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                items=[
                    ft.PopupMenuItem(
                        text='Переименовать', icon=ft.Icons.EDIT,
                        on_click=lambda e: self.open_renaming_dialog(mode='plant', element_id=plant.id)
                    ),
                    ft.PopupMenuItem(
                        text='Удалить', icon=ft.Icons.DELETE,
                        on_click=lambda e: self.open_deletion_dialog(mode='plant', element_id=plant.id)
                    )
                ],
                tooltip=''
            ),
            hover_color=ft.Colors.SURFACE,
            bgcolor_activated=ft.Colors.SURFACE,
            on_click=lambda e: self.load_episodes_for_plant(plant)
        )

    def create_episode_card(self, episode):
        """Creates a card for the fertilizing episode to display a data unit"""
        episode_card = ft.ListTile(
            title=ft.Text(f'Подкормка №{episode.index + 1}',
                          theme_style=ft.TextThemeStyle.TITLE_MEDIUM, size=15),
            subtitle=ft.Column([ft.Container()]),
            hover_color=ft.Colors.SURFACE,
            bgcolor_activated=ft.Colors.SURFACE,
            on_click=lambda e: self.page.run_task(self.prepare_and_display_mixture_data, episode)
        )

        episode_masses = {'азота': episode.nitrogen_mass,
                          'фосфора': episode.phosphorus_mass,
                          'калия': episode.potassium_mass,
                          'сульфата магния': episode.magnesium_sulfate_mass}

        for name, mass in episode_masses.items():
            if mass:
                episode_card.subtitle.controls.append(
                    ft.Text(f'Масса {name}: {mass} г', size=15)
                )

        episode_card.subtitle.controls += [
            ft.Text(f'Стадия жизненного цикла: {episode.plant_life_stage_description}', size=15),
            ft.Text(f'Повторений: {episode.total_repetitions}', size=15)
        ]

        return episode_card

    async def prepare_and_display_mixture_data(self, episode):
        """Updates the UI before and after the mixture calculation process, awaits the mixture calculation."""
        self.selected_episode = episode
        self.list_view.controls.clear()
        self.page.overlay.append(
            ft.Container(
                ft.ProgressRing(),
                width=40, height=40,
                top=self.page.height / 2,
                left=self.page.width / 2 - 20
            )
        )
        self.header_text_ref.current.content.value += f' (подк. №{episode.index + 1})'
        self.back_button_ref.current.on_click = None
        self.page.update()

        try:
            self.ready_to_leave = False
            await asyncio.to_thread(self._obtain_mixture_data_and_layout)

        finally:
            self.ready_to_leave = True
            self.show_back_button(target=lambda e: self.load_episodes_for_plant(self.selected_plant))
            self.page.overlay.pop()
            self.page.update()

    def _obtain_mixture_data_and_layout(self):
        """
        Calculates the best mixture data with the fertilizing episode's properties,
        constructs the complex layout for displaying the mixture components and their
        properties, handles the magnesium sulfate related errors. If unable to calculate
        particular mixture, provides an error message.
        """
        nitrogen_mass = self.selected_episode.nitrogen_mass
        phosphorus_mass = self.selected_episode.phosphorus_mass
        potassium_mass = self.selected_episode.potassium_mass
        magnesium_sulfate_mass = self.selected_episode.magnesium_sulfate_mass

        magnesium_sulfate_presents = magnesium_sulfate_mass > 0
        magnesium_sulfate_cost_undefined = False

        mass = nitrogen_mass + phosphorus_mass + potassium_mass

        calculation_result = calculate_best_mixture(
            nitrogen=nitrogen_mass,
            phosphorus=phosphorus_mass,
            potassium=potassium_mass,
            total_mass=mass
        )

        episode_data_container = ft.Container(
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            alignment=ft.alignment.center,
            margin=ft.margin.only(top=10),
            padding=ft.padding.symmetric(vertical=20, horizontal=20),
            border_radius=ft.border_radius.all(25)
        )

        episode_data_column = ft.Column()
        episode_data_container.content = episode_data_column

        if not calculation_result['success']:
            episode_data_container.bgcolor = ft.Colors.ERROR_CONTAINER
            episode_data_container.height = 200
            episode_data_column.alignment = ft.MainAxisAlignment.CENTER
            episode_data_column.controls.append(
                ft.Text(calculation_result['error'], theme_style=ft.TextThemeStyle.TITLE_MEDIUM)
            )

        else:
            episode_data_row = ft.Row()
            episode_data_subcolumn = ft.Column()
            episode_data_row.controls.append(episode_data_subcolumn)

            episode_data_subcolumn.controls.append(
                ft.Text('Рассчитанная оптимальная смесь:', weight=ft.FontWeight.BOLD, size=20)
            )

            mixture_data = calculation_result['mixture']
            total_cost = Decimal(str(calculation_result['total_cost']))

            if magnesium_sulfate_presents:
                try:
                    magnesium_sulfate_cost = (FertilizingMixture.get(
                        FertilizingMixture.name == 'Сульфат магния'
                    ).price_per_gram * magnesium_sulfate_mass).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                    mixture_data.append({
                        'name': 'Сульфат магния',
                        'mass_in_grams': magnesium_sulfate_mass,
                        'cost': magnesium_sulfate_cost
                    })

                    total_cost = (total_cost + magnesium_sulfate_cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                except (DoesNotExist, AttributeError):
                    mixture_data.append({
                        'name': 'Сульфат магния',
                        'mass_in_grams': magnesium_sulfate_mass,
                        'cost': '?'
                    })

                    magnesium_sulfate_cost_undefined = True
                    total_cost = '?'

            for mix_unit in mixture_data:
                if magnesium_sulfate_cost_undefined and mix_unit['name'] == 'Сульфат магния':
                    cost_text_control = ft.Text('? руб.', size=15, weight=ft.FontWeight.BOLD,
                                                color=ft.Colors.RED_ACCENT)
                else:
                    cost_text_control = ft.Text(f'{mix_unit["cost"]} руб.', size=15)

                episode_data_subcolumn.controls.append(
                    ft.Row([
                        ft.Text(f'{mix_unit["name"]}:', weight=ft.FontWeight.BOLD, size=15),
                        ft.Text(f'{mix_unit["mass_in_grams"]} г,', size=15),
                        cost_text_control
                    ])
                )

            primitive_masses = {'N': nitrogen_mass, 'P': phosphorus_mass, 'K': potassium_mass}
            actual_composition = []

            for alias, mass in primitive_masses.items():
                actual_primitive_mass = Decimal(str(calculation_result['actual_composition'][alias]))

                if actual_primitive_mass > 0:
                    mass_delta = (actual_primitive_mass - mass).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                    if mass_delta == 0:
                        actual_composition.append(f'{alias}: {actual_primitive_mass} г,')

                    elif mass_delta > 0:
                        actual_composition.append(f'{alias}: {actual_primitive_mass} г (+{mass_delta} г),')

                    else:
                        actual_composition.append(f'{alias}: {actual_primitive_mass} г ({mass_delta} г),')

            if magnesium_sulfate_presents:
                actual_composition.append(f'MgS: {magnesium_sulfate_mass} г')
            else:
                actual_composition[-1] = actual_composition[-1].rstrip(',')

            episode_data_subcolumn.controls.append(ft.Row(
                [ft.Text('Конечный состав:', weight=ft.FontWeight.BOLD, size=15)] +
                [ft.Text(composition_str, size=15) for composition_str in actual_composition],
                width=self.page.width / 1.33, wrap=True
            ))

            episode_data_subcolumn.controls.append(
                ft.Row([
                    ft.Text('Общая цена:', weight=ft.FontWeight.BOLD, size=15),

                    ft.Text('? руб.', size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT)
                    if magnesium_sulfate_cost_undefined
                    else ft.Text(f'{total_cost} руб.', size=15)
                ])
            )

            if magnesium_sulfate_cost_undefined:
                episode_data_subcolumn.controls.append(
                    ft.Container(
                        ft.Text('Ошибка: не удалось получить стоимость MgS.', size=15,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT),
                        margin=ft.margin.only(top=6)
                    )
                )

            episode_data_subcolumn.controls.append(
                ft.Container(
                    ft.FilledTonalButton(
                        text='Копировать информацию', icon=ft.Icons.COPY, style=UNIFIED_BUTTON_STYLE,
                        on_click=lambda e: self.copy_episode_data(e, mixture=mixture_data, total_cost=total_cost),
                    ),
                    margin=ft.margin.only(top=6)
                )
            )

            episode_data_column.controls.append(episode_data_row)

        self.list_view.controls.clear()
        self.list_view.controls.append(episode_data_container)

        sleep(0.25)  # waiting to avoid flickering

        self.list_view.update()

    def copy_episode_data(self, e=None, *, mixture, total_cost):
        """Copies the fertilizing episode data to the clipboard in a convenient readable format."""
        output_text = f'Растение: {self.selected_plant.name}\n\n'
        output_text += (f'Подкормка №{self.selected_episode.index + 1} '
                        f'({self.selected_episode.plant_life_stage_description})\n')

        fertilizing_data = {'азота': self.selected_episode.nitrogen_mass,
                            'фосфора': self.selected_episode.phosphorus_mass,
                            'калия': self.selected_episode.potassium_mass,
                            'сульфата магния': self.selected_episode.magnesium_sulfate_mass}

        for name, mass in fertilizing_data.items():
            if mass:
                output_text += f'Масса {name}: {mass} г\n'

        output_text += '\nОптимальная рассчитанная смесь:\n'

        for mix_unit in mixture:
            output_text += f'{mix_unit["name"]}: {mix_unit["mass_in_grams"]} г, {mix_unit["cost"]} руб.\n'

        output_text += f'\nЦена: {total_cost} руб.\n'

        output_text += f'Повторений: {self.selected_episode.total_repetitions}'

        self.page.set_clipboard(output_text)

        e.control.text = 'Скопировано'
        e.control.icon = ft.Icons.CHECK
        e.control.update()

    def show_back_button(self, target):
        """Adjusts the layout and displays the back button with the given target method."""
        self.back_button_ref.current.visible = True
        self.header_text_ref.current.margin = None
        self.back_button_ref.current.on_click = target
        self.page.update()

    def hide_back_button(self):
        """Adjusts the layout and hides the back button."""
        self.back_button_ref.current.visible = False
        self.header_text_ref.current.margin = ft.margin.only(left=25)
        self.page.update()

    def wrap_category_renaming(self, category_id):
        """Handles the process of renaming a plant category."""
        name = self.new_element_name_field.value.strip()

        validation_result = validate_string(name, 'Название категории')
        if not validation_result['success']:
            self.new_element_name_field.error_text = validation_result['error']
            self.new_element_name_field.border_color = ft.Colors.RED
            self.renaming_dialog.update()
            return

        if does_category_exit(name):
            self.new_element_name_field.error_text = f'Категория с названием {name} уже существует!'
            self.new_element_name_field.border_color = ft.Colors.RED
            self.renaming_dialog.update()
            return

        self.new_element_name_field.error_text = None
        self.new_element_name_field.border_color = None

        renaming_result = rename_plant_category(identifier=category_id, new_name=name)
        if not renaming_result['success']:
            sleep(0.15)  # waiting to prevent flickering
            self.show_error_dialog(text=renaming_result['error'])

        else:
            self.new_element_name_field.value = ''
            self.close_renaming_dialog()

        self.load_categories()

    def wrap_category_deletion(self, category_id):
        """Handles the deletion of a plant category and refreshes the list."""
        deletion_result = delete_plant_category(category_id)

        if not deletion_result['success']:
            sleep(0.15)  # waiting to prevent flickering
            self.show_error_dialog(text=deletion_result['error'])

        else:
            self.close_deletion_dialog()

        self.load_categories()

    def wrap_plant_renaming(self, plant_id):
        """Handles the process of renaming a plant."""
        name = self.new_element_name_field.value.strip()

        validation_result = validate_string(name, 'Название растения')
        if not validation_result['success']:
            self.new_element_name_field.error_text = validation_result['error']
            self.new_element_name_field.border_color = ft.Colors.RED
            self.renaming_dialog.update()
            return

        if does_plant_exist(name):
            self.new_element_name_field.error_text = f'Растение с названием {name} уже существует!'
            self.new_element_name_field.border_color = ft.Colors.RED
            self.renaming_dialog.update()
            return

        self.new_element_name_field.error_text = None
        self.new_element_name_field.border_color = None

        renaming_result = rename_plant(identifier=plant_id, new_name=name)
        if not renaming_result['success']:
            sleep(0.15)  # waiting to prevent flickering
            self.show_error_dialog(text=renaming_result['error'])

        else:
            self.new_element_name_field.value = ''
            self.close_renaming_dialog()

        self.load_plants_for_category(category=self.selected_category)

    def wrap_plant_deletion(self, plant_id):
        """Handles the deletion of a plant and refreshes the plant list."""
        deletion_result = delete_plant(plant_id)

        if not deletion_result['success']:
            sleep(0.15)  # waiting to prevent flickering
            self.show_error_dialog(text=deletion_result['error'])

        else:
            self.close_deletion_dialog()

        self.load_plants_for_category(category=self.selected_category)

    def open_renaming_dialog(self, *, mode, element_id):
        """
        Opens the renaming dialog for a category or plant. Takes
        the 'mode' argument that determines the entity to rename.
        """
        self.new_element_name_field.value = ""
        self.new_element_name_field.error_text = None
        self.new_element_name_field.border_color = None

        if mode == 'category':
            self.renaming_dialog.title = ft.Text('Переименовать категорию растений')
            self.renaming_dialog.actions = [
                ft.TextButton('Закрыть', style=UNIFIED_BUTTON_STYLE, on_click=self.close_renaming_dialog),
                ft.TextButton(
                    text='Сохранить', style=UNIFIED_BUTTON_STYLE,
                    on_click=lambda e: self.wrap_category_renaming(element_id)
                )
            ]
        elif mode == 'plant':
            self.renaming_dialog.title = ft.Text('Переименовать растение')
            self.renaming_dialog.actions = [
                ft.TextButton('Закрыть', style=UNIFIED_BUTTON_STYLE, on_click=self.close_renaming_dialog),
                ft.TextButton(
                    text='Сохранить', style=UNIFIED_BUTTON_STYLE,
                    on_click=lambda e: self.wrap_plant_renaming(element_id)
                )
            ]
        else:
            raise ValueError(f'Wrong type of the element: {mode}.')

        self.renaming_dialog.open = True
        self.renaming_dialog.update()

    def close_renaming_dialog(self, e=None):
        """Closes the renaming dialog."""
        self.renaming_dialog.open = False
        self.renaming_dialog.update()

    def open_deletion_dialog(self, *, mode, element_id):
        """
        Opens the deletion dialog for a category or plant. Takes
        the 'mode' argument that determines the entity to delete.
        """
        if mode == 'category':
            self.deletion_dialog.actions = [
                ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE, on_click=self.close_deletion_dialog),
                ft.TextButton('Да', style=UNIFIED_BUTTON_STYLE,
                              on_click=lambda e: self.wrap_category_deletion(element_id))
            ]
        elif mode == 'plant':
            self.deletion_dialog.actions = [
                ft.TextButton('Отмена', style=UNIFIED_BUTTON_STYLE, on_click=self.close_deletion_dialog),
                ft.TextButton('Да', style=UNIFIED_BUTTON_STYLE,
                              on_click=lambda e: self.wrap_plant_deletion(element_id))
            ]
        else:
            raise ValueError(f'Wrong type of the element: {mode}.')

        self.deletion_dialog.open = True
        self.deletion_dialog.update()

    def close_deletion_dialog(self, e=None):
        """Closes the deletion dialog."""
        self.deletion_dialog.open = False
        self.deletion_dialog.update()

    def show_error_dialog(self, text):
        """Displays an error dialog with the given text."""
        self.error_dialog.content = ft.Text(text, size=16)
        self.error_dialog.open = True
        self.error_dialog.update()

    def close_error_dialog(self, e=None):
        """Closes the error dialog."""
        self.error_dialog.open = False
        self.error_dialog.update()
