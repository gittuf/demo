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
    unauthorized_key_path_git = os.path.join(tmp_keys_dir, "unauthorized.pub")

    authorized_key_path_policy = os.path.join(tmp_keys_dir, "authorized.pub")

    prompt_key("Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Set repo config to use demo identity and test key")
    cmd = f"git config --local gpg.format ssh"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local commit.gpgsign true"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.name gittuf-demo"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command(f"export PAGER=cat")

    prompt_key("Initialize gittuf root of trust")
    cmd = "gittuf trust init -k ../keys/root"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add policy key to gittuf root of trust")
    cmd = (
        "gittuf trust add-policy-key"
        " -k ../keys/root"
        " --policy-key ../keys/targets.pub"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Initialize policy")
    cmd = "gittuf policy init -k ../keys/targets"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add trusted person to gittuf policy file")
    cmd = (
        "gittuf policy add-person"
        " -k ../keys/targets"
        " --person-ID 'authorized-user'"
        f" --public-key {authorized_key_path_policy}"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add rule to protect the main branch")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        " --authorize authorized-user"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    cmd = "gittuf policy stage --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Make change to repo's main branch")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    cmd = "git add README.md"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git commit -m 'Initial commit'"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Record change to main in RSL")
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    subprocess.run(shlex.split(cmd), check=True)

    prompt_key("gittuf's verification succeeded!")

    prompt_key("Update repo config to use unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_key_path_git}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Make unauthorized change to repo's main branch")
    display_command("echo 'This is not allowed!' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("This is not allowed!\n")
    cmd = "git add README.md"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git commit -m 'Update README.md'"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Record change to main in RSL")
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("gittuf detected a violation of the branch protection rule!")

    prompt_key("Rewind to last good state to test file protection rules")
    cmd = "git reset --hard HEAD~1"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add rule to protect README.md")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-readme'"
        " --rule-pattern file:README.md"
        " --authorize authorized-user"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    cmd = "gittuf policy stage --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Make change to README.md using unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_key_path_git}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    display_command("echo 'This is not allowed!' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("This is not allowed!\n")
    cmd = "git add README.md"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git commit -m 'Update README.md'"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("But create RSL entry using authorized key")
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "gittuf rsl record main --local-only"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify all rules for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key(
        "gittuf detected a **file** protection rule violation even though the"
        " branch protection rule was met!"
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-prompt":
            NO_PROMPT = True
    check_binaries()
    run_demo()
