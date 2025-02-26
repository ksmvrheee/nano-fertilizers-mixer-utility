from decimal import Decimal, ROUND_HALF_UP


def get_component_masses(n_percentage: Decimal, p_percentage: Decimal,
                         k_percentage: Decimal, total_mass: Decimal) -> dict:
    """
    Calculates the absolute mass of nitrogen, phosphorus and potassium
    according to their percentages and the mass (in grams) of the desired mixture.

    :param n_percentage: the percentage of nitrogen in the desired mixture.
    :param p_percentage: the percentage of phosphorus in the desired mixture.
    :param k_percentage: the percentage of potassium in the desired mixture.
    :param total_mass: the mass of the mix (in grams).
    :return: a dictionary with the keys being the elements (N, P, K)
        and the values being their approximate masses rounded to hundredths.
    :raises TypeError: if any input is not a Decimal isinstance.
    :raises ValueError: if percentages are out of range or total_mass is non-positive.
    """
    for name, value in {'n_percentage': n_percentage, 'p_percentage': p_percentage,
                        'k_percentage': k_percentage, 'total_mass': total_mass}.items():
        if not isinstance(value, Decimal):
            raise TypeError(f'{name} must be a Decimal instance, got {type(value).__name__}.')

    if not (0 <= n_percentage <= 100 and 0 <= p_percentage <= 100 and 0 <= k_percentage <= 100):
        raise ValueError('Percentages must be between 0 and 100.')

    if total_mass <= 0:
        raise ValueError('Total mass must be greater than zero.')

    n_mass = n_percentage / 100 * total_mass
    p_mass = p_percentage / 100 * total_mass
    k_mass = k_percentage / 100 * total_mass

    return {'N': n_mass.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'P': p_mass.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'K': k_mass.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}


def apply_nano_coefficients(component_masses: dict, *, n_coefficient: Decimal = Decimal('0.5'),
                            p_coefficient: Decimal = Decimal('0.2'), k_coefficient: Decimal = Decimal('0.4')) -> None:
    """
    Applies the nano digestibility coefficients to the values in the dictionary
    containing the masses of nitrogen, phosphorus and potassium. Modifies the
    given dictionary. Leaves the other dictionary keys and items as they are.

    :param component_masses: a dictionary containing the 'N', 'P', 'K' keys
        (representing the absolute masses of nitrogen, phosphorus and
        potassium) which values must be the Decimal instances.
    :param n_coefficient: nitrogen nano digestibility coefficient (default is 0.5).
    :param p_coefficient: phosphorus nano digestibility coefficient (default is 0.2).
    :param k_coefficient: potassium nano digestibility coefficient (default is 0.4).
    :raises TypeError: if any input is not of the expected type.
    :raises ValueError: if masses are non-positive or coefficients are out of range.
    """
    for element in ['N', 'P', 'K']:
        if element not in component_masses:
            raise ValueError(f'Missing required key "{element}" in component_masses.')

        if not isinstance(component_masses[element], Decimal):
            raise TypeError(
                f'Value for "{element}" must be a Decimal instance, got {type(component_masses[element]).__name__}.')

        if component_masses[element] < 0:
            raise ValueError(f'Mass for "{element}" must be non-negative.')

    for name, coefficient in {'n_coefficient': n_coefficient, 'p_coefficient': p_coefficient,
                              'k_coefficient': k_coefficient}.items():
        if not isinstance(coefficient, Decimal):
            raise TypeError(f'{name} must be a Decimal instance, got {type(coefficient).__name__}.')

        if not (0 <= coefficient <= 1):
            raise ValueError(f'{name} must be between 0 and 1.')

    component_masses['N'] = (component_masses['N'] * n_coefficient).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    component_masses['P'] = (component_masses['P'] * p_coefficient).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    component_masses['K'] = (component_masses['K'] * k_coefficient).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def truncate_string(string: str, target_length: int = 50) -> str:
    """
    Shortens the passed string so that there are 'target_length' characters
    left in it. Also truncates the trailing whitespace and adds an ellipsis.

    :param string: the string to truncate.
    :param target_length: a length of the returned string (excluding a trailing whitespace and an ellipsis).
    :return: a truncated string without a trailing whitespace and with an ellipsis at the end.
    :raises TypeError: if any input is not of the expected type.
    """
    if not isinstance(string, str):
        raise TypeError(f'String to truncate must be an str instance, got {type(string).__name__}.')

    if not isinstance(target_length, int):
        raise TypeError(f'A number of characters must be an int instance, got {type(target_length).__name__}.')

    if not len(string) > target_length:
        return string

    return string[:target_length].rstrip() + '...'
