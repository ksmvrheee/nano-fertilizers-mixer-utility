def filter_non_negative_decimal_input(e):
    """
    Event handler for a TextField control that removes all
    non-digits (except for the fractional separator) from the string being
    entered and ensures that a decimal part length is two digits long at max.
    """
    old_value = e.control.value
    new_value = []
    point_encountered = False
    decimal_part_length = 0

    for char in old_value:
        if char.isdigit():
            if not point_encountered:
                new_value.append(char)

            elif decimal_part_length < 2:
                decimal_part_length += 1
                new_value.append(char)

        elif char in ('.', ',') and not point_encountered:
            point_encountered = True
            new_value.append('.')

    e.control.value = ''.join(new_value)
    e.control.update()


def filter_non_negative_int_input(e):
    """
    Event handler for a TextField control that removes
    all non-digits from the string being entered.
    """
    old_value = e.control.value
    new_value = []

    for char in old_value:
        if char.isdigit():
            new_value.append(char)

    e.control.value = ''.join(new_value)
    e.control.update()
