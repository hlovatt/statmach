"""
statmech: Pythonic Finite State Machine

See ``__description__`` below or (better) ``README.md`` file in ``__repository__`` for more info.
"""

__author__ = "Howard C Lovatt"
__copyright__ = "Howard C Lovatt, 2021 onwards."
__license__ = "MIT https://opensource.org/licenses/MIT."
__repository__ = "https://github.com/hlovatt/statmech"
__description__ = "Pythonic Finite State Machine with both action outputs (Mearly) and state outputs (Moore)"
__version__ = "1.0.1"  # Version set by https://github.com/hlovatt/tag2ver

import sys


class State:
    """
    A state with an optional ``ident``, optional ``value``, and with actions.
    Actions are an event entry in the ``actions`` dictionary of a tuple of new state and new value.
    ``Machine``'s ``fire`` method changes the machine state to the new state and return the new value.

    A Mearly Machine has the new value associated with each action,
    whereas a Moore Machine has the new value associated with each state.
    Some state machines are easier to code with states having values whilst others are easier to code with
    actions having values, hence ``State`` supports both types of state machine.

    For a Moore Machine the ``action`` property (not ``actions`` dictionary - note 's') is a convenient way of
    returning the action tuple of new state (``self``) and new value (``self.value``).
    """

    def __init__(self, ident=None, value=None):
        """
        Creates a state that has an optional identifier and optional value.

        :param ident: optional identifier for the state (defaults to ``None``).
        :param value: optional value for the state (defaults to ``None``).
        """

        self.ident = ident
        """State's identifier (defaults to ``None``)."""

        self.value = value
        """State's value (defaults to ``None``)."""

        self.actions = {}
        """
        The action associated with each event.
        An empty actions dictionary is created when a state is created; 
        so that actions can be added without checking that the dictionary exists.
        """

    @property
    def action(self):
        """
        The action associated with transitioning to this state.

        :return: action tuple of ``(self, self.value)``.
        """
        return self, self.value

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
                  current state (true) or re-raise the exception (false).
        """
        return False

    def __repr__(self):
        """String representation in same form as the constructor."""
        return 'State(ident={}, value={})'.format(repr(self.ident), repr(self.value))


class Machine:
    """
    The finite state machine itself, which can optionally have actions for the whole of the machine.
    If an event is in the current state's ``actions`` dictionary then this action takes precedence over the same event
    in the machine's dictionary.

    ``Machine`` is intended for use inside a ``with`` statement.

    If ``Machine``'s ``__exit__`` is overridden in a derived class then
    must call ``super().__exit__(exc_type, exc_val, exc_tb)`` in a ``try`` block at start of new ``__exit__``
    to ensure that current state is correctly exited, e.g.:

    ```python
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            _ = super().__exit__(None, None, None)  # Exception from super `__exit__` is propagated (do not catch).
        finally:
            <exit actions>
        return False
    ```
    """

    def __init__(self, *, initial_state):
        """
        Create a state machine with an initial state, an optional identifier, and optional value.

        :param initial_state: initial state of the machine.
        :raises AssertionError: if initial state is ``None``.
        """

        assert initial_state is not None, 'Initial state cannot be `None`.'

        self._state = initial_state
        """The current state (private var, read using property ``state``)."""

        self._new_machine = True
        """True when machine is new and no events have fired as yet (private var)."""

        self.actions = {}
        """
        The action associated with each event that this machine can respond to on behalf of all states.
        An empty actions dictionary is created when a machine is created; 
        so that actions can be added without checking that the dictionary exists.
        """

    @property
    def state(self):
        """Current state."""
        return self._state

    @property
    def events(self):
        """The set of events the machine or its current state can handle."""
        return set(self.actions.keys()).union(self._state.actions.keys())

    # Doesn't use keyword argument, unlike other methods, because Micropython's `schedule` can't use keywords.
    def fire(self, event):
        """
        Fire the given event off and return the new value of the state machine.

        If it is the 1st firing on a new machine then the ``initial_state`` is entered before firing.

        The firing obtains the action tuple (new state, new value) associated with the event on the current state and
        if the new state in the tuple is different than the current state
        then exit the current state and enter the new state.

        :param event: event to fire off.
        :returns: the new value of the state machine.
        :raises AssertionError: if ``initial_state``'s ``__enter__`` returns ``None`` or not a ``State``
                                or new state is ``None``
                                or not a ``State``
                                or if the set of events handled changes as a result of a state change.
        :raises Exception: if initial state's or new state's ``__entry__`` raises or if old state's ``__exit__`` raises.
        """
        # See https://docs.python.org/3/reference/compound_stmts.html#with for how ``with`` works.

        if self._new_machine:  # Enter the initial state of the newly created machine.
            self._new_machine = False
            new_state = self._state.__enter__()
            assert isinstance(new_state, State), \
                "Object, {}, returned by `initial_state`'s, {}, `__enter__` is not a `State`.".format(
                    new_state,
                    self._state,
                )
            self._state = new_state

        current_events = self.events
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
            assert new_state is not None, 'New state cannot be `None`.'

            _ = current_state.__exit__(None, None, None)
            self._state = new_state.__enter__()

            assert self._state is not None, "New state's `__enter__`  cannot return `None`."
            assert isinstance(self._state, State), "New state's `__enter__`  must return a `State`."

            new_events = self.events
            assert new_events == current_events, \
                "Set of current events handled, {}, not the same as set of new events, {}".format(
                    current_events,
                    new_events,
                )

        return new_value

    def __enter__(self):
        """
        Called on entry to the state.
        By default, does nothing and returns ``self``.

        :returns: a newly initialized state, typically ``self``.
        """
        return self

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
        state machine does *not* change and that the state machine continues to operate and the new value is ``None``.

        If ``__exit__`` is overridden in a derived class then
        must call ``super().__exit__(exc_type, exc_val, exc_tb)`` in a ``try`` block at start of new ``__exit__``
        to ensure that current state is correctly exited, e.g.:

        ```python
        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                _ = super().__exit__(None, None, None)  # Exception from super `__exit__` is propagated (do not catch).
            finally:
                <exit actions>
            return False
        ```

        :param exc_type: the type of the exception or ``None`` if no exception occurred.
        :param exc_val: the exception or ``None`` if no exception occurred.
        :param exc_tb: the stack trace for the exception or ``None`` if no exception occurred.
        :returns: if called *due* to an exception, indicates if the enclosing state machine is to continue in the
                  current state (true) or re-raise the exception (false) or if enclosed by a ``with`` statement
                  if that statement is to swallow the exception (true) or re-raise the exception (false).
        """
        if self._state is not None and not self._new_machine:
            # If it is a new `machine that hasn't entered the initial state then don't exit initial state.
            # Since state is not ``None``, it is an exit from a ``with`` statement.
            _ = self._state.__exit__(None, None, None)
        return False

    def __repr__(self):
        """String representation in same form as the constructor, but using the current state for the initial state."""
        return 'Machine(initial_state={})'.format(repr(self.state))


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
