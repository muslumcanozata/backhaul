from ortools.linear_solver import pywraplp


def best_pairs(benefits: dict[tuple[str, str], int]) -> list[tuple[str, str]]:
    if not benefits:
        return []
    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        raise RuntimeError("Eşleştirme çözücüsü yok")
    chosen: dict[tuple[str, str], pywraplp.Variable] = {}
    for index, pair in enumerate(benefits):
        chosen[pair] = solver.BoolVar(f"p{index}")
    loads = {load_id for load_id, _ in benefits}
    vehicles = {vehicle_id for _, vehicle_id in benefits}
    for load_id in loads:
        solver.Add(sum(var for (item, _), var in chosen.items() if item == load_id) <= 1)
    for vehicle_id in vehicles:
        solver.Add(sum(var for (_, item), var in chosen.items() if item == vehicle_id) <= 1)
    solver.Maximize(sum(benefits[pair] * var for pair, var in chosen.items()))
    status = solver.Solve()
    if status not in {pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE}:
        return []
    return [pair for pair, var in chosen.items() if var.solution_value() > 0.5]
