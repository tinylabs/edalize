# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path
import platform
import re
import subprocess

from edalize.tools.edatool import Edatool
from edalize.utils import EdaCommands

logger = logging.getLogger(__name__)


class Ise(Edatool):
    """
    Ise Backend.

    A core (usually the system core) can add the following files:

    * Standard design sources
    * Constraints: Supply ucf files with file_type=ucf or unmanaged constraints with file_type SDC
    """

    argtypes = ["vlogdefine", "vlogparam", "generic"]

    TOOL_OPTIONS = {
                    
        "family": {
            "type": "String",
            "desc": "FPGA family (e.g. spartan6)",
        },
        "device": {
            "type": "String",
            "desc": "FPGA device (e.g. xc6slx45)",
        },
        "package": {
            "type": "String",
            "desc": "FPGA package (e.g. csg324)",
        },
        "speed": {
            "type": "String",
            "desc": "FPGA speed grade (e.g. -2)",
        },
        "board_device_index": {
            "type": "String",
            "desc": "Specifies the FPGA's device number in the JTAG chain, starting at 1",
        },
        "synth": {
            "type": "String",
            "desc": "Synthesis tool. Allowed values are ise (default) or none."
        },
    }

    def get_version(self):
        """
        Get tool version.

        This gets the Ise version by running ise -version and
        parsing the output. If this command fails, "unknown" is returned.
        """
        version = "unknown"
        try:
            ise_text = subprocess.Popen(
                ["xst", "--help"], stdout=subprocess.PIPE, env=os.environ
            ).communicate()[0]
            version_exp = r"xst.*(?P<version>v.*) \(.*"

            match = re.search(version_exp, str(ise_text))
            if match is not None:
                version = match.group("version")
        except Exception:
            logger.warning("Unable to recognize Ise version")

        return version

    def configure(self, edam):
        """
        Configuration is the first phase of the build.

        This writes the project TCL files and Makefile. It first collects all
        sources, IPs and constraints and then writes them to the TCL file along
        with the build steps.
        """
        super().configure(edam)
        src_files = []
        incdirs = []
        edif_files = []
        has_vhdl2008 = False
        has_xci = False
        unused_files = []
        bd_files = []

        for f in self.files:
            file_type = f.get("file_type", "")
            cmd = ""
            if file_type.startswith("verilogSource"):
                cmd = "xfile add"
            elif file_type.startswith("systemVerilogSource"):
                raise RuntimeError ("ISE cannot synthesis systemverilog. Please use synth=yosys")
            elif file_type.startswith("vhdlSource"):
                if f.logical_name:
                    if not f.logical_name in libraries:
                        src_files.append("lib_vhdl new {}\n".format(f.logical_name))
                        libraries.append(f.logical_name)
                    src_files.append ("xfile add {} -lib_vhdl {}\n".format (f.name, f.logical_name))
                else:
                    cmd = "xfile add"
            elif file_type == "tclSource":
                cmd = "source"
            elif file_type == "edif":
                cmd = "xfile add"
                edif_files.append(f["name"])
            elif file_type == "UCF":
                cmd = "xfile_add_exist_ok"
            elif file_type == "BMM":
                cmd = "xfile add"

            if cmd:
                if not self._add_include_dir(f, incdirs):
                    src_files.append(cmd + ' ' + f["name"])
            else:
                unused_files.append(f)
        template_vars = {
            "name": self.name,
            "src_files": "\n".join(src_files),
            #"incdirs": incdirs + ["."],
            "tool_options": self.tool_options,
            "toplevel": self.toplevel,
            "vlogparam": self.vlogparam,
            "vlogdefine": self.vlogdefine,
            "generic": self.generic,
            "netlist_flow": bool(edif_files),
            #"has_vhdl2008": has_vhdl2008,
            #"has_xci": has_xci,
            #"bd_files": bd_files,
        }
        self.render_template("ise-project.tcl.j2", self.name + ".tcl", template_vars)

        jobs = self.tool_options.get("jobs", None)

        #run_template_vars = {"jobs": " -jobs " + str(jobs) if jobs is not None else ""}
        run_template_vars = {
            "name" : self.name
        }
        
        self.render_template(
            "ise-run.tcl.j2", self.name + "_run.tcl", run_template_vars
        )

        synth_template_vars = {
            "jobs": " -jobs " + str(jobs) if jobs is not None else ""
        }

        self.render_template(
            "ise-synth.tcl.j2", self.name + "_synth.tcl", synth_template_vars
        )
        # Write Makefile
        commands = EdaCommands()

        #ise_command = ["ise", "-notrace", "-mode", "batch", "-source"]
        ise_command = ["xtclsh"]
        
        # Create project file
        project_file = self.name + ".xise"
        tcl_file = [self.name + ".tcl"]
        commands.add(ise_command + tcl_file, [project_file], tcl_file + edif_files)
        synth = self.tool_options.get("synth", "ise")
        if synth == "ise":
            depends = [f"{self.name}_synth.tcl", project_file]
            targets = [f"{self.name}/__synthesis_is_complete__"]
            commands.add(ise_command + depends, targets, depends)
        else:
            targets = edif_files

        commands.add([], ["synth"], targets)

        # Bitstream generation
        run_tcl = self.name + "_run.tcl"
        depends = [run_tcl, project_file]
        bitstream = self.name + ".bit"
        commands.add(ise_command + depends, [bitstream], depends)

        commands.add(["ise", project_file], ["build-gui"], [project_file])

        # TODO: Fix programming template to use impact
        depends = [self.name + "_pgm.tcl", bitstream]
        command = [
            "ise",
            "-quiet",
            "-nolog",
            "-notrace",
            "-mode",
            "batch",
            "-source",
            f"{self.name}_pgm.tcl",
            "-tclargs",
        ]
        part = self.tool_options.get("part", "")
        command += [part] if part else []
        command += [bitstream]
        commands.add(command, ["pgm"], depends)

        commands.set_default_target(bitstream)
        commands.write(os.path.join(self.work_root, "Makefile"))
        self.commands = commands.commands
        self.render_template("ise-program.tcl.j2", self.name + "_pgm.tcl")

    def build(self):
        logger.info("Building")
        args = []
        if "pnr" in self.tool_options:
            if self.tool_options["pnr"] == "ise":
                pass
            elif self.tool_options["pnr"] == "none":
                args.append("synth")
        return ("make", self.args, self.work_root)

    def run(self):
        """
        Program the FPGA.

        For programming the FPGA a ise tcl script is written that searches for the
        correct FPGA board and then downloads the bitstream. The tcl script is then
        executed in Ise's batch mode.
        """
        if "pnr" in self.tool_options:
            if self.tool_options["pnr"] == "ise":
                pass
            elif self.tool_options["pnr"] == "none":
                return

        return ("make", ["pgm"], self.work_root)
