# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path
import platform
import re
import subprocess

from edalize.edatool import Edatool
from edalize.yosys import Yosys
from edalize.flows.ise import Ise as Ise_underlying

logger = logging.getLogger(__name__)


class Ise(Edatool):
    """
    Ise Backend.

    A core (usually the system core) can add the following files:

    * Standard design sources
    * Constraints: Supply xdc files with file_type=xdc or unmanaged constraints with file_type SDC
    * IP: Supply the IP core xci file with file_type=xci and other files (like .prj) as file_type=user
    """

    argtypes = ["vlogdefine", "vlogparam", "generic"]

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {
                "description": "The Ise backend executes Xilinx Ise to build systems and program the FPGA",
                "members": [
                    {
                        "name": "family",
                        "type": "String",
                        "desc": "FPGA family (e.g. spartan6)",
                    },
                    {
                        "name": "device",
                        "type": "String",
                        "desc": "FPGA device (e.g. xc6slx45)",
                    },
                    {
                        "name": "package",
                        "type": "String",
                        "desc": "FPGA package (e.g. csg324)",
                    },
                    {
                        "name": "speed",
                        "type": "String",
                        "desc": "FPGA speed grade (e.g. -2)",
                    },
                    {
                        "name": "synth",
                        "type": "String",
                        "desc": "Synthesis tool. Allowed values are ise (default) and yosys.",
                    },
                    {
                        "name": "pnr",
                        "type": "String",
                        "desc": "P&R tool. Allowed values are ise (default) and none (to just run synthesis)",
                    },
                    {
                        "name": "jobs",
                        "type": "Integer",
                        "desc": "Number of jobs. Useful for parallelizing OOC (Out Of Context) syntheses.",
                    },
                    {
                        "name": "jtag_freq",
                        "type": "Integer",
                        "desc": "The frequency for jtag communication",
                    },
                    {
                        "name": "board_device_index",
                        "type": "String",
                        "desc": "Specifies the FPGA's device number in the JTAG chain, starting at 1",
                    },
                    {
                        "name": "frontends",
                        "type": "String",
                        "desc": "",
                    },
                ],
            }

    def __init__(self, edam=None, work_root=None, eda_api=None, verbose=True):
        super().__init__(edam, work_root, eda_api, verbose)
        edam["flow_options"] = edam["tool_options"]["ise"]
        self.ise = Ise_underlying(edam, work_root, verbose)

    def configure_main(self):
        print ('Running edalize locally')
        self.ise.configure()

    def build_pre(self):
        pass

    def build_post(self):
        pass
