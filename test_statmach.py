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
__version__ = "0.0.4"  # Version set by https://github.com/hlovatt/tag2ver

log = []


class LoggingState(State):
    def __init__(self, *, ident, enter_throws=False, exit_throws=False):
        super().__init__(ident=ident)
        self.enter_throws = enter_throws
        self.exit_throws = exit_throws

    def __enter__(self):
        log.append(f'Enter state {self.ident}')
        if self.enter_throws:
            assert False, f'Enter state {self.ident} throw'
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.append(f'Exit state {self.ident}')
        if self.exit_throws:
            assert False, f'Exit state {self.ident} throw'
        return False


class LoggingMachine(Machine):
    def __init__(self, *, initial_state, enter_throws=False, exit_throws=False):
        super().__init__(initial_state=initial_state)
        self.enter_throws = enter_throws
        self.exit_throws = exit_throws

    def __enter__(self):
        log.append(f'Enter machine')
        if self.enter_throws:
            assert False, f'Enter machine throw'
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            _ = super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            log.append(f'Exit machine')
            if self.exit_throws:
                assert False, f'Exit machine throw'
        return False


# TODO Expand test to include machine as a state.
# TODO Can uPython code terminate on ^C? Is this a good idea or is it better to allow code to continue to run.
# noinspection PyTypeChecker
class TestSM:
    # noinspection PyMethodMayBeStatic
    def setup_method(self):
        global log
        log.clear()

    def test_minimal_sm_that_does_nothing(self):
        Events = enum.Enum('Events', 'MACHINE STATE')
        s0 = State()
        s0.actions[Events.STATE] = s0, None
        with Machine(initial_state=s0) as machine:
            machine.actions[Events.MACHINE] = s0, None

            assert machine.state is s0
            assert machine.fire(Events.MACHINE) is None
            assert machine.state is s0
            assert machine.fire(Events.STATE) is None
            assert machine.state is s0

    def test_edge_detector(self):
        """
        https://en.wikipedia.org/wiki/Mealy_machine

        .. image:: media/EdgeDetectorStateDiagram.png
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
            assert machine.fire(Bit.ZERO) is Bit.ZERO  # 6. Fire events and obtain outputs.
            assert machine.state is s_0
            assert machine.fire(Bit.ZERO) is Bit.ZERO
            assert machine.state is s_0
            assert machine.fire(Bit.ONE) is Bit.ONE
            assert machine.state is s_1
            assert machine.fire(Bit.ONE) is Bit.ZERO
            assert machine.state is s_1
            assert machine.fire(Bit.ZERO) is Bit.ONE
            assert machine.state is s_0

    # noinspection PyArgumentList
    def test_traffic_lights(self):
        """
        .. image:: media/TrafficLightStateDiagram.png
        """

        class Inputs(enum.Enum):  # 1. The inputs.
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

        red.actions[Inputs.RED_TIMEOUT] = green.action  # 4a. The *state* actions.
        green.actions[Inputs.GREEN_TIMEOUT] = amber.action
        amber.actions[Inputs.AMBER_TIMEOUT] = red.action

        with Machine(initial_state=red) as machine:  # 5. The machine.
            machine.actions[Inputs.RED_TIMEOUT] = flashing_red.action  # 4b. The *machine* actions.
            machine.actions[Inputs.AMBER_TIMEOUT] = flashing_red.action
            machine.actions[Inputs.GREEN_TIMEOUT] = flashing_red.action
            machine.actions[Inputs.ERROR] = flashing_red.action

            assert machine.state is red
            assert machine.fire(Inputs.RED_TIMEOUT) is Outputs.GREEN  # 6. Fire events and obtain outputs.
            assert machine.state is green
            assert machine.fire(Inputs.GREEN_TIMEOUT) is Outputs.AMBER
            assert machine.state is amber
            assert machine.fire(Inputs.AMBER_TIMEOUT) is Outputs.RED
            assert machine.state is red
            assert machine.fire(Inputs.AMBER_TIMEOUT) is Outputs.FLASHING_RED
            assert machine.state is flashing_red
            assert machine.fire(Inputs.ERROR) is Outputs.FLASHING_RED
            assert machine.state is flashing_red

    def test_transitioning_between_states_and_enter_and_exit_overrides(self):
        Events = enum.Enum('Events', 'MACHINE_TO_STATE_0 STATE_TO_STATE_1')

        states = [LoggingState(ident=0), LoggingState(ident=1)]
        states[0].actions[Events.STATE_TO_STATE_1] = states[1], None
        states[1].actions[Events.STATE_TO_STATE_1] = states[1], None

        with LoggingMachine(initial_state=states[0]) as machine:
            machine.actions[Events.MACHINE_TO_STATE_0] = states[0], None

            assert machine.state is states[0]
            assert machine.fire(Events.MACHINE_TO_STATE_0) is None
            assert machine.state is states[0]
            assert machine.fire(Events.STATE_TO_STATE_1) is None
            assert machine.state is states[1]
            assert machine.fire(Events.STATE_TO_STATE_1) is None
            assert machine.state is states[1]
            assert machine.fire(Events.MACHINE_TO_STATE_0) is None
            assert machine.state is states[0]

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Enter state 1',
            'Exit state 1',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]

    def test_that_unhandled_event_gets_raised(self):
        Events = enum.Enum('Events', 'UNHANDLED')
        state0 = State()
        with pytest.raises(KeyError):
            with Machine(initial_state=state0) as machine:
                assert machine.state is state0
                machine.fire(Events.UNHANDLED)

    def test_that_exception_can_be_suppressed(self):
        Events = enum.Enum('Events', 'UNHANDLED')

        class SuppressAllExceptions(State):
            def __exit__(self, exc_type, exc_val, exc_tb):
                return True  # Suppress the exception.

        state0 = SuppressAllExceptions()
        with Machine(initial_state=state0) as machine:
            assert machine.state is state0
            assert machine.fire(Events.UNHANDLED) is None
            assert machine.state is state0

    def test_not_entering_initial_state_if_no_event(self):
        s0 = LoggingState(ident=0)
        with LoggingMachine(initial_state=s0):
            pass

        assert log == [
            'Enter machine',
            'Exit machine',
        ]

    def test_nesting_order(self):
        s0 = LoggingState(ident=0)
        with LoggingMachine(initial_state=s0) as m:
            m.actions[1] = s0, None
            m.fire(1)

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]

    def test_machine_enter_throwing(self):
        s0 = LoggingState(ident=0, enter_throws=True)
        with pytest.raises(AssertionError, match='Enter machine throw'):
            with LoggingMachine(initial_state=s0, enter_throws=True) as m:
                m.actions[1] = s0, None
                m.fire(1)

        assert log == [
            'Enter machine',
        ]

    def test_state_enter_throwing(self):
        s0 = LoggingState(ident=0, enter_throws=True)
        with pytest.raises(AssertionError, match='Enter state 0 throw'):
            with LoggingMachine(initial_state=s0) as m:
                m.actions[1] = s0, None
                m.fire(1)

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]

    def test_machine_exit_throwing(self):
        s0 = LoggingState(ident=0)
        with pytest.raises(AssertionError, match='Exit machine throw'):
            with LoggingMachine(initial_state=s0, exit_throws=True) as m:
                m.actions[1] = s0, None
                m.fire(1)

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]

    def test_state_exit_throwing(self):
        s0 = LoggingState(ident=0, exit_throws=True)
        with pytest.raises(AssertionError, match='Exit state 0 throw'):
            with LoggingMachine(initial_state=s0) as m:
                m.actions[1] = s0, None
                m.fire(1)

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]

    def test_machine_and_state_exit_throwing(self):
        s0 = LoggingState(ident=0, exit_throws=True)
        # State exit throw swallowed because machine exit also throws.
        with pytest.raises(AssertionError, match='Exit machine throw'):
            with LoggingMachine(initial_state=s0, exit_throws=True) as m:
                m.actions[1] = s0, None
                m.fire(1)

        assert log == [
            'Enter machine',
            'Enter state 0',
            'Exit state 0',
            'Exit machine',
        ]
