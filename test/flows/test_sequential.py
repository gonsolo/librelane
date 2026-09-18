# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Type

import pytest

from librelane.flows import flow as flow_module, sequential as sequential_flow_module
from librelane.steps import Step, step as step_module

pytestmark = pytest.mark.all

mock_variables = pytest.mock_variables


@pytest.fixture
def MetricIncrementer():
    from librelane.steps import Step

    @Step.factory.register()
    class MetricIncrementer(Step):
        id = "Test.MetricIncrementer"
        inputs = []
        outputs = []

        counter_name = "counter"

        def run(self, state_in, **kwargs):
            metric_to_increment = state_in.metrics.get(self.counter_name, 0)
            metric_to_increment += 1
            return {}, {self.counter_name: metric_to_increment}

    return MetricIncrementer


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_sequential_flow(MetricIncrementer: Type[Step]):
    from librelane.flows import SequentialFlow

    class Dummy(SequentialFlow):
        Steps = [
            MetricIncrementer,
            MetricIncrementer,
            MetricIncrementer,
            MetricIncrementer,
        ]

    flow = Dummy(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )

    assert [step.id for step in flow.Steps] == [
        "Test.MetricIncrementer",
        "Test.MetricIncrementer-1",
        "Test.MetricIncrementer-2",
        "Test.MetricIncrementer-3",
    ], "SequentialFlow did not increment IDs properly for duplicate steps"

    state = flow.start()
    assert state.metrics["counter"] == 4, "SequentialFlow did not run properly"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_custom_seqflow(MetricIncrementer):
    from librelane.flows import SequentialFlow

    MyFlow = SequentialFlow.Make(
        [
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
        ]
    )

    for step in MyFlow.Steps:
        assert issubclass(
            step, MetricIncrementer
        ), "CustomSequentialFlow could not properly import Steps by id"

    flow = MyFlow(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )

    state = flow.start()
    assert state.metrics["counter"] == 4, "CustomSequentialFlow did not run properly"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_custom_seqflow_bad_id(MetricIncrementer):
    from librelane.flows import SequentialFlow

    with pytest.raises(TypeError, match="No step found with id"):
        SequentialFlow.Make(
            [
                "Test.MetricIncrementer",
                "Test.MetricIncrementer",
                "Test.NotARealIncrement",
                "Test.MetricIncrementer",
            ]
        )


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_substitution(MetricIncrementer):
    from librelane.flows import SequentialFlow

    @Step.factory.register()
    class FirstMetricIncrementer(MetricIncrementer):
        id = "Test.FirstMetricIncrementer"
        counter_name = "first_counter"

    @Step.factory.register()
    class OtherMetricIncrementer(MetricIncrementer):
        id = "Test.OtherMetricIncrementer"
        counter_name = "other_counter"

    @Step.factory.register()
    class FinalMetricIncrementer(MetricIncrementer):
        id = "Test.FinalMetricIncrementer"
        counter_name = "final_counter"

    MyFlow = SequentialFlow.Make(
        [
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
        ]
    )

    flow = MyFlow.Substitute(
        {
            "-Test.MetricIncrementer": FirstMetricIncrementer,
            "Test.MetricIncrementer-1": OtherMetricIncrementer,
            "Test.MetricIncrementer": "Test.OtherMetricIncrementer",
            "+Test.MetricIncrementer-1": "Test.FinalMetricIncrementer",
        }
    )(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )

    assert [step.id for step in flow.Steps] == [
        "Test.FirstMetricIncrementer",
        "Test.OtherMetricIncrementer",
        "Test.OtherMetricIncrementer-1",
        "Test.MetricIncrementer",
        "Test.MetricIncrementer-1",
        "Test.FinalMetricIncrementer",
    ], "SequentialFlow did not increment IDs properly for duplicate steps"

    state = flow.start()
    assert state.metrics == {
        "first_counter": 1,
        "other_counter": 2,
        "counter": 2,
        "final_counter": 1,
    }, "step substitution execution returned unexpected metrics"

    flow2 = MyFlow.Substitute(
        [
            ("-Test.MetricIncrementer", FirstMetricIncrementer),
            ("Test.MetricIncrementer", "Test.OtherMetricIncrementer"),
            ("Test.MetricIncrementer", OtherMetricIncrementer),
            ("+Test.MetricIncrementer-1", "Test.FinalMetricIncrementer"),
        ]
    )(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )

    assert [step.id for step in flow2.Steps] == [
        "Test.FirstMetricIncrementer",
        "Test.OtherMetricIncrementer",
        "Test.OtherMetricIncrementer-1",
        "Test.MetricIncrementer",
        "Test.MetricIncrementer-1",
        "Test.FinalMetricIncrementer",
    ], "SequentialFlow did not increment IDs properly for duplicate steps when using tuples"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_substitute_none(MetricIncrementer):
    from librelane.flows import SequentialFlow, FlowException

    MyFlow = SequentialFlow.Make(
        [
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
        ]
    )

    with pytest.raises(FlowException, match="Cannot prepend or append None"):
        MyFlow.Substitute({"-Test.MetricIncrementer": None})

    with pytest.raises(FlowException, match="Cannot prepend or append None"):
        MyFlow.Substitute({"+Test.MetricIncrementer": None})

    flow_with_removal = MyFlow.Substitute({"Test.MetricIncrementer-1": None})(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )
    assert [step.id for step in flow_with_removal.Steps] == [
        "Test.MetricIncrementer",
        "Test.MetricIncrementer-1",
        "Test.MetricIncrementer-2",
    ], "Removal did not work as expected"

    with pytest.raises(FlowException, match="no steps with ID"):
        MyFlow.Substitute({"Test.MetricIncrementer-80": None})


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_bad_substitution(MetricIncrementer):
    from librelane.flows import SequentialFlow, FlowException

    MyFlow = SequentialFlow.Make(
        [
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
            "Test.MetricIncrementer",
        ]
    )

    with pytest.raises(
        FlowException, match=r"no replacement step with ID '[\w\.]+' found"
    ):
        MyFlow.Substitute({"Test.MetricIncrementer": "Test.NotARealStep"})(
            {
                "DESIGN_NAME": "WHATEVER",
                "VERILOG_FILES": ["/cwd/src/a.v"],
            },
            design_dir="/cwd",
            pdk="dummy",
            scl="dummy_scl",
            pdk_root="/pdk",
        )
    with pytest.raises(
        FlowException, match=r"no steps with ID '[\w\.]+' found in flow"
    ):
        MyFlow.Substitute({"Test.NotAStepInTheFlow": "Test.MetricIncrementer"})(
            {
                "DESIGN_NAME": "WHATEVER",
                "VERILOG_FILES": ["/cwd/src/a.v"],
            },
            design_dir="/cwd",
            pdk="dummy",
            scl="dummy_scl",
            pdk_root="/pdk",
        )


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_flow_control(MetricIncrementer):
    from librelane.flows import SequentialFlow

    class OtherMetricIncrementer(MetricIncrementer):
        id = "Test.OtherMetricIncrementer"
        counter_name = "other_counter"

    class AnotherMetricIncrementer(MetricIncrementer):
        id = "Test.AnotherMetricIncrementer"
        counter_name = "another_counter"

    class YetAnotherMetricIncrementer(MetricIncrementer):
        id = "Test.YetAnotherMetricIncrementer"
        counter_name = "yet_another_counter"

    class LastMetricIncrementer(MetricIncrementer):
        id = "Test.LastMetricIncrementer"
        counter_name = "last_another_counter"

    class Dummy(SequentialFlow):
        Steps = [
            MetricIncrementer,
            OtherMetricIncrementer,
            AnotherMetricIncrementer,
            YetAnotherMetricIncrementer,
            LastMetricIncrementer,
        ]

    flow = Dummy(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )
    state = flow.start(
        frm="test.othermetricincrementer",
        to="test.lastmetricincrement*",
        skip=["test.*another*"],
    )
    assert list(state.metrics.keys()) == [
        "other_counter",
        "last_another_counter",
    ], "flow control did not yield the expected results"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_wildcard_gating(MetricIncrementer):
    from librelane.flows import SequentialFlow
    from librelane.config import Variable

    class OtherMetricIncrementer(MetricIncrementer):
        id = "Test.OtherMetricIncrementer"

    class AnotherMetricIncrementer(MetricIncrementer):
        id = "Test.AnotherMetricIncrementer"

    class YetAnotherMetricIncrementer(MetricIncrementer):
        id = "Test.YetAnotherMetricIncrementer"

    class LastMetricIncrementer(MetricIncrementer):
        id = "Test.LastMetricIncrementer"

    class Dummy(SequentialFlow):
        Steps = [
            MetricIncrementer,
            OtherMetricIncrementer,
            AnotherMetricIncrementer,
            YetAnotherMetricIncrementer,
            LastMetricIncrementer,
        ]

        config_vars = [
            Variable("TEST_GATING_VARIABLE", bool, description="x", default=False)
        ]

        gating_config_vars = {"*AnotherMetric*": ["TEST_GATING_VARIABLE"]}

    flow = Dummy(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )
    state = flow.start()
    assert state.metrics["counter"] == 3, "Gating variable did not work properly"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_gating_validation(MetricIncrementer):
    from librelane.flows import SequentialFlow
    from librelane.config import Variable

    class Dummy(SequentialFlow):
        Steps = [MetricIncrementer]

        config_vars = [
            Variable("TEST_GATING_VARIABLE", bool, description="x", default=False),
            Variable("BAD_GATING_VARIABLE", int, description="x", default=0),
        ]

    with pytest.raises(TypeError, match="does not match any declared config_vars"):

        class _Test1(Dummy):
            gating_config_vars = {"Test.MetricIncrementer": ["DOESNT_MATCH_ANYTHING"]}

    with pytest.raises(TypeError, match="is not a Boolean"):

        class _Test2(Dummy):
            gating_config_vars = {"Test.MetricIncrementer": ["BAD_GATING_VARIABLE"]}

@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_async_steps_overlap():
    """
    Proves AsyncSteps actually overlaps execution, not just that it doesn't
    crash: BlockingCheck can only complete once Unblocker (a *later* Step in
    the main sequential line) sets an Event. If AsyncSteps' launch of
    BlockingCheck were accidentally synchronous, Unblocker would never get a
    chance to run first, and BlockingCheck's own bounded wait() would time
    out and fail the test deterministically rather than hang it.
    """
    import threading
    from librelane.flows import SequentialFlow

    unblock = threading.Event()

    @Step.factory.register()
    class BlockingCheck(Step):
        id = "Test.BlockingCheck"
        inputs = []
        outputs = []

        def run(self, state_in, **kwargs):
            if not unblock.wait(timeout=5):
                raise TimeoutError(
                    "Test.BlockingCheck was not started concurrently -- "
                    "Test.Unblocker never got a chance to run first"
                )
            return {}, {"drc_ran": True}

    @Step.factory.register()
    class Unblocker(Step):
        id = "Test.Unblocker"
        inputs = []
        outputs = []

        def run(self, state_in, **kwargs):
            unblock.set()
            return {}, {}

    @Step.factory.register()
    class JoinPoint(Step):
        id = "Test.JoinPoint"
        inputs = []
        outputs = []

        def run(self, state_in, **kwargs):
            return {}, {}

    class Dummy(SequentialFlow):
        AsyncSteps = {"Test.BlockingCheck": "Test.JoinPoint"}
        Steps = [BlockingCheck, Unblocker, JoinPoint]

    flow = Dummy(
        {
            "DESIGN_NAME": "WHATEVER",
            "VERILOG_FILES": ["/cwd/src/a.v"],
        },
        design_dir="/cwd",
        pdk="dummy",
        scl="dummy_scl",
        pdk_root="/pdk",
    )

    state = flow.start()
    assert state.metrics["drc_ran"] is True, (
        "AsyncSteps did not merge the asynchronous step's metrics in "
        "before its declared join point ran"
    )


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([flow_module, sequential_flow_module, step_module])
def test_async_steps_validation(MetricIncrementer):
    from librelane.flows import SequentialFlow

    @Step.factory.register()
    class HasOutputs(Step):
        id = "Test.HasOutputs"
        inputs = []
        from librelane.state import DesignFormat

        outputs = [DesignFormat.NETLIST]

        def run(self, state_in, **kwargs):
            return {}, {}

    class Dummy(SequentialFlow):
        Steps = [MetricIncrementer, HasOutputs]

    with pytest.raises(TypeError, match="does not match any Step"):

        class _Test1(Dummy):
            AsyncSteps = {"Test.DoesNotExist": "Test.MetricIncrementer"}

    with pytest.raises(TypeError, match="does not match any Step"):

        class _Test2(Dummy):
            AsyncSteps = {"Test.MetricIncrementer": "Test.DoesNotExist"}

    with pytest.raises(TypeError, match="is not supported"):

        class _Test3(Dummy):
            AsyncSteps = {"Test.HasOutputs": "Test.MetricIncrementer"}

    with pytest.raises(TypeError, match="must come after it"):
        # Test.MetricIncrementer has no outputs (so it clears that check),
        # declared async with a join point that comes *before* it in this
        # order -- isolates the ordering check from the outputs check.
        class _Test4(Dummy):
            Steps = [HasOutputs, MetricIncrementer]
            AsyncSteps = {"Test.MetricIncrementer": "Test.HasOutputs"}
