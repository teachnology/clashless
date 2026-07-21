from ortools.sat.python import cp_model
import pandas as pd

from clashless.exceptions import SchedulingError
from clashless.presentations import ROLE_COLUMNS


class Schedule:
    """Assigns each presentation a (day, session) slot such that no person is
    double-booked across roles at the same slot and no unavailability rule is
    violated. Rooms are unlimited: any number of presentations may share a slot
    provided they share no people. Feasibility only - no optimisation objective.

    Modelled as a CP-SAT constraint problem: one slot variable per presentation
    (domain restricted by unavailability), and an AllDifferent constraint per
    person over every presentation they're involved in (which subsumes "a
    moderator can't chair two rooms at once", since room = moderator identity).
    """

    def __init__(self, presentations, unavailability, session_times, n_days):
        self.presentations = presentations
        self.unavailability = unavailability
        self.session_times = session_times
        self.n_days = n_days

    def solve(self):
        data = self.presentations.data
        ids = list(data.index)
        n_sessions = self.session_times.n_sessions
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
                    f"presentation {presentation_id!r} has no available slot"
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

        solver = cp_model.CpSolver()
        status = solver.solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise SchedulingError(
                "no schedule satisfies every constraint for the given n_days"
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
