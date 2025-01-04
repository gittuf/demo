#!/usr/bin/env python

################################################################################
#
#          utils.py - Supporting routines for the experiment scripts
#
################################################################################

import os
import shlex
import shutil
import subprocess

def check_binaries(required_binaries):
    """Checks that the supplied binaries are present on the system"""
    for p in required_binaries:
        if not shutil.which(p):
            raise Exception(f"required command {p} not found")

def prompt_key(auto, prompt):
    """Controls the flow of the demo for each step"""
    if auto:
        print(f"\n{prompt}")
    inp = False
    while inp != "":
        try:
            inp = input(f"{prompt} -- press Enter to continue")
        except Exception:
            pass

def display_command(cmd):
    """Displays the supplied command with the current directory prepended"""
    print(f"[{os.getcwd()}] $ {cmd}")

def run_command(cmd, expected_retcode):
    """Runs the supplied command and checks for the expected return code"""
    retcode = subprocess.call(shlex.split(cmd)) 
    if retcode != expected_retcode:
        raise Exception(f"Expected {expected_retcode} from process but it exited with {retcode}.")

def print_section(text):
    """Prints the needed amount of dashes for each section heading"""
    print('\n' + text + ' ' + ('-' * (80 - len(text))))