#!/usr/bin/env python
"""
Scripted demo for gittuf's multi‑repository functionality.

This script is modelled after `run-demo.py` in this repository.  It
walks through the steps of creating a controller repository and a
network repository, linking them together and then propagating and
verifying their reference state logs.  Use the accompanying
`multi-repo-demo.md` for a manual walkthrough.

The script prints each command before executing it and pauses between
sections to allow the user to observe output.  Set the environment
variable `NO_PROMPT=1` to disable the pauses.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile

# commands this script requires to run successfully
REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]


def check_binaries() -> None:
    """Ensure required binaries are available on the PATH."""
    for binary in REQUIRED_BINARIES:
        if not shutil.which(binary):
            raise RuntimeError(f"required command {binary} not found")


def prompt_key(prompt: str) -> None:
    """Display a prompt and wait for the user to press enter unless
    NO_PROMPT is set."""
    no_prompt = os.environ.get("NO_PROMPT") == "1"
    if no_prompt:
        print(f"\n{prompt}")
        return
    try:
        input(f"\n{prompt} -- press enter to continue")
    except Exception:
        # Input can occasionally raise when run in certain environments
        pass


def display_command(cmd: str) -> None:
    """Display a command with the current working directory."""
    print(f"[{os.getcwd()}] $ {cmd}")


def run_command(cmd: str, expected_retcode: int = 0) -> None:
    """Run a shell command and ensure it exits with the expected return code."""
    retcode = subprocess.call(shlex.split(cmd))
    if retcode != expected_retcode:
        raise RuntimeError(
            f"Expected return code {expected_retcode} but command exited with {retcode}"
        )


def run_demo() -> None:
    """Perform the multi‑repository demo."""
    check_binaries()

    current_dir = os.getcwd()
    keys_dir = os.path.join(current_dir, "keys")

    # create a temporary directory for the demo
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_keys_dir = os.path.join(tmp_dir.name, "keys")
    controller_dir = os.path.join(tmp_dir.name, "controller")
    network_dir = os.path.join(tmp_dir.name, "network")
    root_pub_path = os.path.join(tmp_keys_dir, "root.pub")

    # copy keys and set permissions
    shutil.copytree(keys_dir, tmp_keys_dir)
    os.mkdir(controller_dir)
    os.mkdir(network_dir)
    for key_file in os.listdir(tmp_keys_dir):
        os.chmod(os.path.join(tmp_keys_dir, key_file), 0o600)

    # define useful paths
    authorized_key_path = os.path.join(tmp_keys_dir, "authorized")
    root_key_path = os.path.join(tmp_keys_dir, "root")
    targets_key_path = os.path.join(tmp_keys_dir, "targets")
    targets_pub_path = os.path.join(tmp_keys_dir, "targets.pub")

    # ensure output is not paged
    os.environ["PAGER"] = "cat"

    # ====== Controller repository setup ======
    prompt_key("Initialise controller Git repository")
    os.chdir(controller_dir)
    display_command("git init -b main")
    run_command("git init -b main")

    prompt_key("Configure controller Git settings and signing key")
    for cmd in [
        "git config --local gpg.format ssh",
        "git config --local commit.gpgsign true",
        f"git config --local user.signingkey {authorized_key_path}",
        "git config --local user.name gittuf-demo",
        "git config --local user.email gittuf.demo@example.com",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Initialise controller gittuf root of trust")
    cmd = f"gittuf trust init -k {root_key_path}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add policy key to controller's root of trust")
    cmd = f"gittuf trust add-policy-key -k {root_key_path} --policy-key {targets_pub_path}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Make repository a controller")
    cmd = f"gittuf trust make-controller -k {root_key_path}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add global threshold rule to controller")
    cmd = (
        "gittuf trust add-global-rule "
        f"-k {root_key_path} "
        "--rule-name global-branch-threshold "
        "--rule-pattern git:refs/heads/* "
        "--type threshold "
        "--threshold 1"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Stage and apply controller trust changes")
    for cmd in [
        f"gittuf trust stage --local-only -k {root_key_path}",
        f"gittuf trust apply --local-only -k {root_key_path}",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Register network repository with controller")
    network_abs = os.path.abspath(network_dir)
    cmd = (
        "gittuf trust add-network-repository "
        f"-k {root_key_path} "
        "--name network "
        f"--location {network_abs} "
        f"--initial-root-principal {root_pub_path}"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Stage and apply controller changes after network registration")
    for cmd in [
        f"gittuf trust stage --local-only -k {root_key_path}",
        f"gittuf trust apply --local-only -k {root_key_path}",
    ]:
        display_command(cmd)
        run_command(cmd)

    # ====== Network repository setup ======
    prompt_key("Initialise network Git repository")
    os.chdir(network_dir)
    display_command("git init -b main")
    run_command("git init -b main")

    prompt_key("Configure network Git settings and signing key")
    for cmd in [
        "git config --local gpg.format ssh",
        "git config --local commit.gpgsign true",
        f"git config --local user.signingkey {authorized_key_path}",
        "git config --local user.name gittuf-demo",
        "git config --local user.email gittuf.demo@example.com",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Initialise network gittuf root of trust")
    cmd = f"gittuf trust init -k {root_key_path}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add policy key to network's root of trust")
    cmd = f"gittuf trust add-policy-key -k {root_key_path} --policy-key {targets_pub_path}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Link controller repository to network")
    controller_abs = os.path.abspath(controller_dir)
    cmd = (
        "gittuf trust add-controller-repository "
        f"-k {root_key_path} "
        "--name controller "
        f"--location {controller_abs} "
        f"--initial-root-principal {root_pub_path}"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Stage and apply network trust changes")
    for cmd in [
        f"gittuf trust stage --local-only -k {root_key_path}",
        f"gittuf trust apply --local-only -k {root_key_path}",
    ]:
        display_command(cmd)
        run_command(cmd)

    # ====== Propagate and verify ======
    prompt_key("Propagate RSL entries into network and verify network state")
    for cmd in [
        "gittuf rsl propagate",
        "gittuf verify-network",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Multi‑repository demo complete!")

    # return to original directory to avoid confusing the user
    os.chdir(current_dir)


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)