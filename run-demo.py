#!/usr/bin/env python

import gnupg
import os
import shlex
import shutil
import subprocess
import tempfile


NO_PROMPT = False
REQUIRED_BINARIES = ["git", "gittuf", "gpg"]


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


def setup_gpg_keys(gpg_dir):
    os.mkdir(gpg_dir)

    gpg = gnupg.GPG(gnupghome=gpg_dir)
    gpg.encoding = "utf-8"

    key_params = gpg.gen_key_input(
        key_type="RSA",
        key_length=1024,
        name_real="Authorized Developer",
        name_email="gittuf.authorized@example.com",
        no_protection=True
    )
    authorized_gpg_key = gpg.gen_key(key_params)

    key_params = gpg.gen_key_input(
        key_type="RSA",
        key_length=1024,
        name_real="Unauthorized Developer",
        name_email="gittuf.unauthorized@example.com",
        no_protection=True
    )
    unauthorized_gpg_key = gpg.gen_key(key_params)

    return authorized_gpg_key, unauthorized_gpg_key


def run_demo():
    current_dir = os.getcwd()
    gpg_dir = "gpg-dir"
    keys_dir = "keys"

    tmp_dir = tempfile.TemporaryDirectory()
    tmp_gpg_dir = os.path.join(tmp_dir.name, gpg_dir)
    tmp_keys_dir = os.path.join(tmp_dir.name, keys_dir)
    tmp_repo_dir = os.path.join(tmp_dir.name, "repo")

    prompt_key("Create test GPG keys")
    authorized_gpg_key, unauthorized_gpg_key = setup_gpg_keys(tmp_gpg_dir)
    prompt_key(
        "Created authorized key with fingerprint"
        f" {authorized_gpg_key.fingerprint} and unauthorized key with"
        f" fingerprint {unauthorized_gpg_key.fingerprint}"
    )

    shutil.copytree(os.path.join(current_dir, keys_dir), tmp_keys_dir)
    os.mkdir(tmp_repo_dir)
    os.chdir(tmp_repo_dir)

    prompt_key("Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Set repo config to use demo identity and test key")
    cmd = f"git config --local user.signingkey {authorized_gpg_key.fingerprint}"
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
        f" --authorize-key gpg:{authorized_gpg_key.fingerprint}"
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
    cmd = "gittuf verify-ref -f main"
    display_command(cmd)
    subprocess.run(shlex.split(cmd), check=True)

    prompt_key("gittuf's verification succeeded!")

    prompt_key("Verify commit signature using gittuf policy")
    cmd = "gittuf verify-commit HEAD"
    display_command(cmd)
    subprocess.run(shlex.split(cmd), check=True)

    prompt_key(
        "gittuf's policy recognizes the signing key and"
        " confirms it's a good signature!"
    )

    prompt_key("Update repo config to use unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_gpg_key.fingerprint}"
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
    cmd = "gittuf verify-ref -f main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("gittuf detected a violation of the branch protection rule!")

    prompt_key("Verify commit signature using gittuf policy")
    cmd = "gittuf verify-commit HEAD"
    display_command(cmd)
    subprocess.run(shlex.split(cmd), check=True)

    prompt_key("gittuf's policy does not recognize the signing key!")

    prompt_key("Rewind to last good state to test file protection rules")
    cmd = "git reset --hard HEAD~1"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = f"git config --local user.signingkey {authorized_gpg_key.fingerprint}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Add rule to protect README.md")
    cmd = ("gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-readme'"
        " --rule-pattern file:README.md"
        f" --authorize-key gpg:{authorized_gpg_key.fingerprint}"
    )
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Make change to README.md using unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_gpg_key.fingerprint}"
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
    cmd = f"git config --local user.signingkey {authorized_gpg_key.fingerprint}"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "gittuf rsl record main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))
    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key("Verify all rules for this change")
    cmd = "gittuf verify-ref -f main"
    display_command(cmd)
    subprocess.call(shlex.split(cmd))

    prompt_key(
        "gittuf detected a **file** protection rule violation even though the"
        " branch protection rule was met!"
    )


if __name__ == "__main__":
    check_binaries()
    run_demo()
