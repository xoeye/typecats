#!/usr/bin/env python
"""A pipenv runner for mypy and other such things"""

import typing as ty
import subprocess
import os
import sys


def run_cmd_in_pipenv(cmd: str, fileorpath: str, cli_args: ty.Iterable = ()):
    """Looks for the closest Pipfile/pipenv and runs the command within that venv"""
    print(f"checking {fileorpath} with {cmd}")
    pipenv_dir = (
        os.path.dirname(fileorpath) if not os.path.isdir(fileorpath) else fileorpath
    )
    found_pipfile = False
    while len(pipenv_dir) > 1:
        if os.path.exists(os.path.join(pipenv_dir, "Pipfile")):
            found_pipfile = True
            break
        pipenv_dir = os.path.dirname(pipenv_dir)

    if found_pipfile:
        fileorpath = (
            fileorpath[len(pipenv_dir) + 1 :]
            if pipenv_dir != fileorpath
            else pipenv_dir
        )
        full_command = ["pipenv", "run", cmd, fileorpath, *cli_args]
        return subprocess.run(full_command, cwd=pipenv_dir)
    else:
        print(
            f"Could not find a pipenv in which to check {fileorpath}. Attempting inside global Python installation."
        )
        return subprocess.run([cmd, fileorpath, *cli_args])


if __name__ == "__main__":
    cmd = sys.argv[1]
    path_args = list()
    cli_args = list()
    for arg in sys.argv[2:]:
        if os.path.exists(arg):
            path_args.append(arg)
        else:
            cli_args.append(arg)

    if len(path_args) == 0:
        raise Exception(
            "Everything passed was considered to be a CLI argument, "
            "so there was nothing to check. " + str(cli_args)
        )

    for path_arg in path_args:
        cp = run_cmd_in_pipenv(cmd, os.path.abspath(path_arg), cli_args)
        cp.check_returncode()
