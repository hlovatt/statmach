"""Test code and examples for ``statmach``."""

import enum

import pytest

from statmach import State, Machine, StateWithValue
import statmach

__author__ = statmach.__author__
__copyright__ = statmach.__copyright__
__license__ = statmach.__license__
__repository__ = statmach.__repository__
__description__ = "Test code and examples for ``statmach``."
__version__ = "0.0.0"

# TODO Expand test to include inner state.
# TODO Check for faults at all levels.
# TODO Check that state event 'overrides' machine event.
# TODO Check that machine exit also exits current state.
# TODO Check that state acts like inner ``with``.
# noinspection PyTypeChecker
class TestSM:
    def test_minimal_sm_that_does_nothing(self):
        Events = enum.Enum('Events', 'MACHINE STATE')
        state0 = State()
        state0.actions[Events.STATE] = state0, None
        with Machine(initial_state=state0) as machine:
            machine.actions[Events.MACHINE] = state0, None

            assert machine.state is state0
            assert machine.fire(event=Events.MACHINE) is None
            assert machine.state is state0
            assert machine.fire(event=Events.STATE) is None
            assert machine.state is state0

    def test_edge_detector(self):
        """
        https://en.wikipedia.org/wiki/Mealy_machine

        .. image:: file:://media/EdgeDetectorStateDiagram.png
            :alt: Edge Detector State Diagram
            :width: 864px
            :height: 720px
        """

        Bit = enum.Enum('Bit', 'ZERO ONE')  # 1. & 2. Define the inputs (in this case also the outputs).

        s_i = State(ident='i')  # 3. Define the states.
        s_0 = State(ident=0)
        s_1 = State(ident=1)

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

    # noinspection PyArgumentList
    def test_traffic_lights(self):
        """
        .. image:: media/TrafficLightStateDiagram.png
        """

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

        flashing_red = StateWithValue(ident='flashing_red', value=Outputs.FLASHING_RED)  # 3. The states.
        red = StateWithValue(ident='red', value=Outputs.RED)
        amber = StateWithValue(ident='amber', value=Outputs.AMBER)
        green = StateWithValue(ident='green', value=Outputs.GREEN)

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

    # def test_nested_state_machines(self):
    #     Events: typing.Final = statmach.Event('Events', 'TO_OUTER_0 TO_OUTER_1 TO_INNER_0 TO_INNER_1')
    #     outer_0: typing.Final = statmach.State()
    #     outer_1: typing.Final = statmach.State()
    #     inner_0: typing.Final = statmach.State()
    #     inner_1: typing.Final = statmach.State()
    #     inner_machine: typing.Final = statmach.Machine(initial_state=inner_0)
    #     with statmach.Machine(initial_state=outer_0) as machine:
    #         machine.actions[Events.TO_OUTER_0] = lambda: outer_0
    #         outer_0.actions[Events.TO_OUTER_1] = lambda: outer_1
    #         outer_1.actions[Events.TO_OUTER_1] = lambda: outer_1
    #         inner_machine.actions[Events.TO_OUTER_0] = lambda: outer_0
    #         outer_0.actions[Events.TO_OUTER_1] = lambda: outer_1
    #         outer_1.actions[Events.TO_OUTER_1] = lambda: outer_1
    #
    #         assert machine.state is states[0]
    #         machine.fire(event=Events.MACHINE_TO_STATE_0)
    #         assert machine.state is states[0]
    #         machine.fire(event=Events.STATE_TO_STATE_1)
    #         assert machine.state is states[1]
    #         machine.fire(event=Events.STATE_TO_STATE_1)
    #         assert machine.state is states[1]
    #         machine.fire(event=Events.MACHINE_TO_STATE_0)
    #         assert machine.state is states[0]

    def test_transitioning_between_states_and_enter_and_exit_overrides(self):
        log = []

        Events = enum.Enum('Events', 'MACHINE_TO_STATE_0 STATE_TO_STATE_1')

        class LoggingState(State):

            def __enter__(self) -> 'LoggingState':
                log.append('Enter State {}'.format(self.ident))
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                log.append('Exit State {}'.format(self.ident))
                return False

        class LoggingMachine(Machine):

            def __enter__(self) -> 'LoggingMachine':
                log.append('Enter Machine')
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                log.append('Exit Machine')
                return False

        states = [LoggingState(ident=0), LoggingState(ident=1)]
        states[0].actions[Events.STATE_TO_STATE_1] = states[1], None
        states[1].actions[Events.STATE_TO_STATE_1] = states[1], None

        with LoggingMachine(initial_state=states[0]) as machine:
            machine.actions[Events.MACHINE_TO_STATE_0] = states[0], None

            assert machine.state is states[0]
            assert machine.fire(event=Events.MACHINE_TO_STATE_0) is None
            assert machine.state is states[0]
            assert machine.fire(event=Events.STATE_TO_STATE_1) is None
            assert machine.state is states[1]
            assert machine.fire(event=Events.STATE_TO_STATE_1) is None
            assert machine.state is states[1]
            assert machine.fire(event=Events.MACHINE_TO_STATE_0) is None
            assert machine.state is states[0]

        assert log == [
            'Enter State 0',
            'Enter Machine',
            'Exit State 0',
            'Enter State 1',
            'Exit State 1',
            'Enter State 0',
            'Exit Machine',
        ]

    def test_that_unhandled_event_gets_raised(self):
        Events = enum.Enum('Events', 'UNHANDLED')
        state0 = State()
        with Machine(initial_state=state0) as machine:
            assert machine.state is state0
            with pytest.raises(KeyError):
                machine.fire(event=Events.UNHANDLED)
            assert machine.state is state0

    def test_that_exception_can_be_suppressed(self):
        Events = enum.Enum('Events', 'UNHANDLED')

        class SuppressAllExceptions(State):
            def __exit__(self, exc_type, exc_val, exc_tb):
                return True  # Suppress the exception.

        state0 = SuppressAllExceptions()
        with Machine(initial_state=state0) as machine:
            assert machine.state is state0
            assert machine.fire(event=Events.UNHANDLED) is None
            assert machine.state is state0
