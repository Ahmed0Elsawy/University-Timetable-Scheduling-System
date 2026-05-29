"""
scheduler/ga_hybrid.py
Genetic Algorithm wrapper around the CP-SAT solver.
"""

from __future__ import annotations

import random

from utils.helpers import safe_str
from scheduler.cp_solver import run_greedy_plus_cp


# ---------------------------------------------------------------------------
# Fitness
# ---------------------------------------------------------------------------

def fitness_score(schedule_df, summary_df) -> float:
    """Score a schedule: penalise shortfalls, reward coverage and compactness."""
    short = int(
        summary_df["Unassigned Lectures"].sum() + summary_df["Unassigned Labs"].sum()
    )
    score = -100_000 * short

    if schedule_df is None or schedule_df.empty:
        return score - 999_999

    score += 2_000 * len(schedule_df)

    p_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3, "P5": 4}
    for (_lvl, _day), g in schedule_df.groupby(["Level", "Day"]):
        idxs = sorted(p_order.get(str(p), 99) for p in g["Period"].tolist())
        if idxs:
            gaps = (max(idxs) - min(idxs) + 1) - len(set(idxs))
            score -= 30 * gaps

    if "Level" in schedule_df.columns and not schedule_df.empty:
        counts = schedule_df["Level"].fillna("").astype(str).value_counts()
        if len(counts) >= 2:
            total = float(counts.sum())
            shares = (counts / total).values
            mean = 1.0 / len(shares)
            var = sum((s - mean) ** 2 for s in shares) / len(shares)
            score -= 20_000 * var

    return float(score)


# ---------------------------------------------------------------------------
# GA operators
# ---------------------------------------------------------------------------

def _order_crossover(p1: list, p2: list) -> list:
    """Order crossover (OX) for permutation chromosomes."""
    n = len(p1)
    if n <= 2:
        return p1[:]
    a = random.randint(0, n - 2)
    b = random.randint(a + 1, n - 1)
    child: list = [None] * n
    child[a: b + 1] = p1[a: b + 1]
    fill = [x for x in p2 if x not in child]
    j = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[j]
            j += 1
    return child


def _mutate_swap(chromosome: list, rate: float = 0.3) -> list:
    """Swap-mutation: randomly swap two genes with probability *rate*."""
    q = chromosome[:]
    if len(q) >= 2 and random.random() < rate:
        i, j = random.sample(range(len(q)), 2)
        q[i], q[j] = q[j], q[i]
    return q


def _tournament_select(scored: list, k: int = 4):
    """Tournament selection: pick *k* random individuals, return best."""
    candidates = random.sample(scored, min(k, len(scored)))
    return max(candidates, key=lambda x: x[0])[1]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ga_hybrid_run(
    selected_courses: list[dict],
    course_students: dict,
    course_doctors: dict,
    course_assistants: dict,
    halls: list[dict],
    labs: list[dict],
    doctors: list[dict],
    assistants: list[dict],
    days: list[str],
    periods_ui: list[str],
    hall_capacity_override: int,
    lab_capacity_override: int,
    level_template_df=None,
    generations: int = 15,
    pop_size: int = 12,
    elite_k: int = 3,
    cp_timeout: int = 20,
):
    """
    Run a Genetic Algorithm that evolves course orderings and evaluates each
    via the CP-SAT solver.

    Returns
    -------
    schedule_df, summary_df, conflicts_df, status, best_fit
    """
    base_codes = [safe_str(c.get("course_code") or c.get("id")) for c in selected_courses]
    code_to_course = {safe_str(c.get("course_code") or c.get("id")): c for c in selected_courses}

    def eval_order(order_codes: list[str]):
        reordered = [code_to_course[c] for c in order_codes if c in code_to_course]
        sch, summ, conf, status = run_greedy_plus_cp(
            reordered, course_students, course_doctors, course_assistants,
            halls, labs, doctors, assistants,
            days, periods_ui, hall_capacity_override, lab_capacity_override,
            level_template_df=level_template_df,
            cp_timeout=cp_timeout,
        )
        return fitness_score(sch, summ), sch, summ, conf, status

    # Initialise population
    population = [base_codes[:]]
    for _ in range(max(0, pop_size - 1)):
        tmp = base_codes[:]
        random.shuffle(tmp)
        population.append(tmp)

    best_fit = -1e18
    best_pack = None

    for _gen in range(generations):
        scored = []
        for individual in population:
            fit, sch, summ, conf, status = eval_order(individual)
            scored.append((fit, individual, sch, summ, conf, status))
            if fit > best_fit:
                best_fit = fit
                best_pack = (sch, summ, conf, status)

        scored.sort(key=lambda x: x[0], reverse=True)

        # Elitism
        new_pop = [scored[i][1][:] for i in range(min(elite_k, len(scored)))]

        # Fill remainder via crossover + mutation
        while len(new_pop) < pop_size:
            p1 = _tournament_select(scored)
            p2 = _tournament_select(scored)
            child = _order_crossover(p1, p2)
            child = _mutate_swap(child, rate=0.35)
            new_pop.append(child)

        population = new_pop

    if best_pack is None:
        # Fallback: return last evaluated result
        best_pack = (scored[0][2], scored[0][3], scored[0][4], scored[0][5])

    return (*best_pack, best_fit)
