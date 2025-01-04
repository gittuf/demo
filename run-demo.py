#!/usr/bin/env python

import os
import shutil
import tempfile
import click
import subprocess

from utils import prompt_key, display_command, run_command, check_binaries, print_section

REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]

@click.command()
@click.option(
    "--automatic", default=False, type=bool, is_flag=True,
    help="Whether to wait for input before each command is run."
)
@click.option(
    "--repository-directory", default="",
    help="The path where the script should store the working copy of the repository."
)

def run_demo(automatic, repository_directory):
    # Repository Setup
    # Set up directory structure and keys
    current_dir = os.getcwd()
    keys_dir = "keys"

    # Select folder for the working repository copy
    working_dir = repository_directory
    if working_dir == "":
        tmp_dir =  tempfile.TemporaryDirectory()
        working_dir = tmp_dir.name
    else:
        working_dir = os.path.abspath(repository_directory)

    # Select folder for the working repository copy
    tmp_keys_dir = os.path.join(working_dir, keys_dir)
    tmp_repo_dir = os.path.join(working_dir, "repo")
    tmp_keys_dir = shutil.copytree(os.path.join(current_dir, keys_dir), tmp_keys_dir)

    os.mkdir(tmp_repo_dir)
    os.chdir(tmp_repo_dir)

    # Ensure correct permissions for keys
    for key in os.listdir(tmp_keys_dir):
        os.chmod(os.path.join(tmp_keys_dir, key), 0o600)

    # Compute folder paths
    authorized_key_path_git = os.path.join(tmp_keys_dir, "authorized.pub")
    unauthorized_key_path_git = os.path.join(tmp_keys_dir, "unauthorized.pub")
    authorized_key_path_policy = os.path.join(tmp_keys_dir, "authorized.pub")

    # Initialize the Git repository in the chosen directory
    prompt_key(automatic, "Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    run_command(cmd, 0)

    # Set the configuration options needed to sign commits. For this demo, the
    # "authorized" key is used, but note that this is not the key used for
    # managing the policy.
    prompt_key(automatic, "Set repo config to use demo identity and test key")
    cmd = f"git config --local gpg.format ssh"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = f"git config --local commit.gpgsign true"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = f"git config --local user.name gittuf-demo"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = f"git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command(f"export PAGER=cat")

    prompt_key(automatic, "Initialize gittuf root of trust")
    cmd = "gittuf trust init -k ../keys/root"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Add policy key to gittuf root of trust")
    cmd = (
        "gittuf trust add-policy-key"
        " -k ../keys/root"
        " --policy-key ../keys/targets.pub"
    )
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Initialize policy")
    cmd = "gittuf policy init -k ../keys/targets"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Add key definition to policy")
    cmd = (
        "gittuf policy add-key"
        " -k ../keys/targets"
        " --public-key ../keys/authorized.pub"
    )
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Add rule to protect the main branch")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-main'"
        " --rule-pattern git:refs/heads/main"
        f" --authorize-key {authorized_key_path_policy}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Make change to repo's main branch")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git commit -m 'Initial commit'"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Record change to main in RSL")
    cmd = "gittuf rsl record main"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "gittuf's verification succeeded!")

    prompt_key(automatic, "Update repo config to use unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_key_path_git}"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Make unauthorized change to repo's main branch")
    cmd = "echo 'This is not allowed!' >> README.md"
    display_command(cmd)
    subprocess.call(cmd, shell=True) 

    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd, 0)
    
    cmd = "git commit -m 'Update README.md'"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Record change to main in RSL")
    cmd = "gittuf rsl record main"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Verify branch protection for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, 1)

    prompt_key(automatic, "gittuf detected a violation of the branch protection rule!")

    prompt_key(automatic, "Rewind to last good state to test file protection rules")
    cmd = "git reset --hard HEAD~1"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Add rule to protect README.md")
    cmd = (
        "gittuf policy add-rule"
        " -k ../keys/targets"
        " --rule-name 'protect-readme'"
        " --rule-pattern file:README.md"
        f" --authorize-key {authorized_key_path_policy}"
    )
    display_command(cmd)
    run_command(cmd, 0)
    cmd = "gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Make change to README.md using unauthorized key")
    cmd = f"git config --local user.signingkey {unauthorized_key_path_git}"
    display_command(cmd)
    run_command(cmd, 1)

    display_command("echo 'This is not allowed!' >> README.md")
    subprocess.call(cmd, shell=True)

    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git commit -m 'Update README.md'"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "But create RSL entry using authorized key")
    cmd = f"git config --local user.signingkey {authorized_key_path_git}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf rsl record main"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git show refs/gittuf/reference-state-log"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Verify all rules for this change")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, 1)

    prompt_key(automatic, 
        "gittuf detected a **file** protection rule violation even though the"
        " branch protection rule was met!"
    )


if __name__ == "__main__":
    check_binaries(REQUIRED_BINARIES)
    run_demo() # pylint: disable=no-value-for-parameter
