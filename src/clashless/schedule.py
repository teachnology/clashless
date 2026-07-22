import pandas as pd
from ortools.sat.python import cp_model

from clashless.exceptions import SchedulingError
from clashless.presentations import ROLE_COLUMNS

# Best-effort time budget: once the objective turns solve() into a genuine
# optimisation instead of "stop at the first feasible solution," proving
# optimality on a large input could take arbitrarily long. All hard constraints
# still apply regardless of the time limit - only how well-grouped an otherwise
# valid schedule is may fall short of proven-optimal.
DEFAULT_MAX_SOLVE_SECONDS = 30.0


class Schedule:
    """Assign each presentation a (day, session) slot with no clashes.

    No person is double-booked across roles at the same slot and no
    unavailability rule is violated. Rooms are unlimited: any number of
    presentations may share a slot provided they share no people.

    Modelled as a CP-SAT constraint problem: one slot variable per presentation
    (domain restricted by unavailability), and an AllDifferent constraint per
    person over every presentation they're involved in (which subsumes "a
    chair can't chair two rooms at once", since room = chair identity). On top
    of that hard-constraint model, solve() searches (best-effort, within a
    time limit) for a schedule that minimizes, per person: first the number of
    distinct days they're needed on, then - as a tiebreaker - how spread out
    their sessions are on the days they are needed, so a few presentations
    land back-to-back rather than scattered with gaps.

    optimize_grouping=False skips building that objective entirely (not just
    ignoring it), reverting to the old "stop at the first feasible schedule"
    behaviour - a genuine speed win on large inputs, not just a smaller model.
    active_day_weight/spread_weight let you re-balance the two terms (default
    active_day_weight is n_days * n_sessions, chosen so it always dominates any
    possible change in total spread; see _add_grouping_objective).
    max_solve_seconds is the best-effort time budget passed straight to CP-SAT.
    """

    def __init__(
        self,
        presentations,
        unavailability,
        session_times,
        n_days,
        optimize_grouping=True,
        active_day_weight=None,
        spread_weight=1,
        max_solve_seconds=DEFAULT_MAX_SOLVE_SECONDS,
    ):
        self.presentations = presentations
        self.unavailability = unavailability
        self.session_times = session_times
        self.n_days = n_days
        self.optimize_grouping = optimize_grouping
        self.active_day_weight = (
            active_day_weight
            if active_day_weight is not None
            else n_days * len(session_times)
        )
        self.spread_weight = spread_weight
        self.max_solve_seconds = max_solve_seconds

    def solve(self):
        """Solve for a schedule and return the resulting day/session DataFrame."""
        data = self.presentations.data
        ids = list(data.index)
        n_sessions = len(self.session_times)
        n_slots = self.n_days * n_sessions

        def day_session(index):
            return index // n_sessions + 1, index % n_sessions + 1

        people = {
            presentation_id: set(data.loc[presentation_id, ROLE_COLUMNS])
            for presentation_id in ids
        }

        model = cp_model.CpModel()
        slot_vars = {}
        for presentation_id in ids:
            allowed = [
                index
                for index in range(n_slots)
                if not any(
                    self.unavailability.is_unavailable(person, *day_session(index))
                    for person in people[presentation_id]
                )
            ]
            if not allowed:
                raise SchedulingError(
                    f"Presentation {presentation_id!r} has no available slot."
                )
            slot_vars[presentation_id] = model.new_int_var_from_domain(
                cp_model.Domain.FromValues(allowed), f"slot_{presentation_id}"
            )

        ids_by_person = {}
        for presentation_id in ids:
            for person in people[presentation_id]:
                ids_by_person.setdefault(person, []).append(presentation_id)
        for sharing_ids in ids_by_person.values():
            if len(sharing_ids) > 1:
                model.add_all_different(slot_vars[i] for i in sharing_ids)

        if self.optimize_grouping:
            warm_start = self._solve_for_warm_start(model, slot_vars)
            self._add_grouping_objective(model, slot_vars, data, n_sessions, warm_start)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_solve_seconds
        status = solver.solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulingError(
                "No schedule satisfies every constraint for the given n_days."
            )

        days, sessions = [], []
        for presentation_id in ids:
            day, session = day_session(solver.value(slot_vars[presentation_id]))
            days.append(day)
            sessions.append(session)

        return pd.DataFrame(
            {"day": days, "session": sessions},
            index=pd.Index(ids, name=data.index.name),
        )

    def _solve_for_warm_start(self, model, slot_vars):
        # The grouping objective's auxiliary variables make the model large enough
        # that, on a big input, CP-SAT can spend most of the time budget just
        # reaching feasibility - sometimes never catching up to how good a plain
        # feasibility-only solve already is. Solving the hard constraints alone
        # first (fast: no objective to search for) gives every later variable a
        # known-consistent value to hint from, so the objective search can only
        # improve on this solution, never land somewhere worse.
        warm_start_solver = cp_model.CpSolver()
        warm_start_solver.parameters.max_time_in_seconds = self.max_solve_seconds
        status = warm_start_solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulingError(
                "No schedule satisfies every constraint for the given n_days."
            )
        return {
            presentation_id: warm_start_solver.value(slot_var)
            for presentation_id, slot_var in slot_vars.items()
        }

    def _add_grouping_objective(self, model, slot_vars, data, n_sessions, warm_start):
        for presentation_id, slot_var in slot_vars.items():
            model.add_hint(slot_var, warm_start[presentation_id])

        # Every role is groupable: none of the four columns is guaranteed to
        # appear at most once per person (the roles are fully symmetric), so
        # grouping applies to whoever shows up in any of them.
        ids_by_groupable_person = {}
        for presentation_id in data.index:
            for person in set(data.loc[presentation_id, ROLE_COLUMNS]):
                ids_by_groupable_person.setdefault(person, []).append(presentation_id)

        # A hint given only for slot_vars relies on CP-SAT successfully completing
        # the rest via propagation, which isn't always reliable for a web of
        # division/modulo/reified constraints this size - so every derived
        # variable below gets its consistent value computed directly in Python
        # and hinted explicitly, for a fully-specified, unambiguous incumbent.
        warm_start_day = {pid: value // n_sessions for pid, value in warm_start.items()}
        warm_start_session = {
            pid: value % n_sessions for pid, value in warm_start.items()
        }

        day_of = {}
        session_of = {}
        for presentation_id, slot_var in slot_vars.items():
            day_var = model.new_int_var(0, self.n_days - 1, f"day_{presentation_id}")
            session_var = model.new_int_var(
                0, n_sessions - 1, f"sess_{presentation_id}"
            )
            model.add_division_equality(day_var, slot_var, n_sessions)
            model.add_modulo_equality(session_var, slot_var, n_sessions)
            model.add_hint(day_var, warm_start_day[presentation_id])
            model.add_hint(session_var, warm_start_session[presentation_id])
            day_of[presentation_id] = day_var
            session_of[presentation_id] = session_var

        on_day = {}
        for presentation_id, day_var in day_of.items():
            for day in range(self.n_days):
                is_on_day = model.new_bool_var(f"on_day_{presentation_id}_{day}")
                model.add(day_var == day).only_enforce_if(is_on_day)
                model.add(day_var != day).only_enforce_if(is_on_day.Not())
                model.add_hint(is_on_day, int(warm_start_day[presentation_id] == day))
                on_day[presentation_id, day] = is_on_day

        active_terms = []
        spread_terms = []
        for person, presentation_ids in ids_by_groupable_person.items():
            for day in range(self.n_days):
                on_day_vars = [on_day[pid, day] for pid in presentation_ids]
                sessions_that_day = [
                    warm_start_session[pid]
                    for pid in presentation_ids
                    if warm_start_day[pid] == day
                ]

                active = model.new_bool_var(f"active_{person}_{day}")
                model.add_max_equality(active, on_day_vars)
                model.add_hint(active, int(bool(sessions_that_day)))
                active_terms.append(active)

                min_session = model.new_int_var(0, n_sessions - 1, "min_session")
                max_session = model.new_int_var(0, n_sessions - 1, "max_session")
                for pid in presentation_ids:
                    model.add(min_session <= session_of[pid]).only_enforce_if(
                        on_day[pid, day]
                    )
                    model.add(max_session >= session_of[pid]).only_enforce_if(
                        on_day[pid, day]
                    )
                model.add(min_session == 0).only_enforce_if(active.Not())
                model.add(max_session == 0).only_enforce_if(active.Not())
                model.add_hint(min_session, min(sessions_that_day, default=0))
                model.add_hint(max_session, max(sessions_that_day, default=0))
                spread_terms.append(max_session - min_session)

        # Weighted so that, by default, reducing the total active-day count by
        # even one always dominates any possible change in total spread (each
        # spread term is bounded by n_sessions - 1) - i.e. active days first,
        # spread as a tiebreaker, via a single weighted objective. Callers can
        # override active_day_weight/spread_weight to change that balance.
        model.minimize(
            self.active_day_weight * sum(active_terms)
            + self.spread_weight * sum(spread_terms)
        )
