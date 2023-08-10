#!/usr/bin/env python

import os
import shlex
import shutil
import subprocess
import tempfile


NO_PROMPT = False
REQUIRED_BINARIES = ["git", "gittuf", "gpg"]
AUTHORIZED_GPG_KEY_ID = "68A760FCD2F5D089DD6EA9743ED92EAC3282A02A"
UNAUTHORIZED_GPG_KEY_ID = "BDB5D6B28E3208612836033CE8654898683AF004"


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
    gpg_dir = "gpg-dir"
    keys_dir = "keys"

    tmp_dir = tempfile.TemporaryDirectory()
    tmp_gpg_dir = os.path.join(tmp_dir.name, gpg_dir)
    tmp_keys_dir = os.path.join(tmp_dir.name, keys_dir)
    tmp_repo_dir = os.path.join(tmp_dir.name, "repo")

    shutil.copytree(os.path.join(current_dir, gpg_dir), tmp_gpg_dir)
    shutil.copytree(os.path.join(current_dir, keys_dir), tmp_keys_dir)
    os.mkdir(tmp_repo_dir)
    os.chdir(tmp_repo_dir)

    prompt_key("Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Set repo config to use demo identity and test key")
    cmd = f"git config --local user.signingkey {AUTHORIZED_GPG_KEY_ID}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.name gittuf-demo"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Set GNUPGHOME")
    os.environ["GNUPGHOME"] = tmp_gpg_dir
    display_command(f"export GNUPGHOME={tmp_gpg_dir}")

    prompt_key("Initialize gittuf root of trust")
    cmd = "gittuf trust init -k ../keys/root"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add policy key to gittuf root of trust")
    cmd = ("gittuf trust add-policy-key"
        " -k ../keys/root"
        " --policy-key ../keys/targets.pub"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Initialize policy")
    cmd = "gittuf policy init -k ../keys/targets"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add rule to protect the main branch")
    cmd = ("gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        f" --authorize-key gpg:{AUTHORIZED_GPG_KEY_ID}"
    )
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
    cmd = "gittuf rsl record main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Update repo config to use unauthorized key")
    cmd = f"git config --local user.signingkey {UNAUTHORIZED_GPG_KEY_ID}"
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
    cmd = "gittuf rsl record main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("gittuf detected a policy violation!")


if __name__ == "__main__":
    check_binaries()
    run_demo()
