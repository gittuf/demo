"""Helpers shared by the run-*.py demo scripts."""

import os
import shlex
import shutil
import subprocess
import sys

NO_PROMPT = len(sys.argv) > 1 and sys.argv[1] == "--no-prompt"


def check_binaries(required_binaries):
    for p in required_binaries:
        if not shutil.which(p):
            raise Exception(f"required command {p} not found")


def prompt_key(prompt):
    if NO_PROMPT:
        print("\n" + prompt)
        return
    inp = False
    while inp != "":
        try:
            inp = input(f"\n{prompt} -- press Enter to continue")
        except EOFError:
            return
        except Exception:
            pass


def display_command(cmd):
    print(f"[{os.getcwd()}] $ {cmd}")


def run_command(cmd, expected_retcode=0):
    retcode = subprocess.call(shlex.split(cmd))
    if retcode != expected_retcode:
        raise Exception(f"Expected {expected_retcode} from process but it exited with {retcode}.")
