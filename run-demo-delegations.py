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

    root_key_path_git = os.path.join(tmp_keys_dir, "root")
    alice_key_path_git = os.path.join(tmp_keys_dir, "alice")
    alice_key_path_policy = os.path.join(tmp_keys_dir, "alice.pub")
    bob_key_path_git = os.path.join(tmp_keys_dir, "bob.pub")

    prompt_key("Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Set repo config to use demo identity and test key")
    cmd = f"git config --local gpg.format ssh"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local commit.gpgsign true"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.signingkey {root_key_path_git}"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.name gittuf-demo"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command(f"export PAGER=cat")

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

    prompt_key("Add trusted person (Alice) to gittuf policy file")
    cmd = (
        "gittuf policy add-person"
        " -k ../keys/targets"
        " --person-ID 'Alice'"
        f" --public-key {alice_key_path_policy}"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Add rule to protect the main branch")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        " --authorize Alice"
    )
    display_command(cmd)
    run_command(cmd)

    cmd = "gittuf policy stage --local-only"
    display_command(cmd)
    run_command(cmd)

    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Alice sets her signing key and identity on Git")
    cmd = f"git config --local user.signingkey {alice_key_path_git}"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.name Alice"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.email alice@example.com
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Hello, world!' > README.md")
    
    prompt_key("Alice makes a change to repo's main branch")
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
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    run_command
    (cmd)

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("gittuf's verification succeeded!")

    prompt_key("Now Alice adds a policy file to delegate responsibility")
    cmd = (
        "gittuf policy init"
        f" -k {alice_key_path_git}"
        " --policy-name protect-main"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Alice adds Bob as an authorized user in the delegated policy")
    cmd = (
        "gittuf policy add-rule"
        f" -k {alice_key_path_git}"
        " --person-ID 'Bob"
        " --policy-name 'protect-main'"
        f" --public-key {bob_key_path_git}"
    )
    display_command(cmd)
    run_command(cmd)

    prompt_key("Alice adds a rule to delegate her authorization to main")
    cmd = (
        "gittuf policy add-rule"
        f" -k {alice_key_path_git}"
        " --rule-name 'protect-main-delegated'"
        " --policy-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        f" --authorize Bob"
    )
    display_command(cmd)
    run_command(cmd)


    cmd = "gittuf policy stage --local-only"
    display_command(cmd)
    run_command(cmd)

    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Now, Bob makes a change to the main branch!")
    cmd = f"git config --local user.signingkey {bob_key_path_git}"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.name Bob"
    display_command(cmd)
    run_command(cmd)
    cmd = f"git config --local user.email bob@example.com
    display_command(cmd)
    run_command(cmd)

    display_command("echo 'This is Bob's change!' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Hello, Bob!\n")
    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd)
    cmd = "git commit -m 'Initial commit from Bob'"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Record Bob's change to main in RSL")
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    run_command(cmd)
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    run_command(cmd)

    prompt_key("Verify branch protection for Bob's change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)

    prompt_key("gittuf's verification succeeded for Bob's change!")

    prompt_key("Add policy file to delegate responsibility")
    cmd = ( 
        "gittuf policy add-rule"
        "-k ../keys/targets"
        "--rule-name 'protect-main-delegated'"
        "--policy-name protect-main"
        "--rule-pattern git:refs/heads/main"
        "--authorize authorized-user"
    )
    display_command(cmd)
    run_command(cmd)
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-prompt":
            NO_PROMPT = True
    check_binaries()
    run_demo()
