from decimal import Decimal

import pulp

from database import FertilizingMixture


def calculate_best_mixture(nitrogen: int | float | Decimal, phosphorus: int | float | Decimal,
                           potassium: int | float | Decimal, total_mass: int | float | Decimal) -> dict:
    """
    Calculates the optimal fertilizing mixture based on the given N, P, and K mass requirements.
    Uses linear programming to find the most cost-effective combination of available fertilizers.

    :param nitrogen: required mass of nitrogen in grams.
    :param phosphorus: required mass of phosphorus in grams.
    :param potassium: required mass of potassium in grams.
    :param total_mass: total mass of the final mixture in grams.
    :return: a dictionary containing:
        - 'success' (bool): whether the optimization was successful.
        - 'mixture' (list[dict]): details of the selected ingredients.
        - 'total_cost' (float): total cost of the optimized mixture.
        - 'actual_composition' (dict): actual achieved N, P, and K mass in grams.
        - 'error' (str, optional): error message if unsuccessful.
    :raises TypeError: if any input is not an int, float or Decimal instance.
    """
    args = locals()
    for name, value in args.items():
        if not isinstance(value, float):
            if not isinstance(value, (int, Decimal)):
                raise TypeError(f'{name} must be an int, float or Decimal instance, got {type(value).__name__}.')

            args[name] = float(value)

    nitrogen, phosphorus, potassium = args['nitrogen'], args['phosphorus'], args['potassium']
    total_mass = args['total_mass']

    if total_mass <= 0:
        return {
            'success': False,
            'error': 'Ошибка: масса должна быть больше нуля.'
        }

    desired_composition = {'N': nitrogen, 'P': phosphorus, 'K': potassium}

    # loading available fertilizing mixtures from the database
    ingredients = []
    for mixture in FertilizingMixture.select().order_by(FertilizingMixture.name):
        ingredients.append({
            'name': mixture.name,
            'composition': {
                'N': float(mixture.nitrogen_percentage),
                'P': float(mixture.phosphorus_percentage),
                'K': float(mixture.potassium_percentage)
            },
            'price': float(mixture.price_per_gram)
        })

    step = 0.05  # unit step for ingredient quantities

    # defining the linear programming problem (minimizing cost)
    problem = pulp.LpProblem('FertilizerMixOptimization', pulp.LpMinimize)

    # defining variables for each ingredient
    ingredient_vars = {
        ingredient['name']: pulp.LpVariable(f'x_{ingredient["name"]}', lowBound=0, cat='Integer')
        for ingredient in ingredients
    }

    # objective function: minimize total cost
    problem += pulp.lpSum([ingredient_vars[ingredient['name']] * ingredient['price'] * step
                           for ingredient in ingredients])

    # constraints to ensure the required composition is met
    for primitive, required_amount in desired_composition.items():
        problem += pulp.lpSum(
            [ingredient_vars[ingredient['name']] * ingredient['composition'].get(primitive, 0) * step * total_mass / 100
             for ingredient in ingredients]
        ) >= required_amount

        problem += pulp.lpSum(
            [ingredient_vars[ingredient['name']] * ingredient['composition'].get(primitive, 0) * step * total_mass / 100
             for ingredient in ingredients]
        ) <= required_amount + 0.5

    problem.solve(pulp.apis.PULP_CBC_CMD(msg=False))  # solving the problem

    if pulp.LpStatus[problem.status] != 'Optimal':
        return {
            'success': False,
            'error': 'Ошибка: не удалось подобрать нужный состав.'
        }

    total_cost = 0
    mixture_info = []
    actual_composition = {'N': 0, 'P': 0, 'K': 0}

    # processing the solution
    for ingredient in ingredients:
        amount_in_mixture = ingredient_vars[ingredient['name']].varValue * step
        absolute_mass = amount_in_mixture * total_mass
        cost = round(ingredient['price'] * absolute_mass, 2)

        if amount_in_mixture:
            mixture_info.append({
                'name': ingredient['name'],
                'mass_in_grams': round(absolute_mass, 2),
                'cost': cost
            })
            total_cost += cost

            for primitive in actual_composition:
                actual_composition[primitive] += absolute_mass * ingredient['composition'][primitive] / 100

    return {
        'success': True,
        'mixture': mixture_info,
        'total_cost': round(total_cost, 2),
        'actual_composition': {key: round(value, 2) for key, value in actual_composition.items()}
    }
