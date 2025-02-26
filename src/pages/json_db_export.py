import asyncio
import json
import os
from datetime import datetime
from time import sleep

import flet as ft
from peewee import fn

from config import VERSION, UNIFIED_BUTTON_STYLE
from database import PlantCategory, Plant, FertilizingMixture
from utils.utils import truncate_string


class JsonDbExportPage(ft.Control):
    """
    A page for creating and saving the JSON DB dump containing all the stored data about the entities.
    """
    def __init__(self, page):
        """Initializes the JSON-export page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = True

        # obtained path for saving the db dump
        self.dump_filepath = None

        # named labels
        self.heading_container = ft.Container(
            ft.Text(value='Экспорт базы данных',
                    theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD),
            margin=ft.margin.only(bottom=2)
        )

        self.filepath_label_container = ft.Container(
            ft.Text(theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
            margin=ft.margin.only(bottom=4)
        )

        # file picker object
        self.file_picker = ft.FilePicker(on_result=self.assess_dump_file_path)

        # named buttons
        self.pick_path_button = ft.FilledTonalButton('Выбрать путь сохранения файла', icon=ft.Icons.FOLDER_OPEN,
                                                     style=UNIFIED_BUTTON_STYLE, on_click=self.wrap_file_picking)

        self.pick_path_button_container = ft.Container(self.pick_path_button, margin=ft.margin.only(top=4))

        self.export_db_button = ft.FilledTonalButton(
            'Экспортировать информацию из БД', style=UNIFIED_BUTTON_STYLE, on_click=self.wrap_db_export
        )

        # critical error modal
        self.error_dialog = ft.AlertDialog(
            title=ft.Text('Ошибка', color=ft.Colors.RED),
            content=None,
            modal=True,
            actions=[ft.ElevatedButton('Понятно', style=UNIFIED_BUTTON_STYLE, on_click=self.close_error_dialog)]
        )

        # pre-defined views
        self.initial_view = (
            self.heading_container,
            self.pick_path_button_container,
            self.file_picker,
            self.error_dialog
        )

        self.loaded_path_view = (
            self.heading_container,
            self.filepath_label_container,
            self.export_db_button,
            self.error_dialog
        )

        self.loading_view = (
            ft.Container(
                ft.ProgressRing(),
                width=40, height=40,
                margin=ft.margin.only(top=self.page.height / 3),
                alignment=ft.alignment.center
            ),
            self.error_dialog
        )

        # main content container with the initial view's content
        self.content_container = ft.Container(
            ft.Column(self.initial_view),
            margin=ft.margin.symmetric(vertical=5), alignment=ft.alignment.center
        )

    def build(self):
        """Returns the main container with the initial view."""
        return self.content_container

    def wrap_file_picking(self, e):
        """Opens a file picker dialog for selecting the save path."""
        self.file_picker.save_file(
            dialog_title='Выбор имени и расположения файла экспорта БД',
            file_name=f'NFMU_v{VERSION}_db_dump_{datetime.now().strftime("%d-%m-%Y %H-%M-%S")}.json',
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['json']
        )

    def assess_dump_file_path(self, e):
        """Validates the selected file path and updates the UI accordingly."""
        filepath = e.path

        if filepath:
            directory = os.path.dirname(filepath)

            if os.access(directory, os.W_OK):
                self.dump_filepath = filepath

                self.filepath_label_container.content.value = f'Путь: {truncate_string(filepath, 50)}'

                self.content_container.content.controls = self.loaded_path_view
                self.content_container.update()

            else:
                self.show_error_dialog(text='Невозможно сохранить файл по данному пути. Выберите другой.')

    def wrap_db_export(self, e=None):
        """Runs the DB export process asynchronously."""
        self.page.run_task(self._adjust_layout_and_await_db_export)

    async def _adjust_layout_and_await_db_export(self):
        """Updates the UI before and after the DB export process, awaits the DB exporting."""
        self.content_container.content.controls = self.loading_view
        self.content_container.update()

        self.ready_to_leave = False
        dump_saving_result = await asyncio.to_thread(self._generate_and_save_db_dump)
        sleep(0.25)  # waiting to avoid flickering

        self.content_container.content.controls = self.initial_view
        self.content_container.update()

        self.ready_to_leave = True

        if dump_saving_result['success']:
            snackbar = ft.SnackBar(ft.Text('Файл экспорта БД успешно сохранён.'), duration=1500)
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

    def _generate_and_save_db_dump(self):
        """
        Generates and saves the DB export JSON-file.
        """
        data_to_dump = {}

        categories = ((PlantCategory
                       .select()
                       .join(Plant, on=(PlantCategory.id == Plant.category))
                       .group_by(PlantCategory))
                      .having(fn.COUNT(Plant.id) > 0)
                      .order_by(PlantCategory.name))

        dataset_is_empty = not len(categories)

        data_to_dump['plants_related_data'] = {}

        for category in categories:
            data_to_dump['plants_related_data'][category.name] = {}

            for plant in category.plants.order_by(Plant.name):
                data_to_dump['plants_related_data'][category.name][plant.name] = []

                for episode in plant.fertilizing_episodes:
                    episode_data_dict = {'nitrogen_mass': str(episode.nitrogen_mass),
                                         'phosphorus_mass': str(episode.phosphorus_mass),
                                         'potassium_mass': str(episode.potassium_mass),
                                         'magnesium_sulfate_mass': str(episode.magnesium_sulfate_mass),
                                         'plant_life_stage_description': episode.plant_life_stage_description,
                                         'total_repetitions': str(episode.total_repetitions)}

                    data_to_dump['plants_related_data'][category.name][plant.name].append(episode_data_dict)

        mixtures = FertilizingMixture.select().order_by(FertilizingMixture.name)

        if not len(mixtures) and dataset_is_empty:
            self.show_error_dialog(text='Данные для экспорта не найдены.')
            return

        data_to_dump['mixtures_related_data'] = {}

        for mixture in mixtures:
            data_to_dump['mixtures_related_data'][mixture.name] = {
                'nitrogen_percentage': str(mixture.nitrogen_percentage),
                'phosphorus_percentage': str(mixture.phosphorus_percentage),
                'potassium_percentage': str(mixture.potassium_percentage),
                'price_per_gram': str(mixture.price_per_gram)
            }

        try:
            self.lock_window_closing()

            # attempting to write json data to a file
            with open(self.dump_filepath, 'w', encoding='utf-8') as json_file:
                json.dump(data_to_dump, json_file, indent=4, ensure_ascii=False)

                return {'success': True}

        except (FileNotFoundError, PermissionError):
            self.show_error_dialog(text='Не удалось сохранить файл по данному пути, '
                                        'попробуйте другой путь или имя файла.')
            return {'success': False}

        except (TypeError, Exception) as err:
            self.show_error_dialog(text=f'Не удалось сохранить файл из-за внутренней ошибки: {err}.')
            return {'success': False}

        finally:
            self.unlock_window_closing()

    def lock_window_closing(self):
        """Prevents closing the window while exporting the DB."""
        self.page.window.prevent_close = True
        self.page.update()

    def unlock_window_closing(self):
        """Allows closing the window after exporting the DB."""
        self.page.window.prevent_close = False
        self.page.update()

    def show_error_dialog(self, text):
        """Displays an error dialog with the given text."""
        self.error_dialog.content = ft.Text(text, size=16)
        self.error_dialog.open = True
        self.error_dialog.update()

    def close_error_dialog(self, e=None):
        """Closes the error dialog."""
        self.error_dialog.open = False
        self.error_dialog.update()
