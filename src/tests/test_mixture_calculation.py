import pytest

from core.mixture_calculation import calculate_best_mixture


class FakeFertilizingMixture:
    """Dataclass for storing the fake fertilizing mixture properties."""
    def __init__(self, name, nitrogen_percentage, phosphorus_percentage, potassium_percentage, price_per_gram):
        self.name = name
        self.nitrogen_percentage = nitrogen_percentage
        self.phosphorus_percentage = phosphorus_percentage
        self.potassium_percentage = potassium_percentage
        self.price_per_gram = price_per_gram


class FakeQuery:
    """Mock class simulating a database query to perform an ordering correctly."""
    def __init__(self, mixtures):
        self.mixtures = mixtures

    def order_by(self, attr):  # mocking the ordering method which will be called while making a query
        return sorted(self.mixtures, key=lambda x: getattr(x, attr))


class FakeFertilizingMixtureWrapper:
    """Wrapper mock class simulating retrieving the records from the db."""
    name = 'name'  # for ordering not to break

    def __init__(self, mixtures=None):
        self.mixtures = mixtures or [
            FakeFertilizingMixture('FertCheap', 10, 5, 5, 0.01),
            FakeFertilizingMixture('FertExpensive', 20, 20, 20, 0.15),
            FakeFertilizingMixture('FertBalanced', 12, 12, 12, 0.08),
            FakeFertilizingMixture('FertUnbalanced', 25, 5, 15, 0.25)
        ]  # exemplary set of mixtures

    def select(self):  # mocking the 'select' method, returning the FakeQuery object
        return FakeQuery(self.mixtures)


@pytest.fixture
def patch_fertilizing_mixture_success(monkeypatch):
    """Fixture to mock the successful request to the db through the wrapper (standard dataset)."""
    fake_fertilizing_mixture = FakeFertilizingMixtureWrapper()
    monkeypatch.setattr('core.mixture_calculation.FertilizingMixture', fake_fertilizing_mixture)


@pytest.fixture
def patch_fertilizing_mixture_failure(monkeypatch):
    """Fixture to mock the unsuccessful request to the db through the wrapper (invalid dataset)."""
    fake_fertilizing_mixture = FakeFertilizingMixtureWrapper([FakeFertilizingMixture('FertZero', 0, 0, 0, 0.05)])
    monkeypatch.setattr('core.mixture_calculation.FertilizingMixture', fake_fertilizing_mixture)


class TestCalculateBestMixture:
    """Tests for the 'calculate_best_mixture' function."""
    def test_invalid_total_mass(self, patch_fertilizing_mixture_success):
        """Checks that the result is negative with invalid mass (0 g)."""
        result = calculate_best_mixture(10, 10, 10, 0)
        
        assert not result['success']
        assert 'масса должна быть больше нуля' in result['error']

    @pytest.mark.parametrize('nitrogen, phosphorus, potassium, total_mass', [
        ('10', 10, 10, 30),
        (10, '10', 10, 30),
        (10, 10, '10', 30),
        (10, 10, 10, '30'),
    ])
    def test_invalid_input_type(self, nitrogen, phosphorus, potassium, total_mass, patch_fertilizing_mixture_success):
        """Checks that an exception fires if one of the args is of invalid type."""
        with pytest.raises(TypeError):
            calculate_best_mixture(nitrogen, phosphorus, potassium, total_mass)

    def test_unsolvable_optimization(self, patch_fertilizing_mixture_failure):
        """Checks that the result is negative if the optimization is not executable (invalid dataset)."""
        result = calculate_best_mixture(10, 10, 10, 30)
        assert not result['success']
        assert 'не удалось подобрать нужный состав' in result['error']

    def test_successful_optimization(self, patch_fertilizing_mixture_success):
        """Checks the successful optimization."""
        nitrogen_mass, phosphorus_mass, potassium_mass, total_mass = 100, 100, 100, 300
        result = calculate_best_mixture(nitrogen_mass, phosphorus_mass, potassium_mass, total_mass)

        assert result['success']

        composition_data = {item['name']: item['mass_in_grams'] for item in result['mixture']}

        assert 'FertUnbalanced' not in composition_data.keys()
        assert all(100 <= mass <= 100.5 for mass in result['actual_composition'].values())
        assert sum(composition_data.values()) >= nitrogen_mass + phosphorus_mass + potassium_mass
