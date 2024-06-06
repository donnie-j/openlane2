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
{
  lib,
  clangStdenv,
  fetchFromGitHub,
  nix-gitignore,
  buildPythonPackage,
  # Tools
  klayout,
  klayout-pymod,
  libparse,
  immutabledict,
  magic,
  netgen,
  opensta,
  openroad,
  surelog,
  tclFull,
  verilator,
  verilog,
  volare,
  # PIP
  click,
  cloup,
  pyyaml,
  rich,
  requests,
  pcpp,
  tkinter,
  lxml,
  deprecated,
  psutil,
  pytestCheckHook,
  pyfakefs,
  system,
}:
buildPythonPackage rec {
  name = "openlane";

  version_file = builtins.readFile ./openlane/__version__.py;
  version_list = builtins.match ''.+''\n__version__ = "([^"]+)"''\n.+''$'' version_file;
  version = builtins.head version_list;

  src = [
    ./Readme.md
    ./setup.py
    (nix-gitignore.gitignoreSourcePure "__pycache__\nruns/\n" ./openlane)
    ./type_stubs
    ./requirements.txt
  ];

  unpackPhase = ''
    echo $src
    for file in $src; do
      BASENAME=$(python3 -c "import os; print('$file'.split('-', maxsplit=1)[1], end='$EMPTY')")
      cp -r $file $PWD/$BASENAME
    done
    ls -lah
  '';

  buildInputs = [];

  includedTools = [
    opensta
    openroad
    klayout
    verilog
    verilator
    tclFull
    surelog
  ];

  propagatedBuildInputs =
    [
      # Python
      click
      cloup
      pyyaml
      rich
      requests
      pcpp
      volare
      tkinter
      lxml
      deprecated
      immutabledict
      libparse
      psutil
      klayout-pymod
    ]
    ++ includedTools;

  doCheck = false;
  checkInputs = [pytestCheckHook pyfakefs];

  computed_PATH = lib.makeBinPath propagatedBuildInputs;

  # Make PATH available to OpenLane subprocesses
  makeWrapperArgs = [
    "--prefix PATH : ${computed_PATH}"
  ];

  meta = with lib; {
    description = "Hardware design and implementation infrastructure library and ASIC flow";
    homepage = "https://efabless.com/openlane";
    mainProgram = "openlane";
    license = licenses.asl20;
    platforms = platforms.linux ++ platforms.darwin;
  };
}
