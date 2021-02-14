"""
statmech: Pythonic Finite State Machine

See ``__description__`` below or (better) ``README.md`` file in ``__repository__`` for more info.
"""

__author__ = "Howard C Lovatt"
__copyright__ = "Howard C Lovatt, 2021 onwards."
__license__ = "MIT https://opensource.org/licenses/MIT."
__repository__ = "https://github.com/hlovatt/statmech"
__description__ = "Pythonic Finite State Machine with both action outputs (Mearly) and state outputs (Moore)"
__version__ = "0.0.5"  # Version set by https://github.com/hlovatt/tag2ver

import sys


class State:
    """
    A state with an optional ``ident`` and with ``actions``.
    """

    def __init__(self, ident=None):
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

    def __exit__(self, exc_type, exc_val, exc_tb):
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
        :param exc_val: the exception or ``None`` if no exception occurred.
        :param exc_tb: the stack trace for the exception or ``None`` if no exception occurred.
        :returns: if called *due* to an exception, indicates if the state machine is to continue in the
                  current state (true) or rethrow the exception (false).
        """
        return False

    def __repr__(self):
        """String representation in same form as the constructor."""
        return 'State(ident={})'.format(self.ident)


class StateWithValue(State):
    """
    A ``State`` which has an output value associated with the state
    (as opposed to associated with the action),
    an optional ``ident``, and ``actions``.

    The ``action`` (not to be confused with ``actions`` which has an 's') property is a convenient way of
    returning the action tuple of new state and new value.

    Some state machines are easier to code with states having values whilst others are easier to code with
    actions having values, hence this module supports both types of state machine.

    State machines that have states with values, as opposed to actions that have values, are termed Moore Machines:
    https://en.wikipedia.org/wiki/Moore_machine.
    """

    def __init__(self, *, ident=None, value):
        """
        Create a state that has an optional identifier and an optional value.

        :param ident: optional identifier for the state.
        :param value: value for the state.
        """
        super().__init__(ident=ident)
        self.value = value
        """The value of the state (defaults to ``None``)."""

    @property
    def action(self):
        """
        The action associated with transitioning to this state.

        :return: action tuple of ``(self, self.value)``.
        """
        return self, self.value

    def __repr__(self):
        """String representation in same form as the constructor."""
        return 'StateWithValue(ident={}, value={})'.format(self.ident, self.value)


# TODO Add warning option to constructor so that a change in the events set from one state to another warned and
#      a second warning option for if both machine and state have same event.
#      Needs an events property that returns super set of events in the machine and its state.
class Machine(State):
    """
    State machine itself, which is also a state so that machines can be nested.

    If ``__exit__`` is overridden in a derived class then
    must call ``super().__exit__(exc_type, exc_val, exc_tb)`` in a ``try`` block at start of new ``__exit__``
    to ensure that current state is correctly exited, e.g.:

    ```python
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            _ = super().__exit__(None, None, None)
        finally:
            <exit actions>
        return False
    ```

    """

    def __init__(self, *, ident=None, initial_state):
        """
        Create a state machine with an initial state and an optional identifier.

        :param ident: optional identifier for the machine.
        :param initial_state: initial state of the machine.
        :throws AssertionError: if initial state is ``None``.
        """
        assert initial_state is not None

        super().__init__(ident=ident)

        self._state = initial_state
        """The current state (private var)."""

        self._new_machine = True
        """True when machine is new and no events have fired as yet (private var)."""

    @property
    def state(self):
        """Current state."""
        return self._state

    def fire(self, event):
        """
        Fire the given event off and return the new value of the state machine.

        If it is the 1st firing on a new machine then the ``initial_state`` is entered before firing.

        The firing obtains the action tuple (new state, new value) associated with the event on the current state and
        if the new state in the tuple is different than the current state
        then exit the current state and enter the new state.

        :param event: event to fire off.
        :returns: the new value of the state machine.
        """
        # See https://docs.python.org/3/reference/compound_stmts.html#with for how ``with`` works.

        if self._new_machine:  # Enter the initial state of the newly created machine.
            self._new_machine = False
            enter = type(self._state).__enter__  # Check that ``__enter__`` and ``__exit__`` exist.
            _ = type(self._state).__exit__
            self._state = enter(self._state)

        current_state = self._state

        new_value = None
        # noinspection PyBroadException
        try:
            machine_actions = self.actions
            state_actions = current_state.actions
            new_state, new_value = state_actions[event] if event in state_actions.keys() else machine_actions[event]
        except BaseException as e:
            if sys.implementation.name == 'micropython':  # Micropython has reduced exception capability.
                if not current_state.__exit__(type(e), e, None):
                    self._state = None  # None indicates that __exit__ already called.
                    raise e
            else:
                if not current_state.__exit__(*sys.exc_info()):
                    self._state = None  # None indicates that __exit__ already called.
                    raise e
            new_state = current_state  # ``__exit__`` has dealt with the exception, therefore continue in current state.

        if new_state is not current_state:
            _ = current_state.__exit__(None, None, None)
            enter = type(new_state).__enter__  # Check that ``__enter__`` and ``__exit__`` exist.
            _ = type(new_state).__exit__
            self._state = enter(new_state)

        return new_value

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called on exit of the machine (exit for any reason including an exception).
        By default, exits the current state (if there is one) and returns false.

        If ``__exit__`` was called due to a *normal* exit (*not* due to an exception) then
        the returned value is ignored.

        If ``__exit__`` was called *due* to an exception then the returned bool indicates if
        the exception should be swallowed (true) or not (false).
        If ``__exit__`` has dealt with the exception, it should return true (swallow exception).
        Swallowing the exception means that the current state of the enclosing
        state machine does *not* change and that the state machine continues to operate.

        If ``__exit__`` is overridden in a derived class then
        must call ``super().__exit__(exc_type, exc_val, exc_tb)`` in a ``try`` block at start of new ``__exit__``
        to ensure that current state is correctly exited, e.g.:

        ```python
        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                _ = super().__exit__(None, None, None)
            finally:
                <exit actions>
            return False
        ```

        :param exc_type: the type of the exception or ``None`` if no exception occurred.
        :param exc_val: the exception or ``None`` if no exception occurred.
        :param exc_tb: the stack trace for the exception or ``None`` if no exception occurred.
        :returns: if called *due* to an exception, indicates if the enclosing state machine is to continue in the
                  current state (true) or rethrow the exception (false) or if enclosed by a ``with`` statement
                  if that statement is to swallow the exception (true) or rethrow the exception (false).
        """
        if self._state is not None and not self._new_machine:
            # If it is a new `machine that hasn't entered the initial state then don't exit initial state.
            # Since state is not ``None``, it is an exit from a ``with`` statement.
            _ = self._state.__exit__(None, None, None)
        return False

    def __repr__(self):
        """String representation in same form as the constructor, but using the current state for the initial state."""
        return 'Machine(initial_state={}, ident={})'.format(self.state, self.ident)


# TODO Make MachineWithValue inherit StateWithValue so that can be used as type or with instance of test.
class MachineWithValue(Machine):
    """The state machine itself, which is also a state so that machines can be nested and has an associated value."""

    def __init__(self, *, ident=None, initial_state, value=None):
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
        return 'MachineWithValue(ident={}, initial_state={}, value={})'.format(self.ident, self.state, self.value)


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
