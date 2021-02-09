"""
Pythonic State Machine
======================

State machines represent different states and the transition between states that have a repetitive sequence
that is pre-determined.
Examples are many appliances (kettle, toaster, etc.),
machines in general (traffic lights, factory automation, etc.), and
stateful software (UI screens, wizards, etc.).
These are very broad categories of uses and therefore state machines are common.
A frequent characteristic of a state machine is that the input events arrive asynchronously and therefore adding
a formal structure is useful otherwise the code becomes difficult to understand, debug, and maintain.

You can 'roll-your-own' state machine; but using a pre-tested module, like this one,
is both easier and more reliable.
In particular, error handling is very tricky to get right.

At a top (most abstract) level state machines are easy to code, just:

  1. List the inputs (events).
     Actually a set of events because you can't have repeats.
     Also the set is finite, i.e. can't have an infinite number of inputs.
     In practice state machine's are only practical if the number of events is less than about 100.

  2. List the states.
     Again actually a set, no repeats.
     Again only practical up to a few 100.

  3. List the transitions from one state to the next in response to an event and at the same time give the new output.

The above requirements are often represented as a state diagram, which is great to document code.

Terminology Used in this Module
-------------------------------

  1. The overall state machine is a ``Machine``.
  2. The state machine has ``States``.
  3. Inputs to the machine are events, which are typically enum members.
  4. The response of a ``State`` to an event is an action, which is a tuple of the new state and the output value.
  5. Events are ``fired`` into the ``Machine`` and the actions give the new states and new outputs.

Making a State Machine
----------------------

The steps to make a state machine are:

  1. Define input events, typically using an enum or class with just class attributes.
  2. Define outputs,
     which is often an enum but could be as complicated as a function to execute to obtain a derived value.
  3. Define states (class ``State``).
  4. Define actions (tuples of new state and new value)
     to take when events fire (add actions to states and machine).
  5. Define a ``Machine`` using a ``with`` statement.
  6. Fire events into machine and obtain outputs.

E.g. an edge detector
(it detects when its input changes from 0 to 1 or vice versa and outputs a 1 if it does, otherwise a 0):

.. image:: media/EdgeDetectorStateDiagram.png
    :alt: Edge Detector State Diagram
    :width: 864px
    :height: 720px

.. code:: Python

    def edge_detector():

        Bit = enum.Enum('Bit', 'ZERO ONE')  # 1. & 2. Define the inputs (in this case also the outputs).

        s_i: typing.Final = State(ident='i')  # 3. Define the states.
        s_0: typing.Final = State(ident=0)
        s_1: typing.Final = State(ident=1)

        s_i.actions = {Bit.ZERO: (s_0, Bit.ZERO), Bit.ONE: (s_1, Bit.ZERO)}  # 4. Define the actions.
        s_0.actions = {Bit.ZERO: (s_0, Bit.ZERO), Bit.ONE: (s_1, Bit.ONE)}
        s_1.actions = {Bit.ZERO: (s_0, Bit.ONE), Bit.ONE: (s_1, Bit.ZERO)}

        with Machine(initial_state=s_i) as machine:  # 5. Define the machine.
            assert machine.state is s_i
            assert machine.fire(event=Bit.ZERO) is Bit.ZERO  # 6. Fire events and obtain outputs.
            assert machine.state is s_0
            assert machine.fire(event=Bit.ZERO) is Bit.ZERO
            assert machine.state is s_0
            assert machine.fire(event=Bit.ONE) is Bit.ONE
            assert machine.state is s_1
            assert machine.fire(event=Bit.ONE) is Bit.ZERO
            assert machine.state is s_1
            assert machine.fire(event=Bit.ZERO) is Bit.ONE
            assert machine.state is s_0

Note how the startup is dealt with, initially outputting a 0 for either input
This special start up condition is achieved using a
start up state that is not used again after the first event is fired.
This unique startup state is a common feature of state space machines.

The edge detector is an example of a state machine that has an output associated with each action,
these are called Mealy Machine (see below) and they use the class ``State`` to define their states.

A more complicated example is a traffic light machine.
This has two common requirements: the events arrive asynchronously and it is important (because it is safety critical)
that all events are dealt with even if they arrive unexpectedly.
For example if the traffic light is red and the amber timeout occurs, this is an error because the machine is waiting
for the red timeout not the amber.

.. image:: media/TrafficLightStateDiagram.png
    :alt: Traffic Light State Diagram
    :width: 1080px
    :height: 720px

Note in the diagram, upper left, how the unexpected events and the error event are dealt with for the whole machine,
rather than coding this requirement on all states individually.
These machine actions can be 'overridden' by a state; so for example when in the red state and
the red timer finished the next state is green, as expected (not an error).
The advantage of the machine dealing with common actions is that the actions of the state machine are much
easier to follow.

.. code:: Python

        class Timeouts(enum.Enum):  # 1. The inputs.
            RED_TIMEOUT = enum.auto()
            AMBER_TIMEOUT = enum.auto()
            GREEN_TIMEOUT = enum.auto()
            ERROR = enum.auto()

        class Outputs(enum.Enum):  # 2. The outputs.
            RED = enum.auto()
            AMBER = enum.auto()
            GREEN = enum.auto()
            FLASHING_RED = enum.auto()

        flashing_red: typing.Final = StateWithValue(ident='flashing_red', value=Outputs.FLASHING_RED)  # 3. The states.
        red: typing.Final = StateWithValue(ident='red', value=Outputs.RED)
        amber: typing.Final = StateWithValue(ident='amber', value=Outputs.AMBER)
        green: typing.Final = StateWithValue(ident='green', value=Outputs.GREEN)

        red.actions[Timeouts.RED_TIMEOUT] = green.action  # 4a. The *state* actions.
        green.actions[Timeouts.GREEN_TIMEOUT] = amber.action
        amber.actions[Timeouts.AMBER_TIMEOUT] = red.action

        with Machine(initial_state=red) as machine:  # 5. The machine.
            machine.actions[Timeouts.RED_TIMEOUT] = flashing_red.action  # 4b. The *machine* actions.
            machine.actions[Timeouts.AMBER_TIMEOUT] = flashing_red.action
            machine.actions[Timeouts.GREEN_TIMEOUT] = flashing_red.action
            machine.actions[Timeouts.ERROR] = flashing_red.action

            assert machine.state is red
            assert machine.fire(event=Timeouts.RED_TIMEOUT) is Outputs.GREEN  # 6. Fire events and obtain outputs.
            assert machine.state is green
            assert machine.fire(event=Timeouts.GREEN_TIMEOUT) is Outputs.AMBER
            assert machine.state is amber
            assert machine.fire(event=Timeouts.AMBER_TIMEOUT) is Outputs.RED
            assert machine.state is red
            assert machine.fire(event=Timeouts.AMBER_TIMEOUT) is Outputs.FLASHING_RED
            assert machine.state is flashing_red
            assert machine.fire(event=Timeouts.ERROR) is Outputs.FLASHING_RED
            assert machine.state is flashing_red

Note how the defining actions in this case are split between state actions, 4a, and machine actions, 4b,
which makes the code shorter, easier to maintain, and easier to debug.

The traffic light machine is an example of a state machine that has an output associated with each state,
these are called Moore Machine (see below) and they use the class ``StateWithValue`` to define their states.

For more examples see ``test_statmach.py``.

Pythonic Aspects of this Module
--------------------------------

  1. ``Machine`` is a ``State`` (inheritance), so that machines can be nested.
  2. ``State`` and hence ``Machine`` are context managers which allows for enter and exit code and error handling.
  3. Use Python ``with`` for executing a ``Machine``.
  4. Warnings (python ``warnings`` module) can optionally be issued if input events handled changes during execution.

Formal Definition
-----------------

The state machine implemented is a Mealy machine, see https://en.wikipedia.org/wiki/Mealy_machine,
but a Moore Machine, the other common type of state machine, can also be easily represented see ``StateWithValue``.
The formal definition of a Mealy machine is a 5-tuple (S, S0, Σ, Λ, T) that consisting of the following:

  * A finite set of states S.
    Class ``State`` represents a state.

  * A start state (also called initial state) S0 which is an element of S.
    When a ``Machine`` is created it must be given an initial state.

  * A finite set called the input alphabet Σ.
    Inputs are unique objects, typically members of an enum.

  * A finite set called the output alphabet Λ.
    The output is any type (generically typed).

  * A combined transition and output function T : S × Σ → S × Λ.
    The transitions are actions on each state that are called when the corresponding event fires,
    the actions give the new state and new output.

In the strictest sense the state machine implemented by this module is superset of a Mealy Machine because:

  1. The code does not enforce that there are a fixed set of: states (S), events (Σ), etc. and these sets can be
     added to or removed from whilst executing the machine.

  2. Both the machine and the state classes can be extended to add extra fields to them
     (thus giving extra state that is not part of the state machine 'per se').

  3. Has extensive error control via Python exceptions and handling in ``__exit__``.

  4. Has machine actions that can be 'overridden' by state actions.
"""

# TODO Document micropython

__author__ = "Howard C Lovatt"
__copyright__ = "Howard C Lovatt, 2021 onwards."
__license__ = "MIT https://opensource.org/licenses/MIT."
__version__ = "0.0.0"

import sys


class State:
    """
    A state.
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
        """String representation in same form as constructor."""
        return 'State(ident={})'.format(self.ident)


class StateWithValue(State):
    """
    Represents a state which has an output value associated with the state (as opposed to associated with the action).
    The ``action`` (not to be confused with ``actions`` which has an 's') property is a convenient way of
    returning the action tuple of new state and new value.

    Some state machines are easier to code with states having values whilst others are easier to code with
    actions having values, hence this module supports both types of state machine.

    State machines that have states with values, as opposed to actions that have values, are termed Moore Machine:
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
        """String representation in same form as constructor."""
        return 'StateWithValue(ident={}, value={})'.format(self.ident, self.value)


# TODO Add warning option to constructor so that a change in the events set from one state to another warned and
#      a second warning option for if both machine and state have same event.
#      Needs an events property that returns super set of events in the machine and its state.
class Machine(State):
    """The state machine itself, which is also a state so that machines can be nested."""

    def __init__(self, *, initial_state, ident=None):
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

    def fire(self, *, event):
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
        except:
            if not state.__exit__(*sys.exc_info()):
                raise
            new_state = state  # ``__exit__`` has dealt with the exception, therefore continue in current state.

        if new_state is not state:
            _ = state.__exit__(None, None, None)
            enter = type(new_state).__enter__  # Check that ``__enter__`` and ``__exit__`` exist.
            _ = type(new_state).__exit__
            self.state = enter(new_state)

        return new_value

    def __repr__(self):
        """String representation in same form as constructor, but using the current state for the initial state."""
        return 'Machine(initial_state={}, ident={})'.format(self.state, self.ident)


class MachineWithValue(Machine):
    """The state machine itself, which is also a state so that machines can be nested and has an associated value."""

    def __init__(self, *, initial_state, ident=None, value=None):
        """
        Creates a state machine with an initial state, an optional identifier, and optional value.

        :param initial_state: initial state of the machine.
        :param ident: optional identifier for the machine.
        :param value: optional value for the machine.
        """

        super().__init__(initial_state=initial_state, ident=ident)
        self.value = value
        """The value of the machine (defaults to ``None``)."""

    def __repr__(self):
        """String representation in same form as constructor, but using the current state for the initial state."""
        return 'MachineWithValue(initial_state={}, ident={}, value={})'.format(self.state, self.ident, self.value)


def _main():
    """
    Simple test of framework (useful for quick debugging).
    """
    class Events:
        MACHINE = 1
        STATE = 2
    state0 = State()
    state0.actions[Events.STATE] = state0, None
    with Machine(initial_state=state0) as machine:
        machine.actions[Events.MACHINE] = state0, None

        assert machine.state is state0
        assert machine.fire(event=Events.MACHINE) is None
        assert machine.state is state0
        assert machine.fire(event=Events.STATE) is None
        assert machine.state is state0


if __name__ == '__main__':
    _main()
