import os
import tempfile
import click
import subprocess

from utils import prompt_key, display_command, run_command, check_binaries, print_section

REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]

REPOSITORY_STEPS = 3  # All of Aditya's examples have 3 steps
GITTUF_STEPS = 11  # There's no demo of what goes wrong currently

@click.command()
@click.option(
    "--automatic", default=False, type=bool, is_flag=True,
    help="Whether to wait for input before each command is run."
)
@click.option(
    "--repository-directory", default="",
    help="The path where the script should store the working copy of the repository."
)

def experiment1(automatic, repository_directory):
    print("...")

    # OS SETUP
    print_section("Background setup...")

    # Set up directory structure and keys
    current_dir = os.getcwd()
    root_keys_dir = "keys/roots"
    policy_keys_dir = "keys/policy"
    people_keys_dir = "keys/people"

    # Select folder for the working repository copy
    working_dir = repository_directory
    if working_dir == "":
        tmp_dir = tempfile.TemporaryDirectory()
        working_dir = tmp_dir.name
    else:
        working_dir = os.path.abspath(repository_directory)

    # Sort key paths into hash for convenient storage  
    def generate_key_hash_store(directory):
        return {
            key.split('.')[0]: {
                "private": os.path.join(directory, key),
                "public": os.path.join(directory, f"{key}.pub")
            }
            for key in os.listdir(directory) if not key.endswith('.pub')
        }

    root_keys_store = generate_key_hash_store(root_keys_dir)  # For R1, R2, R3
    policy_keys_store = generate_key_hash_store(policy_keys_dir)  # For P1, P2, P3
    people_keys_store = generate_key_hash_store(people_keys_dir)  # For Alice, Bob, Carol, etc.

    # REPOSITORY SETUP
    print_section("[1 / 2] Repository Setup")

    # Initialize the Git repository in the chosen directory
    step = 1
    step = prompt_key(automatic, step, REPOSITORY_STEPS, "Initialize Git repository")
    cmd = "git init -b main"
    display_command(cmd)
    run_command(cmd, 0)

    # Set repo config
    step = prompt_key(automatic, step, REPOSITORY_STEPS, "Set repo config to use demo identity and test key")
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

    step = prompt_key(automatic, step, REPOSITORY_STEPS, "Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command("export PAGER=cat")

    # GITTUF STEPS
    print_section("[2 / 2] Gittuf Example")

    # Step 1: Initialize roots of trust
    step = 1
    step = prompt_key(automatic, step, GITTUF_STEPS, "Initialize gittuf root of trust")
    cmd = f"gittuf trust init -k {root_keys_store['R1']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust add-root-key -k {root_keys_store['R1']['private']} --root-key {root_keys_store['R2']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust add-root-key -k {root_keys_store['R1']['private']} --root-key {root_keys_store['R3']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust update-root-threshold -k {root_keys_store['R1']['private']} --threshold 2"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R2']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R3']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 2: Initialize top-level policy keys
    step = prompt_key(automatic, step, GITTUF_STEPS, "Initialize top-level policy keys")
    cmd = f"gittuf trust add-policy-key -k {root_keys_store['R1']['private']} --policy-key {policy_keys_store['P1']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust add-policy-key -k {root_keys_store['R1']['private']} --policy-key {policy_keys_store['P2']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust add-policy-key -k {root_keys_store['R1']['private']} --policy-key {policy_keys_store['P3']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust update-policy-threshold -k {root_keys_store['R1']['private']} --threshold 2"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R2']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust sign -k {root_keys_store['R3']['private']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf trust apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 3: Create folders and add initial git commit
    step = prompt_key(automatic, step, GITTUF_STEPS, "Create folders and add initial git commit")
    cmd = f'echo "Hello, world!" > README.md'
    display_command(cmd)

    # call subprocess directly instead of using run_command
    # cmd string needs to be not parse and shell true in order to
    # handle using the redirect, >, to write to a file 
    subprocess.call(cmd, shell=True) 

    cmd = f"mkdir src ios android"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"git add README.md"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"git commit -q -S -m 'Initial commit'"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"git branch -q prod"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 4: initialize policy file and add policy keys and sign-off
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add policy keys and sign-off")
    cmd = f"gittuf policy init -k {policy_keys_store['P1']['private']} --policy-name targets"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {policy_keys_store['P1']['private']} --public-key {people_keys_store['Alice']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {policy_keys_store['P1']['private']} --public-key {people_keys_store['Bob']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {policy_keys_store['P1']['private']} --public-key {people_keys_store['Carol']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {policy_keys_store['P1']['private']} --public-key {people_keys_store['Helen']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {policy_keys_store['P1']['private']} --public-key {people_keys_store['Ilda']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 5: Add rules and sign-off
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add rules and sign-off")
    cmd = f"gittuf policy add-rule -k {policy_keys_store['P1']['private']} --rule-name protect-main-prod --rule-pattern git:refs/heads/main --rule-pattern git:refs/heads/prod --authorize-key {people_keys_store['Alice']['public']} --authorize-key {people_keys_store['Bob']['public']} --authorize-key {people_keys_store['Carol']['public']} --threshold 2"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-rule -k {policy_keys_store['P1']['private']} --rule-name protect-ios-app --rule-pattern file:ios/* --authorize-key {people_keys_store['Alice']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-rule -k {policy_keys_store['P1']['private']} --rule-name protect-android-app --rule-pattern file:android/* --authorize-key {people_keys_store['Bob']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-rule -k {policy_keys_store['P1']['private']} --rule-name protect-core-libraries --rule-pattern file:src/* --authorize-key {people_keys_store['Carol']['public']} --authorize-key {people_keys_store['Helen']['public']} --authorize-key {people_keys_store['Ilda']['public']} --threshold 2"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy sign -k {policy_keys_store['P1']['private']} --policy-name targets"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy sign -k {policy_keys_store['P2']['private']} --policy-name targets"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 6: Add delegated policy protect-ios-app
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add delegated policy protect-ios-app")
    cmd = f"gittuf policy init -k {policy_keys_store['P3']['private']} --policy-name protect-ios-app"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {people_keys_store['Alice']['private']} --policy-name protect-ios-app --public-key {people_keys_store['Dana']['public']} --public-key {people_keys_store['George']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 7: Add rule for protect-ios-app
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add rule for protect-ios-app")
    cmd = f"gittuf policy add-rule -k {people_keys_store['Alice']['private']} --policy-name protect-ios-app --rule-name authorize-ios-team --rule-pattern file:ios/* --authorize-key {people_keys_store['Dana']['public']} --authorize-key {people_keys_store['George']['public']} --threshold 1"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy sign -k {people_keys_store['Alice']['private']} --policy-name protect-ios-app"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 8: Add delegated policy protect-android-app
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add delegated policy protect-android-app")
    cmd = f"gittuf policy init -k {policy_keys_store['P3']['private']} --policy-name protect-android-app"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy add-key -k {people_keys_store['Bob']['private']} --policy-name protect-android-app --public-key {people_keys_store['Eric']['public']} --public-key {people_keys_store['Frank']['public']}"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 9: Add rule for protect-android-app
    step = prompt_key(automatic, step, GITTUF_STEPS, "Add rule for protect-android-app")
    cmd = f"gittuf policy add-rule -k {people_keys_store['Bob']['private']} --policy-name protect-android-app --rule-name authorize-android-team --rule-pattern file:android/* --authorize-key {people_keys_store['Eric']['public']} --authorize-key {people_keys_store['Frank']['public']} --threshold 1"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy sign -k {people_keys_store['Bob']['private']} --policy-name protect-android-app"
    display_command(cmd)
    run_command(cmd, 0)

    cmd = f"gittuf policy apply"
    display_command(cmd)
    run_command(cmd, 0)

    # Step 10: Verify policy 
    step = prompt_key(automatic, step, GITTUF_STEPS, "Verify policy")
    cmd = f"gittuf --verbose verify-ref refs/gittuf/policy"
    display_command(cmd)
    run_command(cmd, 0)
    
    # Step 11: Show final policy state 
    step = prompt_key(automatic, step, GITTUF_STEPS, "Final policy state")
    cmd = f"gittuf policy list-rules"
    display_command(cmd)
    run_command(cmd, 0)

if __name__ == "__main__":
    check_binaries(REQUIRED_BINARIES)
    experiment1()  # pylint: disable=no-value-for-parameter
