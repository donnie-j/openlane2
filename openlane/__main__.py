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
import os
import glob
from typing import Type, Optional, List

import click

from .steps import State
from .flows import Flow, SequentialFlow, FlowException, FlowError
from .config import ConfigBuilder, InvalidConfig
from .common import err, warn, log


@click.command()
# @click.option("--verbose", type=click.choice('BASIC', 'INFO', 'DEBUG', 'SILLY'), default="INFO", )
@click.option(
    "-p",
    "--pdk",
    type=str,
    default="sky130A",
    help="The process design kit to use. [default: sky130A]",
)
@click.option(
    "-s",
    "--scl",
    type=str,
    default=None,
    help="The standard cell library to use. [default: varies by PDK]",
)
@click.option(
    "-f",
    "--flow",
    "flow_name",
    type=click.Choice(Flow.factory.list(), case_sensitive=False),
    default=None,
    help="The built-in OpenLane flow to use",
)
@click.option("--pdk-root", default=None, help="Override volare PDK root folder")
@click.option(
    "--run-tag",
    default=None,
    type=str,
    help="An optional name to use for this particular run of an OpenLane-based flow. Mutually exclusive with --last-run.",
)
@click.option(
    "--last-run",
    is_flag=True,
    default=False,
    help="Attempt to resume the last run. Supported by sequential flows. Mutually exclusive with --run-tag.",
)
@click.option(
    "-F",
    "--from",
    "frm",
    type=str,
    default=None,
    help="Start from a step with this id. Supported by sequential flows.",
)
@click.option(
    "-T",
    "--to",
    type=str,
    default=None,
    help="Stop at a step with this id. Supported by sequential flows.",
)
@click.option(
    "-I",
    "--with-initial-state",
    "initial_state_json",
    type=str,
    default=None,
    help="Use this JSON file as an initial state. If this is not specified, the latest `state_out.json` of the run directory will be used if available.",
)
@click.option(
    "-c",
    "--override-config",
    "config_override_strings",
    type=str,
    multiple=True,
    help="For this run only- override a configuration variable with a certain value. In the format KEY=VALUE. Can be specified multiple times. Values must be valid JSON values.",
)
@click.argument("config_file")
def cli(
    flow_name: str,
    pdk_root: Optional[str],
    pdk: str,
    scl: Optional[str],
    config_file: str,
    run_tag: Optional[str],
    last_run: bool,
    frm: Optional[str],
    to: Optional[str],
    initial_state_json: Optional[str],
    config_override_strings: List[str],
):
    # Enforce Mutual Exclusion
    if run_tag is not None and last_run:
        err("--run-tag and --last-run are mutually exclusive.")
        exit(1)

    try:
        config_in, design_dir = ConfigBuilder.load(
            config_file,
            pdk_root=pdk_root,
            pdk=pdk,
            scl=scl,
            config_override_strings=config_override_strings,
        )
    except InvalidConfig as e:
        log(f"[green]Errors have occurred while loading the {e.config}:")
        for error in e.errors:
            err(error)
        if len(e.warnings) > 0:
            log("The following warnings have also been generated:")
            for warning in e.warnings:
                warn(warning)
        log("OpenLane will now quit. Please check your configuration.")
        exit(1)
    except ValueError as e:
        err(e)
        log("OpenLane will now quit.")
        exit(1)

    flow_description = flow_name or config_in.meta.flow

    TargetFlow: Type[Flow]

    if not isinstance(flow_description, str):
        TargetFlow = SequentialFlow.make(flow_description)
    else:
        if FlowClass := Flow.factory.get(flow_description):
            TargetFlow = FlowClass
        else:
            err(
                f"Unknown flow '{flow_description}' specified in configuration's 'meta' object."
            )
            exit(1)

    flow = TargetFlow(config_in, design_dir)
    initial_state: Optional[State] = None
    if initial_state_json is not None:
        initial_state = State.loads(open(initial_state_json).read())

    if last_run:
        runs = glob.glob(os.path.join(design_dir, "runs", "*"))

        latest_time: float = 0
        latest_run: Optional[str] = None
        for run in runs:
            time = os.path.getmtime(run)
            if time > latest_time:
                latest_time = time
                latest_run = run

        if latest_run is None:
            err("--last-run specified, but no runs found.")
            exit(1)

        run_tag = os.path.basename(latest_run)

    try:
        flow.start(
            tag=run_tag,
            frm=frm,
            to=to,
            with_initial_state=initial_state,
        )
    except FlowException as e:
        err(f"The flow has encountered an unexpected error: {e}")
        err("OpenLane will now quit.")
        exit(1)
    except FlowError as e:
        err(f"The following error was encountered while running the flow: {e}")
        err("OpenLane will now quit.")
        exit(2)


if __name__ == "__main__":
    cli()
