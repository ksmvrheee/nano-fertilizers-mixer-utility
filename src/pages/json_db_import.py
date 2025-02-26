import asyncio
import os
from json import load, JSONDecodeError
from time import sleep

import flet as ft
from peewee import IntegrityError, DatabaseError, DoesNotExist, OperationalError

from config import UNIFIED_BUTTON_STYLE
from database import db, PlantCategory, FertilizingMixture, Plant, PlantFertilizingEpisode
from utils.utils import truncate_string
from utils.validation import validate_string, validate_decimal_string, validate_int_string


class JsonDbImportPage(ft.Control):
    """
    A page for importing the DB contents from the JSON dump file.
    Includes validation of the importing data and exception catching.
    Opens dialogs to ask a user what action to execute on conflicts and errors.
    """
    def __init__(self, page):
        """Initializes the JSON-import page."""
        super().__init__()

        self.page = page
        self.ready_to_leave = True

        # obtained path of the db dump to import
        self.dump_filepath = None

        # whether user confirmed that the db is to be erased
        self.db_erasure_confirmed = False

        # whether user confirmed that the dump data should overwrite a data in the db
        self.db_overwriting_confirmed = None

        # named labels
        self.heading_container = ft.Container(
            ft.Text(value='Импорт базы данных',
                    theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD),
            margin=ft.margin.only(bottom=2)
        )

        self.filepath_label_container = ft.Container(
            ft.Text(theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
            margin=ft.margin.only(bottom=4)
        )

        # file picker object
        self.file_picker = ft.FilePicker(on_result=self.assess_dump_file_path)

        # checkbox
        self.erase_db_checkbox = ft.Checkbox(label='полностью стереть информацию в текущей БД',
                                             label_style=ft.TextStyle(weight=ft.FontWeight.W_500),
                                             value=False, on_change=self.handle_erasure_checkbox)
        # named buttons
        self.pick_path_button = ft.FilledTonalButton('Выбрать файл импорта БД', icon=ft.Icons.FOLDER_OPEN,
                                                     style=UNIFIED_BUTTON_STYLE, on_click=self.wrap_file_picking)

        self.pick_path_button_container = ft.Container(self.pick_path_button, margin=ft.margin.only(top=4))

        self.import_db_button = ft.FilledTonalButton(
            'Импортировать данные информацию в БД', style=UNIFIED_BUTTON_STYLE, on_click=self.wrap_db_import
        )

        # warning dialog modal
        self.warning_dialog = ft.AlertDialog(
            title=ft.Text('Требуется действие', color=ft.Colors.ORANGE),
            content=None,
            modal=True
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
            self.erase_db_checkbox,
            self.import_db_button,
            self.warning_dialog,
            self.error_dialog
        )

        self.loading_view = (
            ft.Container(
                ft.ProgressRing(),
                width=40, height=40,
                margin=ft.margin.only(top=self.page.height / 3),
                alignment=ft.alignment.center
            ),
            self.warning_dialog,
            self.error_dialog
        )

        # main content container with the initial view's content
        self.content_container = ft.Container(
            ft.Column(self.initial_view),
            margin=ft.margin.symmetric(vertical=5), alignment=ft.alignment.center
        )

    def build(self):
        """Returns an initial layout."""
        # (this atrocity is needed to ensure the central positioning with a complex layout)
        return ft.Column([ft.Row([self.content_container], alignment=ft.MainAxisAlignment.CENTER)])

    def wrap_file_picking(self, e=None):
        """Opens a file picker dialog for selecting the dump file path."""
        self.file_picker.pick_files(
            dialog_title='Выбор расположения файла импорта БД',
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['json']
        )

    def assess_dump_file_path(self, e=None):
        """Validates the selected file path and updates the UI accordingly."""
        if e.files is not None:
            filepath = e.files[0].path

            if filepath:
                directory = os.path.dirname(filepath)

                if os.access(directory, os.R_OK):
                    self.dump_filepath = filepath

                    self.filepath_label_container.content.value = f'Путь: {truncate_string(filepath, 50)}'

                    self.content_container.content.controls = self.loaded_path_view
                    self.content_container.update()

                else:
                    self.show_error_dialog(text='Невозможно прочитать файл по данному пути. Выберите другой.')

    def handle_erasure_checkbox(self, e=None):
        """
        Manages the erasure checkbox state and the flag of the db erasure
        itself. Opens a confirmation dialog for erasure confirmation.
        """
        if self.db_erasure_confirmed:
            self.db_erasure_confirmed = False

        else:
            self.open_confirmation_dialog_on_db_erasure()

    def open_confirmation_dialog_on_db_erasure(self):
        """
        Opens a confirmation dialog for user to decide whether
        they sure about the decision to completely erase the db.
        """
        self.warning_dialog.content = ft.Text(
            value='Вы точно уверены, что хотите перезаписать '
                  'все данные в БД? Эту операцию нельзя отменить.',
            size=16
        )

        self.warning_dialog.actions = [
            ft.TextButton('Перезаписать', style=UNIFIED_BUTTON_STYLE, on_click=self.confirm_db_erasure),
            ft.TextButton('Отменить', style=UNIFIED_BUTTON_STYLE, on_click=self.decline_db_erasure)
        ]

        self.open_warning_dialog()

    def confirm_db_erasure(self, e=None):
        """Flags the db erasure as confirmed."""
        self.db_erasure_confirmed = True
        self.close_warning_dialog(e)

    def decline_db_erasure(self, e=None):
        """Flags the db erasure as declined."""
        self.erase_db_checkbox.value = False

        self.erase_db_checkbox.update()
        self.db_erasure_confirmed = False

        self.close_warning_dialog(e)

    def wrap_db_import(self, e=None):
        """Runs the DB import process asynchronously."""
        self.page.run_task(self._adjust_layout_and_await_db_import)

    async def _adjust_layout_and_await_db_import(self):
        """Updates the UI before and after the DB import process, awaits the DB importing."""
        self.content_container.content.controls = self.loading_view
        self.content_container.update()

        self.ready_to_leave = False

        db_import_result = await self._import_data_from_db_dump()
        sleep(0.25)  # waiting to avoid flickering

        self.content_container.content.controls = self.initial_view
        self.content_container.update()

        if db_import_result['success']:
            snackbar = ft.SnackBar(ft.Text('Данные были успешно загружены в БД.'), duration=1500)
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
            
        self.ready_to_leave = True

    async def _import_data_from_db_dump(self):
        """
        Imports the data from the json dump file into the db validating them and
        catching the exceptions. Asks for the user's confirmation on conflicts.
        """
        try:
            with open(self.dump_filepath, 'r', encoding='utf-8') as file:
                dump_data = load(file)

        except (FileNotFoundError, PermissionError):
            self.show_error_dialog(text='Не удалось открыть файл по данному пути, '
                                        'попробуйте другой путь или имя файла.')
            return {'success': False}

        except JSONDecodeError:
            self.show_error_dialog(text='Структура данного файла не соответствует искомой. Попробуйте другой файл.')
            return {'success': False}

        except Exception as err:
            self.show_error_dialog(text=f'Не удалось прочитать файл из-за внутренней ошибки: {err}.')
            return {'success': False}

        plants_related_data = dump_data.get('plants_related_data', {})
        mixtures_related_data = dump_data.get('mixtures_related_data', {})

        if not isinstance(plants_related_data, dict) or not isinstance(mixtures_related_data, dict):
            self.show_error_dialog(text='Структура данного файла не соответствует искомой. Попробуйте другой файл.')
            return {'success': False}

        if not plants_related_data and not mixtures_related_data:
            self.show_error_dialog(text='Файл экспорта БД пуст. Попробуйте другой файл.')
            return {'success': False}

        if not mixtures_related_data and self.db_erasure_confirmed:
            user_input_future = asyncio.Future()
            self.open_confirmation_dialog_on_empty_mixtures_data_import(user_input_future)
            user_choice = await user_input_future

            await asyncio.sleep(1)

            if user_choice == 'decline':
                return {'success': False}

        at_least_one_category_created = False
        at_least_one_mixture_created = False
        there_was_successful_plant_related_transaction = False

        with db.atomic() as main_transaction:
            if self.db_erasure_confirmed:
                try:
                    for category in PlantCategory.select():
                        # deleting all data about categories, plants and episodes altogether
                        category.delete_instance(recursive=True)

                    for mixture in FertilizingMixture.select():
                        mixture.delete_instance()

                except (DoesNotExist, IntegrityError, OperationalError):
                    self.show_error_dialog(text='Произошла ошибка при попытке стереть текущую БД. Попробуйте ещё раз.')
                    main_transaction.rollback()
                    return {'success': False}

            for category in plants_related_data:
                category_name_validation_result = validate_string(category)

                if not category_name_validation_result['success']:
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='категории')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                category_name = category_name_validation_result['value'].capitalize()

                try:
                    category_id, category_created = PlantCategory.get_or_create(name=category_name)

                    if not at_least_one_category_created and category_created:
                        at_least_one_category_created = True

                except (DatabaseError, IntegrityError, OperationalError):
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_saving_error(user_input_future, data_name='категории')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                category_related_data = plants_related_data.get(category, {})

                if not isinstance(category_related_data, dict):
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='растениях')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                main_transaction_to_be_terminated = False

                for plant in category_related_data:
                    if main_transaction_to_be_terminated:
                        main_transaction.rollback()
                        return {'success': False}

                    plant_name_validation_result = validate_string(plant)

                    if not plant_name_validation_result['success']:
                        user_input_future = asyncio.Future()
                        self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='растении')
                        user_choice = await user_input_future

                        await asyncio.sleep(1)

                        if user_choice == 'decline':
                            main_transaction.rollback()
                            return {'success': False}

                        elif user_choice == 'confirm':
                            continue

                    plant_related_transaction_failed = False

                    with db.atomic() as plant_related_transaction:
                        plant_name = plant_name_validation_result['value'].capitalize()

                        try:
                            plant_record = Plant.get_or_none(name=plant_name, category=category_id)

                            if plant_record is None:
                                plant_record = Plant.create(name=plant_name, category=category_id)
                                plant_created = True

                            else:
                                plant_created = False

                            plant_id = plant_record.id

                            if not plant_created:
                                if self.db_overwriting_confirmed is None:
                                    user_input_future = asyncio.Future()
                                    self.open_confirmation_dialog_on_data_conflict(user_input_future)
                                    user_choice = await user_input_future

                                    await asyncio.sleep(1)

                                    if user_choice == 'leave':
                                        continue

                                elif not self.db_overwriting_confirmed:
                                    continue

                        except (DatabaseError, DoesNotExist, IntegrityError, OperationalError):
                            user_input_future = asyncio.Future()
                            self.open_confirmation_dialog_on_saving_error(user_input_future, data_name='растения')
                            user_choice = await user_input_future

                            await asyncio.sleep(1)

                            if user_choice == 'decline':
                                main_transaction_to_be_terminated = True

                            elif user_choice == 'confirm':
                                plant_related_transaction.rollback()

                            continue

                        related_fertilizing_episodes = category_related_data.get(plant, [])

                        if not isinstance(related_fertilizing_episodes, list) or not related_fertilizing_episodes:
                            user_input_future = asyncio.Future()
                            self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                 data_name='подкормках')
                            user_choice = await user_input_future

                            await asyncio.sleep(1)

                            if user_choice == 'decline':
                                main_transaction_to_be_terminated = True

                            elif user_choice == 'confirm':
                                plant_related_transaction.rollback()

                            continue

                        if not plant_created:
                            PlantFertilizingEpisode.delete().where(PlantFertilizingEpisode.plant == plant_id).execute()

                        for fertilizing_episode in related_fertilizing_episodes:
                            if not isinstance(fertilizing_episode, dict):
                                user_input_future = asyncio.Future()
                                self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                     data_name='подкормке')
                                user_choice = await user_input_future

                                await asyncio.sleep(1)

                                if user_choice == 'decline':
                                    main_transaction_to_be_terminated = True

                                elif user_choice == 'confirm':
                                    plant_related_transaction.rollback()
                                    plant_related_transaction_failed = True

                                break

                            desired_fields = {'nitrogen_mass', 'phosphorus_mass', 'potassium_mass',
                                              'magnesium_sulfate_mass', 'plant_life_stage_description',
                                              'total_repetitions'}

                            if not desired_fields <= fertilizing_episode.keys():
                                user_input_future = asyncio.Future()
                                self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                     data_name='подкормке')
                                user_choice = await user_input_future

                                await asyncio.sleep(1)

                                if user_choice == 'decline':
                                    main_transaction_to_be_terminated = True

                                elif user_choice == 'confirm':
                                    plant_related_transaction.rollback()
                                    plant_related_transaction_failed = True

                                break

                            episode_data = {
                                'nitrogen_mass': fertilizing_episode['nitrogen_mass'],
                                'phosphorus_mass': fertilizing_episode['phosphorus_mass'],
                                'potassium_mass': fertilizing_episode['potassium_mass'],
                                'magnesium_sulfate_mass': fertilizing_episode['magnesium_sulfate_mass'],
                                'plant_life_stage_description': fertilizing_episode['plant_life_stage_description'],
                                'total_repetitions': fertilizing_episode['total_repetitions']
                            }

                            cleaned_data = {}

                            import_to_be_continued_further = False

                            for mass_field_name, mass in list(episode_data.items())[:4]:
                                mass_validation_result = validate_decimal_string(mass, min_value=0, max_value=9999.99)

                                if not mass_validation_result['success']:
                                    user_input_future = asyncio.Future()
                                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                         data_name='подкормке')
                                    user_choice = await user_input_future

                                    await asyncio.sleep(1)

                                    if user_choice == 'decline':
                                        main_transaction_to_be_terminated = True

                                    elif user_choice == 'confirm':
                                        plant_related_transaction.rollback()
                                        plant_related_transaction_failed = True
                                        import_to_be_continued_further = True

                                    break

                                cleaned_data[mass_field_name] = mass_validation_result['value']

                            if main_transaction_to_be_terminated or import_to_be_continued_further:
                                break

                            life_stage_validation_result = validate_string(episode_data['plant_life_stage_description'])
                            if not life_stage_validation_result['success']:
                                user_input_future = asyncio.Future()
                                self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                     data_name='подкормке')
                                user_choice = await user_input_future

                                await asyncio.sleep(1)

                                if user_choice == 'decline':
                                    main_transaction_to_be_terminated = True

                                elif user_choice == 'confirm':
                                    plant_related_transaction.rollback()
                                    plant_related_transaction_failed = True

                                break

                            cleaned_data['plant_life_stage_description'] = life_stage_validation_result['value']

                            total_repetitions_validation_result = validate_int_string(episode_data['total_repetitions'])
                            if not total_repetitions_validation_result['success']:
                                user_input_future = asyncio.Future()
                                self.open_confirmation_dialog_on_invalid_import_data(user_input_future,
                                                                                     data_name='подкормке')
                                user_choice = await user_input_future

                                await asyncio.sleep(1)

                                if user_choice == 'decline':
                                    main_transaction_to_be_terminated = True

                                elif user_choice == 'confirm':
                                    plant_related_transaction.rollback()
                                    plant_related_transaction_failed = True

                                break

                            cleaned_data['total_repetitions'] = total_repetitions_validation_result['value']

                            try:
                                PlantFertilizingEpisode.create(
                                    nitrogen_mass=cleaned_data['nitrogen_mass'],
                                    phosphorus_mass=cleaned_data['phosphorus_mass'],
                                    potassium_mass=cleaned_data['potassium_mass'],
                                    magnesium_sulfate_mass=cleaned_data['magnesium_sulfate_mass'],
                                    plant_life_stage_description=cleaned_data['plant_life_stage_description'],
                                    total_repetitions=cleaned_data['total_repetitions'],
                                    plant=plant_id
                                )

                            except (DatabaseError, DoesNotExist, IntegrityError, OperationalError):
                                user_input_future = asyncio.Future()
                                self.open_confirmation_dialog_on_saving_error(user_input_future, data_name='подкормки')
                                user_choice = await user_input_future

                                await asyncio.sleep(1)

                                if user_choice == 'decline':
                                    main_transaction_to_be_terminated = True

                                elif user_choice == 'confirm':
                                    plant_related_transaction.rollback()
                                    plant_related_transaction_failed = True

                                break

                    if main_transaction_to_be_terminated:
                        main_transaction.rollback()
                        return {'success': False}

                    if not plant_related_transaction_failed and not there_was_successful_plant_related_transaction:
                        there_was_successful_plant_related_transaction = True

            for mixture in mixtures_related_data:
                mixture_name_validation_result = validate_string(mixture)

                if not mixture_name_validation_result['success']:
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='удобрении',
                                                                         preposition='об')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                mixture_name = mixture_name_validation_result['value'].capitalize()

                mixture_content = mixtures_related_data.get(mixture, {})

                if not isinstance(mixture_content, dict):
                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='удобрении',
                                                                         preposition='об')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                desired_fields = {'nitrogen_percentage', 'phosphorus_percentage',
                                  'potassium_percentage', 'price_per_gram'}

                if not desired_fields <= mixture_content.keys():
                    self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='удобрении',
                                                                         preposition='об')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

                mixture_data = {
                    'nitrogen_percentage': mixture_content['nitrogen_percentage'],
                    'phosphorus_percentage': mixture_content['phosphorus_percentage'],
                    'potassium_percentage': mixture_content['potassium_percentage'],
                    'price_per_gram': mixture_content['price_per_gram']
                }

                cleaned_data = {}

                proceed_to_next_mixture = False

                for key in mixture_data.keys():
                    min_value = 0.01 if 'price' in key else 0
                    max_value = 100 if 'percentage' in key else 9999.99

                    value_validation_result = validate_decimal_string(mixture_data[key],
                                                                      min_value=min_value, max_value=max_value)

                    if not value_validation_result['success']:
                        user_input_future = asyncio.Future()
                        self.open_confirmation_dialog_on_invalid_import_data(user_input_future, data_name='удобрении',
                                                                             preposition='об')
                        user_choice = await user_input_future

                        await asyncio.sleep(1)

                        if user_choice == 'decline':
                            main_transaction.rollback()
                            return {'success': False}

                        elif user_choice == 'confirm':
                            proceed_to_next_mixture = True
                            break

                    cleaned_data[key] = value_validation_result['value']

                if proceed_to_next_mixture:
                    continue

                mixture_record = FertilizingMixture.get_or_none(name=mixture_name)
                mixture_exists = mixture_record is not None

                if mixture_exists:
                    mixture_record_data = mixture_record.__data__.copy()
                    mixture_record_data.pop('id', None)
                    mixture_record_data.pop('name', None)

                    if mixture_record_data != cleaned_data:
                        if self.db_overwriting_confirmed is None:
                            user_input_future = asyncio.Future()
                            self.open_confirmation_dialog_on_data_conflict(user_input_future)
                            user_choice = await user_input_future

                            await asyncio.sleep(1)

                            if user_choice == 'leave':
                                continue

                        elif not self.db_overwriting_confirmed:
                            continue

                    mixture_id = mixture_record.id

                try:
                    if not mixture_exists:
                        FertilizingMixture.create(
                            name=mixture_name,
                            nitrogen_percentage=cleaned_data['nitrogen_percentage'],
                            phosphorus_percentage=cleaned_data['phosphorus_percentage'],
                            potassium_percentage=cleaned_data['potassium_percentage'],
                            price_per_gram=cleaned_data['price_per_gram']
                        )

                        if not at_least_one_mixture_created:
                            at_least_one_mixture_created = True

                    elif self.db_overwriting_confirmed:
                        FertilizingMixture.update({
                            FertilizingMixture.nitrogen_percentage: cleaned_data['nitrogen_percentage'],
                            FertilizingMixture.phosphorus_percentage: cleaned_data['phosphorus_percentage'],
                            FertilizingMixture.potassium_percentage: cleaned_data['potassium_percentage'],
                            FertilizingMixture.price_per_gram: cleaned_data['price_per_gram']
                        }).where(FertilizingMixture.id == mixture_id).execute()

                        if not at_least_one_mixture_created:
                            at_least_one_mixture_created = True

                except (DatabaseError, DoesNotExist, IntegrityError, OperationalError):
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_saving_error(user_input_future, data_name='удобрения')
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()
                        return {'success': False}

                    elif user_choice == 'confirm':
                        continue

            if not there_was_successful_plant_related_transaction and not at_least_one_mixture_created:
                if not self.db_erasure_confirmed:
                    failure_message = 'Ничего не было импортировано.' if not at_least_one_category_created else \
                        'Не было импортировано ничего, кроме пустых категорий растений (нечего отображать).'

                    self.show_error_dialog(text=failure_message)
                    await asyncio.sleep(1)

                else:
                    user_input_future = asyncio.Future()
                    self.open_confirmation_dialog_on_general_import_failure(user_input_future,
                                                                            at_least_one_category_created)
                    user_choice = await user_input_future

                    await asyncio.sleep(1)

                    if user_choice == 'decline':
                        main_transaction.rollback()

                        snackbar = ft.SnackBar(ft.Text('База данных восстановлена.'), duration=1500)
                        self.page.overlay.append(snackbar)
                        snackbar.open = True
                        self.page.update()

                return {'success': False}

            else:
                return {'success': True}

    def open_confirmation_dialog_on_empty_mixtures_data_import(self, future_object):
        """
        Opens a confirmation dialog when the imported database contains no data about the fertilizing mixtures.
        Since the fertilizing mixtures are required for mixture calculations, the user is asked whether to proceed.
        """
        self.warning_dialog.content = ft.Text(
            value='В импортируемой БД нет записей, содержащих информацию об удобрениях, '
                  'что делает расчёт смесей невозможным. Продолжить импорт?',
            size=16
        )

        self.warning_dialog.actions = [
            ft.TextButton('Продолжить', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.confirm_and_continue_import(future_object)),
            ft.TextButton('Отменить', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.decline_and_abort_import(future_object))
        ]

        self.open_warning_dialog()

    def open_confirmation_dialog_on_invalid_import_data(self, future_object, *, data_name, preposition='о'):
        """
        Opens a confirmation dialog when invalid or incompatible data is encountered during import.
        The user can either skip the problematic record or cancel the import entirely.
        """
        self.warning_dialog.content = ft.Text(
            value=f'Ошибка: обнаружены данные {preposition} {data_name} в неверном или несовместимом формате. '
                  'Отменить импорт полностью или пропустить текущую запись?',
            size=16
        )

        self.warning_dialog.actions = [
            ft.TextButton('Пропустить запись', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.confirm_and_continue_import(future_object)),
            ft.TextButton('Отменить импорт', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.decline_and_abort_import(future_object))
        ]

        self.open_warning_dialog()

    def open_confirmation_dialog_on_saving_error(self, future_object, *, data_name):
        """
        Opens a confirmation dialog when an error occurs while saving a specific record.
        The user can either skip the problematic record or cancel the import.
        """
        self.warning_dialog.content = ft.Text(
            value=f'Произошла ошибка при попытке сохранения {data_name}. '
                  'Отменить импорт полностью или пропустить текущую запись?',
            size=16
        )

        self.warning_dialog.actions = [
            ft.TextButton('Пропустить запись', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.confirm_and_continue_import(future_object)),
            ft.TextButton('Отменить импорт', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.decline_and_abort_import(future_object))
        ]

        self.open_warning_dialog()

    def open_confirmation_dialog_on_data_conflict(self, future_object):
        """
        Opens a confirmation dialog when conflicting data is found in the database.
        The user can choose to overwrite existing data or keep the current records.
        """
        self.warning_dialog.content = ft.Text(
            value='Обнаружены данные, конфликтующие с ныне присутствующими в БД. Как следует поступить?',
            size=16
        )

        self.warning_dialog.actions = [
            ft.TextButton('Перезаписать', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.confirm_data_overwriting(future_object)),
            ft.TextButton('Оставить текущие', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.decline_data_overwriting(future_object))
        ]

        self.open_warning_dialog()

    def open_confirmation_dialog_on_general_import_failure(self, future_object, empty_categories_imported=False):
        """
        Opens a confirmation dialog when the import fails entirely after wiping the database.
        The user can choose to revert the import and restore deleted data or leave the database empty.
        """
        empty_categories_imported_message = ', кроме пустых категорий растений,' if empty_categories_imported else ''

        warning_text = ('База данных была стёрта, но из-за ошибок импорта данных никакой новой информации' +
                        empty_categories_imported_message + ' загружено не было. Откатить импорт и вернуть ' +
                        'стёртые данные или оставить базу данных пустой?')

        self.warning_dialog.content = ft.Text(warning_text, size=16)

        self.warning_dialog.actions = [
            ft.TextButton('Вернуть данные', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.decline_and_abort_import(future_object)),

            ft.TextButton('Оставить БД пустой', style=UNIFIED_BUTTON_STYLE,
                          on_click=lambda e: self.confirm_and_leave(future_object))
        ]

        self.open_warning_dialog()

    def confirm_and_continue_import(self, future_object):
        """Confirms the import and proceeds to the next step."""
        future_object.set_result('confirm')
        self.close_warning_dialog()

    def decline_and_abort_import(self, future_object):
        """Cancels the import process and restores previous data if necessary."""
        future_object.set_result('decline')
        self.close_warning_dialog()

    def confirm_data_overwriting(self, future_object):
        """Confirms overwriting of existing database records."""
        self.db_overwriting_confirmed = True
        future_object.set_result('overwrite')
        self.close_warning_dialog()

    def decline_data_overwriting(self, future_object):
        """Declines overwriting and keeps existing database records."""
        self.db_overwriting_confirmed = False
        future_object.set_result('leave')
        self.close_warning_dialog()

    def confirm_and_leave(self, future_object):
        """Leaves the database empty after a failed import attempt."""
        future_object.set_result('leave_empty')
        self.close_warning_dialog()

    def open_warning_dialog(self):
        """Opens the warning dialog."""
        self.warning_dialog.open = True
        self.warning_dialog.update()

    def close_warning_dialog(self, e=None):
        """Closes the warning dialog and clears it's properties."""
        self.warning_dialog.content = None
        self.warning_dialog.actions = None
        self.warning_dialog.open = False
        self.warning_dialog.update()

    def show_error_dialog(self, text):
        """Displays an error dialog with the given message."""
        self.error_dialog.content = ft.Text(text, size=16)
        self.error_dialog.open = True
        self.error_dialog.update()

    def close_error_dialog(self, e=None):
        """Closes the error dialog."""
        self.error_dialog.open = False
        self.error_dialog.update()
