import pytest

from utils.validation import *


class TestStringsValidation:
    @pytest.mark.parametrize('value, required, expected', [
        ('Valid string', True, {'success': True, 'value': 'Valid string'}),
        ('  Trimmed string  ', True, {'success': True, 'value': 'Trimmed string'}),
        ('', True, {'success': False, 'error': 'Значение не должно быть пустым.'}),
        ('', False, {'success': True, 'value': ''}),
        (123, True, {'success': False, 'error': 'Значение должно быть строкой.'}),
        (None, True, {'success': False, 'error': 'Значение должно быть строкой.'}),
    ])
    def test_validate_string(self, value, required, expected):
        """Tests string validation, including empty and non-string values."""
        assert validate_string(value, required=required) == expected

    @pytest.mark.parametrize('value_str, min_value, max_value, max_decimals, expected', [
        ('10.50', 0, 100, 2, {'success': True, 'value': Decimal('10.50')}),
        ('-5.00', 0, 100, 2, {'success': False, 'error': 'Значение должно быть больше или равным 0.'}),
        ('1.001', 0, 100, 2, {'success': False, 'error': 'Значение должно содержать не более 2 знаков после запятой.'}),
        ('200', 0, 100, 2, {'success': False, 'error': 'Значение должно быть меньше или равным 100.'}),
        ('abc', 0, 100, 2, {'success': False, 'error': 'Значение должно быть числом.'}),
    ])
    def test_validate_decimal_string(self, value_str, min_value, max_value, max_decimals, expected):
        """Tests decimal string validation, including min/max constraints and decimal places."""
        assert validate_decimal_string(value_str, min_value=min_value,
                                       max_value=max_value, max_decimals=max_decimals) == expected

    @pytest.mark.parametrize('value_str, min_value, max_value, expected', [
        ('10', 0, 100, {'success': True, 'value': 10}),
        ('-5', 0, 100, {'success': False, 'error': 'Значение должно быть больше или равным 0.'}),
        ('200', 0, 100, {'success': False, 'error': 'Значение должно быть меньше или равным 100.'}),
        ('abc', 0, 100, {'success': False, 'error': 'Значение должно быть числом.'}),
    ])
    def test_validate_int_string(self, value_str, min_value, max_value, expected):
        """Tests integer string validation, including min/max constraints."""
        assert validate_int_string(value_str, min_value=min_value, max_value=max_value) == expected

    @pytest.mark.parametrize('value_str, expected', [
        ('5', {'success': True, 'value': 5}),
        ('0', {'success': False, 'error': 'Значение должно быть больше или равным 1.'}),
        ('-10', {'success': False, 'error': 'Значение должно быть больше или равным 1.'}),
    ])
    def test_validate_positive_integer_string(self, value_str, expected):
        """Tests validation of positive integers (minimum 1)."""
        assert validate_positive_integer_string(value_str) == expected

    @pytest.mark.parametrize('value_str, expected', [
        ('50.5', {'success': True, 'value': Decimal('50.5')}),
        ('101', {'success': False, 'error': 'Процент должен быть меньше или равным 100.'}),
        ('-1', {'success': False, 'error': 'Процент должен быть больше или равным 0.'}),
        ('50.123', {'success': False, 'error': 'Процент должен содержать не более 2 знаков после запятой.'}),
    ])
    def test_validate_percentage_string(self, value_str, expected):
        """Tests percentage validation (0–100) with up to 2 decimal places."""
        assert validate_percentage_string(value_str) == expected

    @pytest.mark.parametrize('value_str, expected', [
        ('10.5', {'success': True, 'value': Decimal('10.5')}),
        ('-1', {'success': False, 'error': 'Значение должно быть больше или равным 0.'}),
        ('50.123', {'success': False, 'error': 'Значение должно содержать не более 2 знаков после запятой.'}),
    ])
    def test_validate_non_negative_decimal_string(self, value_str, expected):
        """Tests validation of non-negative decimals (>=0, max 2 decimal places)."""
        assert validate_non_negative_decimal_string(value_str) == expected
