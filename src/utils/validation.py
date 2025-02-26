from decimal import Decimal, InvalidOperation


def validate_string(value, field_name='Значение', required=True, gender='n'):
    """
    Validates that the field is a string and, if required, is non-empty, with gender-specific error messages.

    :param value: the value to validate.
    :param field_name: the name of the field for error messages.
    :param required: if True, the field must not be empty.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (str).
    """

    # gender-specific verb forms for Russian
    verb_form = {
        'm': 'должен',  # masculine
        'f': 'должна',  # feminine
        'n': 'должно'   # neutral
    }

    empty_noun_form = {
        'm': 'пустым',
        'f': 'пустой',
        'n': 'пустым'
    }

    # checking if the value is a string
    if not isinstance(value, str):
        return {'success': False, 'error': f'{field_name} {verb_form.get(gender, "должно")} быть строкой.'}

    # if required, checking if the string is non-empty
    if required and not value.strip():
        return {'success': False, 'error': f'{field_name} не {verb_form.get(gender, "должно")} быть '
                                           f'{empty_noun_form.get(gender, "пустым")}.'}

    return {'success': True, 'value': value.strip()}


def validate_decimal_string(value_str, field_name='Значение', min_value=0, max_value=None,
                            max_decimals=2, required=True, gender='n'): # TODO: type-constraints for min-max values?
    """
    Validates that a string represents a numeric value with specific constraints and gender-based error messages.

    :param value_str: the string to validate.
    :param field_name: the name of the field for error messages.
    :param min_value: minimum allowable value (inclusive).
    :param max_value: maximum allowable value (inclusive).
    :param max_decimals: maximum number of decimal places allowed.
    :param required: if True, the field must not be empty.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (Decimal).
    """

    if not isinstance(value_str, str):
        return {'success': False, 'error': 'Входное значение должно иметь формат str.'}

    # gender-specific words forms for Russian
    must_verb_form = {
        'm': 'должен',  # masculine
        'f': 'должна',  # feminine
        'n': 'должно'  # neutral
    }

    empty_noun_form = {
        'm': 'пустым',
        'f': 'пустой',
        'n': 'пустым'
    }

    equal_adjective_form = {
        'm': 'равным',
        'f': 'равной',
        'n': 'равным'
    }

    # checking if the value is required and empty
    if required and not value_str.strip():
        return {'success': False, 'error': f'{field_name} не {must_verb_form.get(gender, "должно")} быть '
                                           f'{empty_noun_form.get(gender, "пустым")}.'}

    try:
        # trying to convert the value to Decimal
        value = Decimal(value_str)

        # checking minimum value
        if min_value is not None and value < Decimal(str(min_value)):
            return {'success': False,
                    'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть больше или '
                             f'{equal_adjective_form.get(gender, "равным")} {min_value}.'}

        # checking maximum value
        if max_value is not None and value > Decimal(str(max_value)):
            return {'success': False,
                    'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть меньше или '
                             f'{equal_adjective_form.get(gender, "равным")} {max_value}.'}

        # checking decimal places
        if abs(value.as_tuple().exponent) > max_decimals:
            return {'success': False,
                    'error': f'{field_name} {must_verb_form.get(gender, "должно")} содержать '
                             f'не более {max_decimals} знаков после запятой.'}

        # validation passed
        return {'success': True, 'value': value}

    except (ValueError, InvalidOperation):
        # if value is not empty but cannot be converted to Decimal
        return {'success': False, 'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть числом.'}


def validate_int_string(value_str, field_name='Значение', min_value=0, max_value=None, required=True, gender='n'):
    """
    Validates that a string represents an integer value with specific constraints and gender-based error messages.

    :param value_str: the string to validate.
    :param field_name: the name of the field for error messages.
    :param min_value: minimum allowable value (inclusive).
    :param max_value: maximum allowable value (inclusive).
    :param required: if True, the field must not be empty.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (int).
    """
    if not isinstance(value_str, str):
        return {'success': False, 'error': 'Входное значение должно иметь формат str.'}

    # gender-specific words forms for Russian
    must_verb_form = {
        'm': 'должен',  # masculine
        'f': 'должна',  # feminine
        'n': 'должно'  # neutral
    }

    empty_noun_form = {
        'm': 'пустым',
        'f': 'пустой',
        'n': 'пустым'
    }

    equal_adjective_form = {
        'm': 'равным',
        'f': 'равной',
        'n': 'равным'
    }

    # checking if the value is required and empty
    if required and not value_str.strip():
        return {'success': False, 'error': f'{field_name} не {must_verb_form.get(gender, "должно")} быть '
                                           f'{empty_noun_form.get(gender, "пустым")}.'}

    try:
        # trying to convert value to an int
        value = int(value_str)

        # checking minimum value
        if min_value is not None and value < min_value:
            return {'success': False,
                    'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть больше или '
                             f'{equal_adjective_form.get(gender, "равным")} {min_value}.'}

        # checking maximum value
        if max_value is not None and value > max_value:
            return {'success': False,
                    'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть меньше или '
                             f'{equal_adjective_form.get(gender, "равным")} {max_value}.'}

        # validation passed
        return {'success': True, 'value': value}

    except ValueError:
        # if value is not empty but cannot be converted to int
        return {'success': False, 'error': f'{field_name} {must_verb_form.get(gender, "должно")} быть числом.'}


# specific wrappers with gender parameter
def validate_positive_integer_string(value_str, field_name='Значение', gender='n'):
    """
    Validates a positive integer with gender-specific messages.

    :param value_str: the string to validate.
    :param field_name: the name of the field for error messages.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (int).
    """
    return validate_int_string(value_str, field_name, min_value=1, gender=gender)


def validate_percentage_string(value_str, field_name='Процент', gender='m'):
    """
    Validates a percentage (0-100) with up to two decimal places and gender-specific messages.

    :param value_str: the string to validate.
    :param field_name: the name of the field for error messages.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (Decimal).
    """
    return validate_decimal_string(value_str, field_name, min_value=0, max_value=100, max_decimals=2, gender=gender)


def validate_non_negative_decimal_string(value_str, field_name='Значение', gender='n'):
    """
    Validates a non-negative Decimal with up to two decimal places and gender-specific messages.

    :param value_str: the string to validate.
    :param field_name: the name of the field for error messages.
    :param gender: grammatical gender for error messages ('m' - masculine, 'f' - feminine, 'n' - neutral).
    :return: a dictionary with 'success' (bool) and 'error' (str) or 'value' (Decimal).
    """
    return validate_decimal_string(value_str, field_name, min_value=0, max_decimals=2, gender=gender)
