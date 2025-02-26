from decimal import Decimal

from peewee import (SqliteDatabase, Model, CharField, DecimalField, ForeignKeyField,
                    IntegerField, IntegrityError, DoesNotExist)

db = SqliteDatabase('app_data.db')

# DB models:

class BaseModel(Model):
    """The basic model. Determines the DB to connect."""
    class Meta:
        database = db


class PlantCategory(BaseModel):
    """A plant category storing model."""
    name = CharField(unique=True)


class Plant(BaseModel):
    """A plant storing model."""
    name = CharField(unique=True)
    category = ForeignKeyField(PlantCategory, backref='plants', on_delete='CASCADE')


class PlantFertilizingEpisode(BaseModel):
    """A fertilizing episode storing model."""
    nitrogen_mass = DecimalField(max_digits=6, decimal_places=2)
    phosphorus_mass = DecimalField(max_digits=6, decimal_places=2)
    potassium_mass = DecimalField(max_digits=6, decimal_places=2)
    magnesium_sulfate_mass = DecimalField(max_digits=6, decimal_places=2)
    plant_life_stage_description = CharField(max_length=150)
    total_repetitions = IntegerField(default=1)
    plant = ForeignKeyField(Plant, backref='fertilizing_episodes', on_delete='CASCADE')


class FertilizingMixture(BaseModel):
    """A fertilizing mixture storing model."""
    name = CharField(unique=True)
    nitrogen_percentage = DecimalField(max_digits=4, decimal_places=2)
    phosphorus_percentage = DecimalField(max_digits=4, decimal_places=2)
    potassium_percentage = DecimalField(max_digits=4, decimal_places=2)
    price_per_gram = DecimalField(max_digits=6, decimal_places=2)


def initialize_db():
    # DB initialization: creating the tables only if they aren't there
    db.connect()

    fertilizing_mixtures_table_existed = FertilizingMixture.table_exists()

    db.create_tables((PlantCategory, Plant, PlantFertilizingEpisode, FertilizingMixture), safe=True)

    if not fertilizing_mixtures_table_existed:
        initial_fertilizing_mixtures_dataset = [
            ('Азофоска 15:15:15', '15', '15', '15', '0.04'),
            ('Азофоска 16:16:16', '16', '16', '16', '0.05'),
            ('Аммиачная селитра', '33', '0', '0', '0.1'),
            ('Борофоска', '0', '10', '16', '0.1'),
            ('Кальциевая селитра', '15.5', '0', '0', '0.12'),
            ('Монокалийфосфат', '0', '50', '33', '0.45'),
            ('Селитра калиевая', '13.5', '0', '45.8', '0.34'),
            ('Сернокислый калий', '0', '0', '21', '0.23'),
            ('Сульфат магния', '0', '0', '0', '0.1'),
            ('Суперфосфат', '6', '21', '0', '0.15'),
            ('Суперфосфат двойной', '9', '42', '0', '0.15'),
            ('Хлористый калий', '0', '0', '57', '0.1'),
        ]

        with db.atomic():
            for mixture in initial_fertilizing_mixtures_dataset:
                FertilizingMixture.create(
                    name=mixture[0],
                    nitrogen_percentage=Decimal(mixture[1]),
                    phosphorus_percentage=Decimal(mixture[2]),
                    potassium_percentage=Decimal(mixture[3]),
                    price_per_gram=Decimal(mixture[4])
                )

    db.close()

# CRUD operations:

def does_category_exit(name: str) -> bool:
    """
    Checks whether the plant category object exists in the database.

    :param name: the unique name of the category to check.
    :return: True if the plant object exists in the db, False if it does not.
    :raises TypeError: if a format of the entered data is not str.
    """
    if not isinstance(name, str):
        raise TypeError(f'Wrong data format: expected an str instance, got {type(name).__name__} instead.')

    return PlantCategory.select().where(PlantCategory.name == name.capitalize()).exists()


def create_plant_category(name: str) -> dict:
    """
    Creates a new plant category in the database.

    :param name: the name of the category.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'error_code': str | None - a short code representing an error occurred,
        'category_id': int | None - an id of the created object in the db.
    """
    if not isinstance(name, str) or not name.strip():
        return {'success': False, 'error': 'Название категории должно быть непустой строкой.',
                'error_code': 'invalid_name_format'}

    try:
        with db.atomic():
            category = PlantCategory.create(name=name.capitalize())
            return {'success': True, 'category_id': category.id}

    except IntegrityError as err:
        if 'UNIQUE constraint' in str(err):
            return {'success': False, 'error': 'Категория с таким названием уже существует.',
                    'error_code': 'already_exists'}
        else:
            return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.',
                    'error_code': 'db_constraint_error'}

    except Exception as err:
        return {'success': False, 'error': f'Произошла непредвиденная ошибка: {str(err)}.',
                'error_code': 'db_error'}


def rename_plant_category(identifier: int, new_name: str) -> dict:
    """
    Renames an existing plant category in the database.

    :param identifier: the id of the category to rename.
    :param new_name: the new name for the category.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'category_id': int | None - an id of the renamed category in the db.
    """
    if not isinstance(identifier, int):
        return {'success': False, 'error': 'ID категории должен быть числом.'}

    if not isinstance(new_name, str) or not new_name.strip():
        return {'success': False, 'error': 'Новое название категории должно быть непустой строкой.'}

    try:
        with db.atomic():
            category = PlantCategory.get_by_id(identifier)
            category.name = new_name.capitalize()
            category.save()

            return {'success': True, 'category_id': category.id}

    except IntegrityError as err:
        if 'UNIQUE constraint' in str(err):
            return {'success': False, 'error': 'Категория с таким названием уже существует.'}
        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except DoesNotExist:
        return {'success': False, 'error': 'Категория с указанным ID не найдена.'}

    except Exception as err:
        return {'success': False, 'error': f'Произошла непредвиденная ошибка: {str(err)}.'}


def delete_plant_category(identifier: int) -> dict:
    """
    Deletes the plant category from the database.

    :param identifier: the id of the category to delete.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error.
    """
    if not isinstance(identifier, int):
        return {'success': False, 'error': 'ID категории должен быть числом.'}

    try:
        with db.atomic():
            category = PlantCategory.get_by_id(identifier)
            category.delete_instance(recursive=True)
            return {'success': True}

    except DoesNotExist:
        return {'success': False, 'error': 'Категория с указанным ID не найдена.'}

    except IntegrityError as err:
        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as err:
        return {'success': False, 'error': f'Произошла непредвиденная ошибка: {str(err)}.'}


def does_plant_exist(name: str) -> bool:
    """
    Checks whether the plant object exists in the database.

    :param name: the unique name of the plant to check.
    :return: True if the plant object exists in the db, False if it does not.
    :raises TypeError: if a format of the entered data is not str.
    """
    if not isinstance(name, str):
        raise TypeError(f'Wrong data format: expected an str instance, got {type(name).__name__} instead.')

    return Plant.select().where(Plant.name == name.capitalize()).exists()


def create_plant(name: str, category_id: int) -> dict:
    """
    Creates a new plant in the database.

    :param name: the name of the plant.
    :param category_id: an id of the category of the plant (must be an id of an existing Category record).
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'plant_id': int | None - an id of the created object in the db.
    """
    if not isinstance(name, str) or not name.strip():
        return {'success': False, 'error': 'Название растения должно быть непустой строкой.'}

    if not isinstance(category_id, int):
        return {'success': False, 'error': 'Неверный формат id категории растения.'}

    try:
        with db.atomic():
            category = PlantCategory.get_by_id(category_id)
            plant = Plant.create(
                name=name.capitalize(),
                category=category
            )
            return {'success': True, 'plant_id': plant.id}

    except DoesNotExist:
        return {'success': False, 'error': 'Указанная категория растения не существует.'}

    except IntegrityError as err:
        if 'UNIQUE constraint' in str(err):
            return {'success': False, 'error': 'Растение с таким названием уже существует.'}

        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as err:
        return {'success': False, 'error': f'Неизвестная ошибка: {str(err)}.'}


def rename_plant(identifier: int, new_name: str) -> dict:
    """
    Renames an existing plant in the database.

    :param identifier: the id of the plant to rename.
    :param new_name: the new name for the plant.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'plant_id': int | None - an id of the renamed plant in the db.
    """
    if not isinstance(identifier, int):
        return {'success': False, 'error': 'ID растения должно быть целым числом.'}

    if not isinstance(new_name, str) or not new_name.strip():
        return {'success': False, 'error': 'Новое название растения должно быть непустой строкой.'}

    try:
        with db.atomic():
            plant = Plant.get_by_id(identifier)
            plant.name = new_name.capitalize()
            plant.save()

            return {'success': True, 'plant_id': plant.id}

    except DoesNotExist:
        return {'success': False, 'error': 'Растение с указанным ID не найдено.'}

    except IntegrityError as err:
        if 'UNIQUE constraint' in str(err):
            return {'success': False, 'error': 'Растение с таким названием уже существует.'}
        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as e:
        return {'success': False, 'error': f'Неизвестная ошибка: {str(e)}.'}


def delete_plant(identifier: int) -> dict:
    """
    Deletes the plant from the database.

    :param identifier: the id of the plant to delete.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error.
    """
    if not isinstance(identifier, int):
        return {'success': False, 'error': 'ID растения должен быть числом.'}

    try:
        with db.atomic():
            plant = Plant.get_by_id(identifier)
            plant.delete_instance(recursive=True)
            return {'success': True}

    except DoesNotExist:
        return {'success': False, 'error': 'Растение с указанным ID не найдено.'}

    except IntegrityError as err:
        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as err:
        return {'success': False, 'error': f'Произошла непредвиденная ошибка: {str(err)}.'}


def create_fertilizing_episode(plant_id: int, nitrogen_mass: Decimal, phosphorus_mass: Decimal,
                               potassium_mass: Decimal, magnesium_sulfate_mass: Decimal,
                               plant_life_stage_description: str,
                               total_repetitions: int = 1) -> dict:
    """
    Creates a new fertilizing episode for a plant in the database.

    :param plant_id: the id of the plant to associate with this fertilizing episode.
    :param nitrogen_mass: the absolute mass of nitrogen in the fertilizing material.
    :param phosphorus_mass: the absolute mass of phosphorus in the fertilizing material.
    :param potassium_mass: the absolute mass of potassium in the fertilizing material.
    :param magnesium_sulfate_mass: the absolute mass of magnesium sulfate in the fertilizing material.
    :param plant_life_stage_description: a description of the plant's life stage during this fertilizing episode.
    :param total_repetitions: the number of repetitions of this fertilizing episode.
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'episode_id': int | None - an id of the created fertilizing episode in the db.
    """
    if not isinstance(plant_id, int):
        return {'success': False, 'error': 'ID растения должен быть целым числом.'}

    for mass in (nitrogen_mass, phosphorus_mass, potassium_mass, magnesium_sulfate_mass):
        if not isinstance(mass, Decimal):
            return {'success': False, 'error': 'Масса элементов должна быть числом (Decimal).'}

        if not (0 <= mass <= Decimal('9999.99')):
            return {'success': False, 'error': 'Масса элементов должна быть в диапазоне от 0.00 до 9999.99.'}

        if abs(mass.as_tuple().exponent) > 2:
            return {'success': False, 'error': 'Масса элементов должна содержать не более двух знаков после запятой.'}

    if not isinstance(total_repetitions, int) or total_repetitions < 1:
        return {'success': False, 'error': 'Количество повторений должно быть целым числом больше 0.'}

    if plant_life_stage_description and (not isinstance(plant_life_stage_description, str) or
                                         len(plant_life_stage_description) > 150):
        return {'success': False, 'error': 'Описание стадии жизненного цикла должно быть строкой '
                                           'длиной до 150 символов.'}

    try:
        with db.atomic():
            plant = Plant.get_by_id(plant_id)
            episode = PlantFertilizingEpisode.create(
                nitrogen_mass=nitrogen_mass,
                phosphorus_mass=phosphorus_mass,
                potassium_mass=potassium_mass,
                magnesium_sulfate_mass=magnesium_sulfate_mass,
                plant_life_stage_description=plant_life_stage_description,
                total_repetitions=total_repetitions,
                plant=plant
            )
            return {'success': True, 'episode_id': episode.id}

    except DoesNotExist:
        return {'success': False, 'error': 'Растение с указанным ID не найдено.'}

    except IntegrityError as err:
        return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as err:
        return {'success': False, 'error': f'Неизвестная ошибка: {str(err)}.'}


def create_fertilizing_mixture(name: str, nitrogen_percentage: Decimal, phosphorus_percentage: Decimal,
                               potassium_percentage: Decimal, price_per_gram: Decimal) -> dict:
    """
    Creates a new fertilizing mixture in the database.

    :param name: the name of the mixture.
    :param nitrogen_percentage: the percentage of nitrogen in the mixture.
    :param phosphorus_percentage: the percentage of phosphorus in the mixture.
    :param potassium_percentage: the percentage of potassium in the mixture.
    :param price_per_gram: an approximate price for the gram of the mixture (in rubles).
    :return: a dict with the info about the operation:
        'success': bool - True if the operation was successful, False if it was not,
        'error': str | None - a description of an occurred error,
        'mixture_id': int | None - an id of the created fertilizing mixture in the db.
    """
    if not isinstance(name, str) or not name.strip():
        return {'success': False, 'error': 'Название удобрения должно быть непустой строкой.'}

    for element in (nitrogen_percentage, phosphorus_percentage, potassium_percentage, price_per_gram):
        if not isinstance(element, Decimal):
            return {'success': False, 'error': 'Данные должны иметь числовой формат (Decimal).'}

        if abs(element.as_tuple().exponent) > 2:
            return {'success': False, 'error': 'Данные должны содержать не более двух знаков после запятой.'}

    for percentage in (nitrogen_percentage, phosphorus_percentage, potassium_percentage):
        if not (0 <= percentage <= Decimal('99.99')):
            return {'success': False, 'error': 'Процентные значения должны быть в диапазоне от 0.00 до 99.99.'}

    if not (0 < price_per_gram <= Decimal(9999.99)):
        return {'success': False, 'error': 'Цена за грамм удобрения должна быть в диапазоне от 0.01 до 9999.99.'}

    try:
        with db.atomic():
            mixture = FertilizingMixture.create(
                name=name.capitalize(),
                nitrogen_percentage=nitrogen_percentage,
                phosphorus_percentage=phosphorus_percentage,
                potassium_percentage=potassium_percentage,
                price_per_gram=price_per_gram
            )
            return {'success': True, 'mixture_id': mixture.id}

    except IntegrityError as err:
        if 'UNIQUE constraint' in str(err):
            return {'success': False, 'error': 'Удобрение с таким названием уже существует.'}
        else:
            return {'success': False, 'error': f'Ошибка базы данных: {str(err)}.'}

    except Exception as err:
        return {'success': False, 'error': f'Неизвестная ошибка: {str(err)}.'}
