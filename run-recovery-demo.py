#!/usr/bin/env python

import os
import shlex
import shutil
import subprocess
import sys
import tempfile


NO_PROMPT = False
REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]


def check_binaries():
    for p in REQUIRED_BINARIES:
        if not shutil.which(p):
            raise Exception(f"required command {p} not found")


def prompt_key(prompt):
    if NO_PROMPT:
        print("\n" + prompt)
        return
    inp = False
    while inp != "":
        try:
            inp = input(f"\n{prompt} -- press any key to continue")
        except Exception:
            pass


def display_command(cmd):
    print(f"[{os.getcwd()}] $ {cmd}")

def run_command(cmd, expected_retcode=0):
    retcode = subprocess.call(shlex.split(cmd))
    if retcode != expected_retcode:
        raise Exception(f"Expected {expected_retcode} from process but it exited with {retcode}.")

def run_demo():
    current_dir = os.getcwd()
    keys_dir = "keys"

    tmp_dir = tempfile.TemporaryDirectory()
    tmp_keys_dir = os.path.join(tmp_dir.name, keys_dir)
    tmp_repo_dir = os.path.join(tmp_dir.name, "repo")

    shutil.copytree(os.path.join(current_dir, keys_dir), tmp_keys_dir)
    os.mkdir(tmp_repo_dir)
    os.chdir(tmp_repo_dir)

    for key in os.listdir(tmp_keys_dir):
        os.chmod(os.path.join(tmp_keys_dir, key), 0o600)

    authorized_key_path_git = os.path.join(tmp_keys_dir, "authorized")
    unauthorized_key_path_git = os.path.join(tmp_keys_dir, "unauthorized")

    authorized_key_path_policy = os.path.join(tmp_keys_dir, "authorized.pub")

    prompt_key("Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Set repo config to use demo identity and test key")
    cmd = "git config --local gpg.format ssh"
    display_command(cmd)
    run_command(cmd)
    cmd = "git config --local commit.gpgsign true"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    run_command(cmd)
    cmd = "git config --local user.name gittuf-demo"
    display_command(cmd)
    run_command(cmd)
    cmd = "git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command("export PAGER=cat")

    prompt_key("Initialize gittuf root of trust")
    cmd = "gittuf trust init -k ../keys/root"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add policy key to gittuf root of trust")
    cmd = (
        "gittuf trust add-policy-key"
        " -k ../keys/root"
        " --policy-key ../keys/targets.pub"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Initialize policy")
    cmd = "gittuf policy init -k ../keys/targets"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add trusted person to gittuf policy file")
    cmd = (
        "gittuf policy add-person"
        " -k ../keys/targets"
        " --person-ID 'authorized-user'"
        f" --public-key {authorized_key_path_policy}"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add rule to protect the main branch")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        " --authorize authorized-user"
    )
    display_command(cmd)
    run_command(cmd)

    cmd = "gittuf policy stage --local-only"
    display_command(cmd)
    run_command(cmd)

    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Make an authorized change to repo's main branch")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd)
    cmd = "git commit -m 'Initial commit'"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Record change to main in RSL")
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("gittuf's verification succeeded!")

    prompt_key("Simulate a repository compromise: switch to an unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_key_path_git}"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Push an unauthorized change to main")
    display_command("echo 'This change was never approved!' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("This change was never approved!\n")
    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd)
    cmd = "git commit -m 'Malicious update'"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Record change to main in RSL")
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    run_command(cmd)

    bad_entry_id = subprocess.check_output(
        shlex.split("git show --pretty=%H refs/gittuf/reference-state-log")
    ).decode().splitlines()[0]
    display_command(f"# note the RSL entry for the malicious commit: {bad_entry_id}")

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)

    prompt_key("gittuf detected the unauthorized change!")

    prompt_key(
        "A developer clones the compromised repository, unaware it's been"
        " tampered with"
    )
    os.chdir(tmp_dir.name)
    cmd = f"gittuf clone {tmp_repo_dir} victim"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)

    prompt_key(
        "gittuf's clone verification immediately flags the compromised"
        " history, even though the underlying git clone itself succeeds"
    )

    prompt_key(
        "The fix is issued: skip the RSL entry for the malicious commit, then"
        " revert it with a new, forward-only commit. Since the revert commit's"
        " tree is identical to the last known-good state, this doesn't need an"
        " authorized signer, so anyone who can push to the repo can issue it"
        " -- we'll keep using the unauthorized key here to demonstrate that"
    )
    os.chdir(tmp_repo_dir)
    cmd = (
        "gittuf rsl annotate --skip --local-only"
        " --message 'Reverting unauthorized change'"
        f" {bad_entry_id}"
    )
    display_command(cmd)
    run_command(cmd)
    cmd = "git revert --no-edit HEAD"
    display_command(cmd)
    run_command(cmd)
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Verify branch protection again on the recovered repository")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("gittuf verification succeeds again on the recovered repository!")

    prompt_key("The developer's clone can now sync to the recovered state")
    os.chdir(os.path.join(tmp_dir.name, "victim"))
    cmd = "git pull origin main"
    display_command(cmd)
    run_command(cmd)
    cmd = "gittuf sync origin"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Verify branch protection on the developer's recovered clone")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("The developer's repository is now recovered and verifies successfully!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-prompt":
            NO_PROMPT = True
    check_binaries()
    run_demo()
