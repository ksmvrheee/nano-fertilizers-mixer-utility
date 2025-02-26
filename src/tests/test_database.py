import pytest

from database import *


@pytest.fixture(autouse=True)
def test_db():
    """
    Set up an in-memory SQLite database for testing.
    Bind all models to the test DB, create tables before each test,
    and drop them after the test.
    """
    test_db = SqliteDatabase(':memory:')
    db.init(':memory:')
    db.bind([PlantCategory, Plant, PlantFertilizingEpisode, FertilizingMixture])
    db.connect()
    db.create_tables([PlantCategory, Plant, PlantFertilizingEpisode, FertilizingMixture])
    yield
    db.drop_tables([PlantCategory, Plant, PlantFertilizingEpisode, FertilizingMixture])
    db.close()

class TestDBOperations:
    """Unit tests for DB models and CRUD operations using Peewee ORM."""

    def test_create_plant_category_success(self):
        """Test successful creation of a plant category and existence check."""
        result = create_plant_category('Vegetables')
        assert result['success'] is True
        assert 'category_id' in result
        # check that the category exists (name is capitalized by the function)
        assert does_category_exit('vegetables')

    def test_create_plant_category_invalid_name(self):
        """Test creation fails when the category name is empty."""
        result = create_plant_category('')
        assert not result['success']
        assert result['error'] == 'Название категории должно быть непустой строкой.'

    def test_create_duplicate_plant_category(self):
        """Test that creating a duplicate category returns an error."""
        create_plant_category('Flowers')
        result = create_plant_category('flowers')  # имя приводится к capitalize()
        assert not result['success']
        assert result['error'] == 'Категория с таким названием уже существует.'

    def test_rename_plant_category_success(self):
        """Test renaming an existing plant category."""
        create_result = create_plant_category('Herbs')
        cat_id = create_result['category_id']
        result = rename_plant_category(cat_id, 'Spices')
        assert result['success']
        # can't access the category by the old name after renaming it
        assert not does_category_exit('herbs')
        assert does_category_exit('spices')

    def test_rename_plant_category_nonexistent(self):
        """Test renaming fails if the category does not exist."""
        result = rename_plant_category(9999, 'Nonexistent')
        assert not result['success']
        assert result['error'] == 'Категория с указанным ID не найдена.'

    def test_delete_plant_category_success(self):
        """Test deletion of an existing plant category."""
        create_result = create_plant_category('Trees')
        cat_id = create_result['category_id']
        result = delete_plant_category(cat_id)
        assert result['success'] is True
        # can't access the category after it's been deleted
        assert not does_category_exit('trees')

    def test_create_plant_success(self):
        """Test successful creation of a plant with a valid category."""
        cat_result = create_plant_category('Fruits')
        cat_id = cat_result['category_id']
        plant_result = create_plant('Apple', cat_id)
        assert plant_result['success'] is True
        assert 'plant_id' in plant_result
        assert does_plant_exist('Apple')

    def test_create_plant_invalid_category(self):
        """Test that plant creation fails if the given category ID does not exist."""
        result = create_plant('Banana', 9999)
        assert not result['success']
        assert result['error'] == 'Указанная категория растения не существует.'

    def test_rename_plant_success(self):
        """Test renaming an existing plant."""
        cat_result = create_plant_category('Cereals')
        cat_id = cat_result['category_id']
        plant_result = create_plant('Wheat', cat_id)
        plant_id = plant_result['plant_id']
        rename_result = rename_plant(plant_id, 'Barley')
        assert rename_result['success']
        assert not does_plant_exist('Wheat')
        assert does_plant_exist('Barley')

    def test_delete_plant_success(self):
        """Test deletion of a plant."""
        cat_result = create_plant_category('Shrubs')
        cat_id = cat_result['category_id']
        plant_result = create_plant('Rose', cat_id)
        plant_id = plant_result['plant_id']
        delete_result = delete_plant(plant_id)
        assert delete_result['success']
        assert not does_plant_exist('Rose')

    def test_create_fertilizing_episode_success(self):
        """Test creating a fertilizing episode for an existing plant."""
        cat_result = create_plant_category('Orchids')
        cat_id = cat_result['category_id']
        plant_result = create_plant('Orchid', cat_id)
        plant_id = plant_result['plant_id']
        episode_result = create_fertilizing_episode(
            plant_id,
            Decimal('10.00'),
            Decimal('5.00'),
            Decimal('3.00'),
            Decimal('2.00'),
            'Начало цветения',
            total_repetitions=1
        )
        assert episode_result['success']
        assert 'episode_id' in episode_result

    def test_create_fertilizing_mixture_success(self):
        """Test successful creation of a fertilizing mixture."""
        mixture_result = create_fertilizing_mixture(
            'Mix1',
            Decimal('10.00'),
            Decimal('15.00'),
            Decimal('20.00'),
            Decimal('0.50')
        )
        assert mixture_result['success']
        assert 'mixture_id' in mixture_result
