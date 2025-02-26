import pytest

from utils.utils import *


class TestUtils:
    """Tests for the 'utils' module."""
    def test_get_component_masses_type_error(self):
        """Tests TypeError raising for 'get_component_masses'."""
        with pytest.raises(TypeError):
            get_component_masses(Decimal('10.0'), Decimal('20.0'), Decimal('30.0'), 100)

        with pytest.raises(TypeError):
            get_component_masses(Decimal('10.0'), 20, Decimal('30.0'), Decimal('100'))

    def test_get_component_masses_percentage_limits(self):
        """Tests percentages limits for 'get_component_masses'."""

        # valid cases:
        result = get_component_masses(Decimal('10.0'), Decimal('20.0'), Decimal('30.0'), Decimal('100.0'))
        assert result['N'] == Decimal('10.00')
        assert result['P'] == Decimal('20.00')
        assert result['K'] == Decimal('30.00')

        # invalid cases (out of range):
        with pytest.raises(ValueError):
            get_component_masses(Decimal('-1.0'), Decimal('20.0'), Decimal('30.0'), Decimal('100.0'))

        with pytest.raises(ValueError):
            get_component_masses(Decimal('110.0'), Decimal('20.0'), Decimal('30.0'), Decimal('100.0'))

    def test_get_component_masses_precision(self):
        """Tests calculation precision for 'get_component_masses'."""
        result = get_component_masses(Decimal('33.33'), Decimal('33.33'), Decimal('33.34'), Decimal('300.0'))
        assert result['N'] == Decimal('99.99')
        assert result['P'] == Decimal('99.99')
        assert result['K'] == Decimal('100.02')

    def test_get_component_masses_rounding(self):
        """Tests rounding for 'get_component_masses'."""
        result = get_component_masses(Decimal('33.333'), Decimal('99.999'), Decimal('10.999'), Decimal('300.0'))
        assert result['N'] == Decimal('100.00')
        assert result['P'] == Decimal('300.00')
        assert result['K'] == Decimal('33.00')

    def test_apply_nano_coefficients_type_error(self):
        """Tests TypeError raising for 'apply_nano_coefficients'."""
        component_masses = {'N': Decimal('100.0'), 'P': Decimal('50.0'), 'K': Decimal('150.0')}

        with pytest.raises(TypeError):
            apply_nano_coefficients(component_masses, n_coefficient='0.5')

        with pytest.raises(TypeError):
            apply_nano_coefficients(component_masses, p_coefficient=0.5)

    def test_apply_nano_coefficients_missing_key(self):
        """Tests keys for 'apply_nano_coefficients'."""
        component_masses = {'N': Decimal('100.0'), 'P': Decimal('50.0')}

        with pytest.raises(ValueError):
            apply_nano_coefficients(component_masses)

    def test_apply_nano_coefficients_precision(self):
        """Tests calculation precision for 'apply_nano_coefficients'."""
        component_masses = {'N': Decimal('100.0'), 'P': Decimal('50.0'), 'K': Decimal('150.0')}
        apply_nano_coefficients(component_masses, n_coefficient=Decimal('0.5'), p_coefficient=Decimal('0.2'),
                                k_coefficient=Decimal('0.4'))
        assert component_masses['N'] == Decimal('50.00')
        assert component_masses['P'] == Decimal('10.00')
        assert component_masses['K'] == Decimal('60.00')

    def test_apply_nano_coefficients_rounding(self):
        """Tests rounding for 'apply_nano_coefficients'."""
        component_masses = {'N': Decimal('100.555'), 'P': Decimal('50.333'), 'K': Decimal('150.777')}
        apply_nano_coefficients(component_masses, n_coefficient=Decimal('0.5'), p_coefficient=Decimal('0.2'),
                                k_coefficient=Decimal('0.4'))
        assert component_masses['N'] == Decimal('50.28')
        assert component_masses['P'] == Decimal('10.07')
        assert component_masses['K'] == Decimal('60.31')

    def test_truncate_string_type_error(self):
        """Test types for 'truncate_string'."""
        with pytest.raises(TypeError):
            truncate_string(123)

        with pytest.raises(TypeError):
            truncate_string('Hello world', target_length='10')

    def test_truncate_string_basic(self):
        """Tests basic functionality for 'truncate_string'."""
        result = truncate_string('Hello world, this is a test string!', target_length=16)
        assert result == 'Hello world, thi...'

    def test_truncate_string_no_truncation(self):
        """Tests for 'truncate_string' if there's no need to truncate."""
        result = truncate_string('Short string', target_length=50)
        assert result == 'Short string'

    def test_truncate_string_exact_length(self):
        """Tests 'truncate_string' with a string of exact length."""
        result = truncate_string('Exact length string', target_length=19)
        assert result == 'Exact length string'

    def test_truncate_string_empty(self):
        """Tests 'truncate_string' with an empty string."""
        result = truncate_string('', target_length=10)
        assert result == ''

    def test_truncate_string_with_whitespace(self):
        """Tests 'truncate_string' for a string with whitespace."""
        result = truncate_string('Hello     ', target_length=5)
        assert result == 'Hello...'
