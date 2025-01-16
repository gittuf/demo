import os
import tempfile
import click
import subprocess

from utils import prompt_key, display_command, run_command, check_binaries 

REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]

def generate_key_hash_store(directory):
    """ Generate a hash which stores the relative path to all keys within a directory """
    return {
        key.split('.')[0]: {
            "private": os.path.join(directory, key),
            "public": os.path.join(directory, f"{key}.pub")
        }
        for key in os.listdir(directory) if not key.endswith('.pub')
    }

@click.command()
@click.option(
    "--automatic", default=False, type=bool, is_flag=True,
    help="Whether to wait for input before each command is run."
)
@click.option(
    "--repository-directory", default="",
    help="The path where the script should store the working copy of the repository."
)

def deployment(automatic, repository_directory):
    """ Runs a series of commands which emulates a possible gittuf deployment """
    # OS SETUP
    # Set up directory structure and keys
    current_dir = os.getcwd()
    root_keys_dir = "keys/roots"
    policy_keys_dir = "keys/policy"
    people_keys_dir = "keys/people"

    # Ensure the keys have the correct access permissions 
    key_dir_list = [root_keys_dir, policy_keys_dir, people_keys_dir]
    for dir in key_dir_list:  
        for key in os.listdir(dir):
            os.chmod(os.path.join(dir, key), 0o600)

    # Select folder for the working repository copy
    working_dir = repository_directory
    if working_dir == "":
        tmp_dir = tempfile.TemporaryDirectory()
        working_dir = tmp_dir.name
    else:
        working_dir = os.path.abspath(repository_directory)

    # Sort key paths into hash for convenient access 
    root_keys_store = generate_key_hash_store(root_keys_dir)  # For R1, R2, R3
    policy_keys_store = generate_key_hash_store(policy_keys_dir)  # For P1, P2, P3
    people_keys_store = generate_key_hash_store(people_keys_dir)  # For Alice, Bob, Carol, etc.

    # REPOSITORY SETUP
    # Initialize the Git repository in the chosen directory
    prompt_key(automatic, "Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    run_command(cmd, 0)

    # Set repo config
    prompt_key(automatic, "Set repo config to use demo identity and root key")
    cmd = f"git config --local user.signingkey {root_keys_store['R1']['private']}"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = "git config --local gpg.format ssh"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = "git config --local commit.gpgsign true"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git config --local user.name gittuf-demo"
    display_command(cmd)
    run_command(cmd, 0)
    cmd = "git config --local user.email gittuf.demo@example.com"
    display_command(cmd)
    run_command(cmd, 0)

    prompt_key(automatic, "Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command("export PAGER=cat")

    # GITTUF COMMANDS 
    # Initialize roots of trust
    prompt_key(automatic, "Initialize gittuf root of trust")
    cmd = f"gittuf trust init -k {root_keys_store['R1']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust add-root-key"
        f" -k {root_keys_store['R1']['private']}"
        f" --root-key {root_keys_store['R2']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust add-root-key"
        f" -k {root_keys_store['R1']['private']}"
        f" --root-key {root_keys_store['R3']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust update-root-threshold"
        f" -k {root_keys_store['R1']['private']}"
        " --threshold 2"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R2']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R3']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf trust apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Initialize top-level policy keys
    prompt_key(automatic, "Initialize top-level policy keys")
    cmd = (
        "gittuf trust add-policy-key"
        f" -k {root_keys_store['R1']['private']}"
        f" --policy-key {policy_keys_store['P1']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust add-policy-key"
        f" -k {root_keys_store['R1']['private']}"
        f" --policy-key {policy_keys_store['P2']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust add-policy-key"
        f" -k {root_keys_store['R1']['private']}"
        f" --policy-key {policy_keys_store['P3']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf trust update-policy-threshold"
        f" -k {root_keys_store['R1']['private']}"
        " --threshold 2"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R2']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R3']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf trust apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Initialize policy file and add policy keys and sign-off
    prompt_key(automatic, "Add policy keys and sign-off")
    cmd = (
        "gittuf policy init"
        f" -k {policy_keys_store['P1']['private']}"
        " --policy-name targets"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {policy_keys_store['P1']['private']}"
        f" --public-key {people_keys_store['Alice']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {policy_keys_store['P1']['private']}"
        f" --public-key {people_keys_store['Bob']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {policy_keys_store['P1']['private']}"
        f" --public-key {people_keys_store['Carol']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {policy_keys_store['P1']['private']}"
        f" --public-key {people_keys_store['Helen']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {policy_keys_store['P1']['private']}"
        f" --public-key {people_keys_store['Ilda']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

   # Add rules and sign-off
    prompt_key(automatic, "Add rules and sign-off")
    cmd = (
        "gittuf policy add-rule"
        f" -k {policy_keys_store['P1']['private']}"
        " --rule-name protect-main-prod"
        " --rule-pattern git:refs/heads/main"
        " --rule-pattern git:refs/heads/prod"
        f" --authorize-key {people_keys_store['Alice']['public']}"
        f" --authorize-key {people_keys_store['Bob']['public']}"
        f" --authorize-key {people_keys_store['Carol']['public']}"
        " --threshold 2"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-rule"
        f" -k {policy_keys_store['P1']['private']}"
        " --rule-name protect-ios-app"
        " --rule-pattern file:ios/*"
        f" --authorize-key {people_keys_store['Alice']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-rule"
        f" -k {policy_keys_store['P1']['private']}"
        " --rule-name protect-android-app"
        " --rule-pattern file:android/*"
        f" --authorize-key {people_keys_store['Bob']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-rule"
        f" -k {policy_keys_store['P1']['private']}"
        " --rule-name protect-core-libraries"
        " --rule-pattern file:src/*"
        f" --authorize-key {people_keys_store['Carol']['public']}"
        f" --authorize-key {people_keys_store['Helen']['public']}"
        f" --authorize-key {people_keys_store['Ilda']['public']}"
        " --threshold 2"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy sign"
        f" -k {policy_keys_store['P1']['private']}"
        " --policy-name targets"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy sign"
        f" -k {policy_keys_store['P2']['private']}"
        " --policy-name targets"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Create folders and add initial git commit
    prompt_key(automatic, "Create folders and add initial git commit")
    cmd = "echo \"Hello, world!\" > README.md"
    display_command(cmd)

    subprocess.call(cmd, shell=True)

    cmd = "mkdir src ios android"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git add README.md"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git commit -q -S -m 'Initial commit'"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "git branch -q prod"
    display_command(cmd)
    run_command(cmd, 0)

    # Add delegated policy protect-ios-app
    prompt_key(automatic, "Add delegated policy protect-ios-app")
    cmd = (
        "gittuf policy init"
        f" -k {policy_keys_store['P3']['private']}"
        " --policy-name protect-ios-app"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {people_keys_store['Alice']['private']}"
        " --policy-name protect-ios-app"
        f" --public-key {people_keys_store['Dana']['public']}"
        f" --public-key {people_keys_store['George']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    # Add rule for protect-ios-app
    prompt_key(automatic, "Add rule for protect-ios-app")
    cmd = (
        "gittuf policy add-rule"
        f" -k {people_keys_store['Alice']['private']}"
        " --policy-name protect-ios-app"
        " --rule-name authorize-ios-team"
        " --rule-pattern file:ios/*"
        f" --authorize-key {people_keys_store['Dana']['public']}"
        f" --authorize-key {people_keys_store['George']['public']}"
        " --threshold 1"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy sign"
        f" -k {people_keys_store['Alice']['private']}"
        " --policy-name protect-ios-app"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Add delegated policy protect-android-app
    prompt_key(automatic, "Add delegated policy protect-android-app")
    cmd = (
        "gittuf policy init"
        f" -k {policy_keys_store['P3']['private']}"
        " --policy-name protect-android-app"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy add-key"
        f" -k {people_keys_store['Bob']['private']}"
        " --policy-name protect-android-app"
        f" --public-key {people_keys_store['Eric']['public']}"
        f" --public-key {people_keys_store['Frank']['public']}"
    )
    display_command(cmd)
    run_command(cmd, 0)

    # Add rule for protect-android-app
    prompt_key(automatic, "Add rule for protect-android-app")
    cmd = (
        "gittuf policy add-rule"
        f" -k {people_keys_store['Bob']['private']}"
        " --policy-name protect-android-app"
        " --rule-name authorize-android-team"
        " --rule-pattern file:android/*"
        f" --authorize-key {people_keys_store['Eric']['public']}"
        f" --authorize-key {people_keys_store['Frank']['public']}"
        " --threshold 1"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = (
        "gittuf policy sign"
        f" -k {people_keys_store['Bob']['private']}"
        " --policy-name protect-android-app"
    )
    display_command(cmd)
    run_command(cmd, 0)

    cmd = "gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Verify policy 
    prompt_key(automatic, "Verify policy")
    cmd = "gittuf --verbose verify-ref refs/gittuf/policy"
    display_command(cmd)
    run_command(cmd, 0)

    # Show final policy state 
    prompt_key(automatic, "Final policy state")
    cmd = "gittuf policy list-rules"
    display_command(cmd)
    run_command(cmd, 0)

if __name__ == "__main__":
    check_binaries(REQUIRED_BINARIES)
    deployment()  # pylint: disable=no-value-for-parameter

