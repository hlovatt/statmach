"""
statmech: Pythonic Finite State Machine

See ``__description__`` below or (better) ``README.md`` file in ``__repository__`` for more info.
"""

# TODO Document micropython

__author__ = "Howard C Lovatt"
__copyright__ = "Howard C Lovatt, 2021 onwards."
__license__ = "MIT https://opensource.org/licenses/MIT."
__repository__ = "https://github.com/hlovatt/statmech"
__description__ = "Pythonic Finite State Machine with both action outputs (Mearly) and state outputs (Moore)"
__version__ = "0.0.3"  # Version set by https://github.com/hlovatt/tag2ver

import sys


class State:
    """
    A state with an optional ``ident`` and with ``actions``.
    """

    def __init__(self, *, ident=None):
        """
        Creates a state that has an optional identifier.

        :param ident: optional identifier for the state.
        """

        self.ident = ident
        """Identifier of state (defaults to ``None``)."""

        self.actions = {}
        """
        The action associated with each event.
        An empty actions dictionary is created when a state is created; 
        so that actions can be added without checking that the dictionary exists.
        """

    def __enter__(self):
        """
        Called on entry to the state.
        By default, does nothing and returns ``self``.

        :returns: a newly initialized state, typically ``self``.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Called on exit of the state (exit for any reason including an exception).
        By default, does nothing and returns false.

        If ``__exit__`` was called due to a *normal* exit (*not* due to an exception) then
        the returned value is ignored.

        If ``__exit__`` was called *due* to an exception then the returned bool indicates if
        the exception should be swallowed (true) or not (false).
        If ``__exit__`` has dealt with the exception, it should return true (swallow exception).
        Swallowing the exception means that the current state of the
        state machine does *not* change and that the state machine continues to operate.

        :param exc_type: the type of the exception or ``None`` if no exception occurred.
        :param exc_value: the exception or ``None`` if no exception occurred.
        :param traceback: the stack trace for the exception or ``None`` if no exception occurred.
        :returns: if called *due* to an exception, indicates if the state machine is to continue in the
                  current state (true) or rethrow the exception (false).
        """
        return False

    def __repr__(self):
        """String representation in same form as the constructor."""
        return 'State(ident={})'.format(self.ident)


class StateWithValue(State):
    """
    Represents a ``State`` which has an output value associated with the state
    (as opposed to associated with the action),
    an optional ``ident``, and ``actions``.

    The ``action`` (not to be confused with ``actions`` which has an 's') property is a convenient way of
    returning the action tuple of new state and new value.

    Some state machines are easier to code with states having values whilst others are easier to code with
    actions having values, hence this module supports both types of state machine.

    State machines that have states with values, as opposed to actions that have values, are termed Moore Machines:
    https://en.wikipedia.org/wiki/Moore_machine.
    """

    def __init__(self, *, ident=None, value=None):
        """
        Creates a state that has an optional identifier and an optional value.

        :param ident: optional identifier for the state.
        :param value: optional value for the state.
        """
        super().__init__(ident=ident)
        self.value = value
        """The value of the state (defaults to ``None``)."""

    @property
    def action(self):
        """
        The action associated with transitioning to this state.

        :return: the action tuple of ``(self, self.value)``.
        """
        return self, self.value

    def __repr__(self):
        """String representation in same form as the constructor."""
        return 'StateWithValue(ident={}, value={})'.format(self.ident, self.value)


# TODO Add warning option to constructor so that a change in the events set from one state to another warned and
#      a second warning option for if both machine and state have same event.
#      Needs an events property that returns super set of events in the machine and its state.
class Machine(State):
    """The state machine itself, which is also a state so that machines can be nested."""

    def __init__(self, *, ident=None, initial_state):
        """
        Creates a state machine with an initial state and an optional identifier.

        :param initial_state: initial state of the machine.
        :param ident: optional identifier for the machine.
        """

        super().__init__(ident=ident)

        # See https://docs.python.org/3/reference/compound_stmts.html#with for how `with` works.
        enter = type(initial_state).__enter__  # Check that ``__enter__`` and ``__exit__`` exist.
        _ = type(initial_state).__exit__
        self.state = enter(initial_state)
        """The current state."""

    def fire(self, event):
        """
        Fire the given event off and return the new value of the state machine.

        Obtains the action tuple associated with the event on the current state and
        if the new state in the tuple is different than the current state
        then exit the current state and enter the new state.

        :param event: event to fire off.
        :returns: the new value of the state machine.
        """
        # See https://docs.python.org/3/reference/compound_stmts.html#with for how ``with`` works.
        state = self.state
        new_value = None
        # noinspection PyBroadException
        try:
            machine_actions = self.actions
            state_actions = state.actions
            new_state, new_value = state_actions[event] if event in state_actions.keys() else machine_actions[event]
        except BaseException as e:
            if sys.implementation.name == 'micropython':  # Micropython has reduced exception capability.
                if not state.__exit__(None, e, None):
                    raise e
            else:
                if not state.__exit__(*sys.exc_info()):
                    raise e
            new_state = state  # ``__exit__`` has dealt with the exception, therefore continue in current state.

        if new_state is not state:
            _ = state.__exit__(None, None, None)
            enter = type(new_state).__enter__  # Check that ``__enter__`` and ``__exit__`` exist.
            _ = type(new_state).__exit__
            self.state = enter(new_state)

        return new_value

    def __repr__(self):
        """String representation in same form as the constructor, but using the current state for the initial state."""
        return 'Machine(initial_state={}, ident={})'.format(self.state, self.ident)


class MachineWithValue(Machine):
    """The state machine itself, which is also a state so that machines can be nested and has an associated value."""

    def __init__(self, ident=None, *, initial_state, value=None):
        """
        Creates a state machine with an initial state, an optional identifier, and optional value.

        :param initial_state: initial state of the machine.
        :param ident: optional identifier for the machine.
        :param value: optional value for the machine.
        """

        super().__init__(ident=ident, initial_state=initial_state)
        self.value = value
        """The value of the machine (defaults to ``None``)."""

    def __repr__(self):
        """String representation in same form as the constructor, but using the current state for the initial state."""
        return 'MachineWithValue(initial_state={}, ident={}, value={})'.format(self.state, self.ident, self.value)


def _main():
    """Simple test of framework (useful for quick debugging)."""
    class Events:
        MACHINE = 1
        STATE = 2
    s0 = State()
    s0.actions[Events.STATE] = s0, None
    with Machine(initial_state=s0) as machine:
        machine.actions[Events.MACHINE] = s0, None

        assert machine.state is s0
        assert machine.fire(Events.MACHINE) is None
        assert machine.state is s0
        assert machine.fire(Events.STATE) is None
        assert machine.state is s0


if __name__ == '__main__':
    _main()
