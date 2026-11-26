#!/usr/bin/env python

import os
import shlex
import shutil
import subprocess
import tempfile

from demo_utils import check_binaries, display_command, prompt_key, run_command

REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen", "gpg"]
KEYS = ["root", "root2", "policy", "policy2", "alice", "alice-ed25519", "bob", "carol", "dave", "erin", "pop", "mallory"]
TMP_DIR = None


def print_section(text):
    """Prints the needed amount of dashes for each section heading"""
    print('\n' + text + ' ' + ('-' * (80 - len(text))))


def setup_repo(name, persons, signer="alice"):
    prompt_key(f"Create repository {name}: root of trust, policy key, persons {', '.join(persons)}, no rules")
    os.chdir(TMP_DIR)
    display_command(f"mkdir {name} && cd {name}")
    os.mkdir(name)
    os.chdir(name)

    cmds = [
        "git init -b main",
        "git config --local gpg.format ssh",
        "git config --local commit.gpgsign true",
        f"git config --local user.signingkey ../keys/{signer}",
        "git config --local user.name gittuf-demo",
        "git config --local user.email gittuf.demo@example.com",
        "gittuf trust init -k ../keys/root",
        "gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/policy.pub",
        "gittuf policy init -k ../keys/policy",
    ]
    for person in persons:
        cmds.append(
            f"gittuf policy add-person -k ../keys/policy --person-ID {person} --public-key ../keys/{person}.pub"
        )
    cmds += [
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-principals",
    ]
    for cmd in cmds:
        display_command(cmd)
        run_command(cmd)


def scenario_1():
    print_section("SCENARIO 1")

    prompt_key("SCENARIO 1: SSH and GPG signatures count toward the same threshold")

    prompt_key("Create a throwaway GPG key for Dana")
    gnupg_home = tempfile.mkdtemp(prefix="gtg-", dir="/tmp")
    os.environ["GNUPGHOME"] = gnupg_home
    display_command(f"export GNUPGHOME={gnupg_home}")
    cmd = (
        "gpg --batch --pinentry-mode loopback --passphrase ''"
        " --quick-generate-key 'Dana <dana@example.com>' rsa3072 sign never"
    )
    display_command(cmd)
    run_command(cmd)
    cmd = "gpg --batch --with-colons --list-secret-keys dana@example.com"
    display_command(cmd)
    listing = subprocess.check_output(shlex.split(cmd)).decode()
    dana = [line for line in listing.splitlines() if line.startswith("fpr:")][0].split(":")[9]
    display_command(f"# Dana's fingerprint: {dana}")

    setup_repo("s01-ssh-and-gpg", ["bob"], signer="bob")

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Add Dana (GPG key) and a rule: main needs 2 of {Bob, Dana}")
    for cmd in [
        f"gittuf policy add-person -k ../keys/policy --person-ID dana --public-key gpg:{dana}",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize bob --authorize dana --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-principals",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Dana approves with GPG, Bob merges and signs the RSL entry with SSH")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Feature by Bob' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("Feature by Bob\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Add feature (Bob)'",
        "gittuf rsl record feature --local-only",
        f"gittuf attest authorize -k gpg:{dana} --from-ref feature --create-rsl-entry main",
        "git checkout main",
        "git merge --ff-only feature",
        "gittuf rsl record main --local-only",
        "gittuf verify-ref main",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key("Verification succeeded: SSH RSL entry + GPG approval = 2 of 2")

    prompt_key("Bob approves with SSH, Dana merges and signs the RSL entry with GPG")
    cmd = "git checkout -b feature-2"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'More from Bob' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("More from Bob\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Extend feature (Bob)'",
        "gittuf rsl record feature-2 --local-only",
        "gittuf attest authorize -k ../keys/bob --from-ref feature-2 --create-rsl-entry main",
        "git checkout main",
        "git merge --ff-only feature-2",
        "git config --local gpg.format openpgp",
        f"git config --local user.signingkey {dana}",
        "gittuf rsl record main --local-only",
        "git cat-file -p refs/gittuf/reference-state-log",
        "gittuf verify-ref main",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key("Verification succeeded: GPG RSL entry + SSH approval = 2 of 2")

    if shutil.which("gpgconf"):
        subprocess.call(["gpgconf", "--kill", "gpg-agent"])
    shutil.rmtree(gnupg_home, ignore_errors=True)


def scenario_2():
    print_section("SCENARIO 2")

    prompt_key("SCENARIO 2: overlapping file rules, any matching rule is enough")
    setup_repo("s02-overlapping-file-rules", ["alice", "bob", "pop"])

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Add rules: .github/* needs Pop (1); .github/doc/* needs 2 of {Alice, Bob}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-github"
        " --rule-pattern 'file:.github/*' --authorize pop --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-github-docs"
        " --rule-pattern 'file:.github/doc/*' --authorize alice --authorize bob --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Pop signs a commit to .github/doc/guide.md and its RSL entry, with no approvals")
    cmd = "git config --local user.signingkey ../keys/pop"
    display_command(cmd)
    run_command(cmd)
    display_command("mkdir -p .github/doc && echo 'Notes by Pop' >> .github/doc/guide.md")
    os.makedirs(".github/doc", exist_ok=True)
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Notes by Pop\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Edit docs guide (Pop)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key(
        "Verification succeeded: Pop alone can change .github/doc/* because protect-github"
        " (.github/*) also matches it; protect-github-docs is not required"
    )

    prompt_key("Alice signs a commit to .github/doc/guide.md, Pop signs only the RSL entry")
    cmd = "git config --local user.signingkey ../keys/alice"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Guide by Alice' >> .github/doc/guide.md")
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Guide by Alice\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Add docs guide (Alice)'",
        "git config --local user.signingkey ../keys/pop",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key(
        "gittuf detected the violation: file rules check the commit, not the RSL entry."
        " protect-github sees no signature from Pop; protect-github-docs sees 1 of 2"
    )

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
        "git config --local user.signingkey ../keys/alice",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice signs the same change on a feature branch; Pop approves it; Bob does not")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("mkdir -p .github/doc && echo 'Guide by Alice' >> .github/doc/guide.md")
    os.makedirs(".github/doc", exist_ok=True)
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Guide by Alice\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Add docs guide (Alice)'",
        "gittuf rsl record feature --local-only",
        "gittuf attest authorize -k ../keys/pop --from-ref feature --create-rsl-entry main",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
        "git checkout main",
        "git merge --ff-only feature",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key(
        "Verification succeeded: Pop's approval meets protect-github, so the change passes"
        " although protect-github-docs (2 of Alice, Bob) is not met"
    )


def scenario_3():
    print_section("SCENARIO 3")

    prompt_key("SCENARIO 3: flipped overlapping file rules (Scenario 2) with a branch rule")
    setup_repo("s03-flipped-overlap", ["alice", "bob", "pop"])

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Add rules: main needs 1 of {Alice, Bob, Pop}; .github/doc/* needs Pop (1); .github/* needs 2 of {Alice, Bob}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --authorize pop --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-github-docs"
        " --rule-pattern 'file:.github/doc/*' --authorize pop --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-github"
        " --rule-pattern 'file:.github/*' --authorize alice --authorize bob --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Pop commits to .github/doc/guide.md, signs commit and RSL entry")
    cmd = "git config --local user.signingkey ../keys/pop"
    display_command(cmd)
    run_command(cmd)
    display_command("mkdir -p .github/doc && echo 'Notes by Pop' >> .github/doc/guide.md")
    os.makedirs(".github/doc", exist_ok=True)
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Notes by Pop\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Edit docs guide (Pop)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key(
        "Verification succeeded: protect-github-docs (Pop, 1 of 1) is met;"
        " protect-github (Alice+Bob, 2) is not needed"
    )

    prompt_key("Pop commits to .github/ci.yml (outside doc/), signs commit and RSL entry")
    display_command("mkdir -p .github && echo 'steps: []' >> .github/ci.yml")
    os.makedirs(".github", exist_ok=True)
    with open(".github/ci.yml", "a") as fp:
        fp.write("steps: []\n")
    for cmd in [
        "git add .github/ci.yml",
        "git commit -m 'Edit CI (Pop)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key(
        "gittuf detected the violation: .github/ci.yml matches only protect-github"
        " (2 of Alice, Bob); Pop is not in that rule"
    )

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice commits to .github/doc/guide.md, signs commit and RSL entry")
    cmd = "git config --local user.signingkey ../keys/alice"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Guide by Alice' >> .github/doc/guide.md")
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Guide by Alice\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Add docs guide (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key(
        "gittuf detected the violation: protect-github-docs needs Pop, not Alice;"
        " protect-github needs 2 of {Alice, Bob}, Alice is only 1"
    )

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice commits to .github/doc/guide.md on a feature branch; Bob approves; Alice merges")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Guide by Alice' >> .github/doc/guide.md")
    with open(".github/doc/guide.md", "a") as fp:
        fp.write("Guide by Alice\n")
    for cmd in [
        "git add .github/doc/guide.md",
        "git commit -m 'Add docs guide (Alice)'",
        "gittuf rsl record feature --local-only",
        "gittuf attest authorize -k ../keys/bob --from-ref feature --create-rsl-entry main",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
        "git checkout main",
        "git merge --ff-only feature",
        "git config --local user.signingkey ../keys/alice",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key(
        "Verification succeeded: protect-github (2 of Alice, Bob) is met via"
        " Alice's commit + Bob's approval; protect-github-docs (Pop) is not needed"
    )


def scenario_4():
    print_section("SCENARIO 4")

    prompt_key("SCENARIO 4: delegated rule files must be signed by the delegating rule's principals")
    setup_repo("s04-delegations", ["alice", "bob"])

    prompt_key("Add rule: main needs 2 of {Alice, Bob}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice creates rule file protect-main, delegating main to Dave and Erin (1 of 2)")
    for cmd in [
        "gittuf policy init -k ../keys/alice --policy-name protect-main",
        "gittuf policy add-person -k ../keys/alice --policy-name protect-main"
        " --person-ID dave --public-key ../keys/dave.pub",
        "gittuf policy add-person -k ../keys/alice --policy-name protect-main"
        " --person-ID erin --public-key ../keys/erin.pub",
        "gittuf policy add-rule -k ../keys/alice --policy-name protect-main --rule-name main-developers"
        " --rule-pattern git:refs/heads/main --authorize dave --authorize erin --threshold 1",
        "gittuf policy stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: rule file protect-main has 1 of 2 required signatures")

    prompt_key("Bob co-signs rule file protect-main")
    for cmd in [
        "gittuf policy sign -k ../keys/bob --policy-name protect-main",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Dave signs a commit and the RSL entry for main")
    cmd = "git config --local user.signingkey ../keys/dave"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Change by Dave' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Dave\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Dave)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: protect-main is not met, but the delegated rule main-developers is")

    prompt_key("Mallory signs a commit and the RSL entry for main")
    cmd = "git config --local user.signingkey ../keys/mallory"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Change by Mallory' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Mallory\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Mallory)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: no matching rule trusts Mallory")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Dave tries to add Mallory to rule file protect-main, signing it himself")
    for cmd in [
        "git config --local user.signingkey ../keys/dave",
        "gittuf policy add-person -k ../keys/dave --policy-name protect-main"
        " --person-ID mallory --public-key ../keys/mallory.pub",
        "gittuf policy update-rule -k ../keys/dave --policy-name protect-main --rule-name main-developers"
        " --rule-pattern git:refs/heads/main --authorize dave --authorize erin --authorize mallory --threshold 1",
        "gittuf policy stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: Dave cannot sign rule file protect-main")

    prompt_key("Discard the rejected change and verify main")
    for cmd in [
        "gittuf policy discard",
        "gittuf verify-ref main",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key("Verification succeeded: the rejected policy was never applied")


def scenario_5():
    print_section("SCENARIO 5")

    prompt_key("SCENARIO 5: overlapping rules are alternatives, global rules are mandatory")
    setup_repo("s05-global-rules", ["alice", "bob", "carol"])

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Add rules: any branch needs Alice; main needs 2 of {Bob, Carol}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name any-branch"
        " --rule-pattern 'git:refs/heads/*' --authorize alice --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize bob --authorize carol --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice starts a feature branch, then updates main on her own")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Feature by Alice' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("Feature by Alice\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Add feature (Alice)'",
        "gittuf rsl record feature --local-only",
        "git checkout main",
    ]:
        display_command(cmd)
        run_command(cmd)
    display_command("echo 'Change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: any-branch is met, so protect-main is not required")

    prompt_key("Add a global rule: main needs 2 signers")
    for cmd in [
        "gittuf trust add-global-rule -k ../keys/root --rule-name main-two-signers"
        " --type threshold --rule-pattern git:refs/heads/main --threshold 2",
        "gittuf trust stage --local-only",
        "gittuf trust apply --local-only",
        "gittuf trust list-global-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice updates main on her own again")
    display_command("echo 'Second change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Second change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README again (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: any-branch is met, but the global rule sees 1 of 2")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Carol approves merging the diverged feature branch; Alice merges with a merge commit")
    for cmd in [
        "gittuf attest authorize -k ../keys/carol --from-ref feature --create-rsl-entry main",
        "git merge --no-ff -m 'Merge feature' feature",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key(
        "Verification succeeded: any-branch is met, the global rule sees Alice + Carol,"
        " and the merge commit's tree matches the tree Carol approved"
    )

    prompt_key("Add a global rule blocking force pushes on dev, then make two normal updates to dev")
    for cmd in [
        "gittuf trust add-global-rule -k ../keys/root --rule-name dev-no-force-push"
        " --type block-force-pushes --rule-pattern git:refs/heads/dev",
        "gittuf trust stage --local-only",
        "gittuf trust apply --local-only",
        "git checkout -b dev",
    ]:
        display_command(cmd)
        run_command(cmd)
    for line in ["Dev work 1", "Dev work 2"]:
        display_command(f"echo '{line}' >> dev.txt")
        with open("dev.txt", "a") as fp:
            fp.write(line + "\n")
        for cmd in [
            "git add dev.txt",
            f"git commit -m '{line}'",
            "gittuf rsl record dev --local-only",
        ]:
            display_command(cmd)
            run_command(cmd)

    prompt_key("Verify dev")
    cmd = "gittuf verify-ref dev"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: each entry descends from the previous one")

    prompt_key("Alice rewrites the last dev commit and records it")
    for cmd in [
        "git commit --amend -m 'Dev work 2, rewritten'",
        "gittuf rsl record dev --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify dev")
    cmd = "gittuf verify-ref dev"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the force push")


def scenario_6():
    print_section("SCENARIO 6")

    prompt_key("SCENARIO 6: thresholds that can never be met")
    setup_repo("s06-unmeetable-thresholds", ["alice", "bob"])

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Register Alice's second key: 3 keys, 2 principals")
    for cmd in [
        "gittuf policy update-person -k ../keys/policy --person-ID alice"
        " --public-key ../keys/alice.pub --public-key ../keys/alice-ed25519.pub",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-principals",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Try rules that cannot be met: threshold 3 with 2 principals, Alice listed twice, threshold 0")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --threshold 3",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize alice --threshold 2",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --threshold 0",
    ]:
        display_command(cmd)
        run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected all three rules when they were written")

    prompt_key("Add a valid 2-of-2 rule, then try to raise it to 3")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = (
        "gittuf policy update-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --threshold 3"
    )
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the update for the same reason")

    prompt_key("Add a global rule: main needs 3 signers (not checked against principals when written)")
    for cmd in [
        "gittuf trust add-global-rule -k ../keys/root --rule-name main-needs-three"
        " --type threshold --rule-pattern git:refs/heads/main --threshold 3",
        "gittuf trust stage --local-only",
        "gittuf trust apply --local-only",
        "gittuf trust list-global-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice makes a feature change, Bob approves, Alice merges and signs the RSL entry")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Feature by Alice' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("Feature by Alice\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Add feature (Alice)'",
        "gittuf rsl record feature --local-only",
        "gittuf attest authorize -k ../keys/bob --from-ref feature --create-rsl-entry main",
        "git checkout main",
        "git merge --ff-only feature",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: protect-main is met, but the global rule sees 2 of 3")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Add Carol to the policy (not to protect-main); Carol approves; Alice merges again")
    for cmd in [
        "gittuf policy add-person -k ../keys/policy --person-ID carol --public-key ../keys/carol.pub",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf attest authorize -k ../keys/carol --from-ref feature --create-rsl-entry main",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
        "git merge --ff-only feature",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: global rules count every principal in the policy (Alice, Bob, Carol)")


def scenario_7():
    print_section("SCENARIO 7")

    prompt_key("SCENARIO 7: one person meets a threshold of 2 when his/her keys are also registered as key principals")
    setup_repo("s07-key-reuse", ["alice"], signer="alice")

    prompt_key("Initial commit on main, recorded before any rule exists (the feature branch is created from main)")
    display_command("echo 'Hello, world!' > README.md")
    with open("README.md", "w") as fp:
        fp.write("Hello, world!\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Initial commit'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Look up the IDs of Alice's two keys")
    cmd = "ssh-keygen -E sha256 -lf ../keys/alice.pub"
    display_command(cmd)
    alice_1_id = subprocess.check_output(shlex.split(cmd)).decode().split()[1]
    cmd = "ssh-keygen -E sha256 -lf ../keys/alice-ed25519.pub"
    display_command(cmd)
    alice_2_id = subprocess.check_output(shlex.split(cmd)).decode().split()[1]
    print(f"key1 = {alice_1_id}")
    print(f"key2 = {alice_2_id}")

    prompt_key("Add Alice as one person holding both keys")
    for cmd in [
        "gittuf policy update-person -k ../keys/policy --person-ID alice"
        " --public-key ../keys/alice.pub --public-key ../keys/alice-ed25519.pub",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-principals",
    ]:
        display_command(cmd)
        run_command(cmd)
    print("\nPolicy now has 1 principal:")
    print(f"  alice -> keys: {alice_1_id}, {alice_2_id}")

    prompt_key("Register the same two keys again as standalone key principals")
    for cmd in [
        "gittuf policy add-key -k ../keys/policy --public-key ../keys/alice.pub --public-key ../keys/alice-ed25519.pub",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-principals",
    ]:
        display_command(cmd)
        run_command(cmd)
    print("\nPolicy now has 3 principals, and each key appears twice:")
    print(f"  alice -> keys: {alice_1_id}, {alice_2_id}")
    print(f"  {alice_1_id} -> keys: {alice_1_id}")
    print(f"  {alice_2_id} -> keys: {alice_2_id}")

    prompt_key("Add rule: main needs 2 of {key1, key2}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        f" --rule-pattern git:refs/heads/main --authorize {alice_1_id} --authorize {alice_2_id} --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)
    print("\ngittuf accepted the rule: it sees 2 distinct principal IDs for threshold 2")

    prompt_key("Alice alone commits on feature (signed with key1)")
    cmd = "git checkout -b feature"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Feature by Alice' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("Feature by Alice\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Add feature (Alice)'",
        "gittuf rsl record feature --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice approves merging feature into main (signed with key2)")
    for cmd in [
        "gittuf attest authorize -k ../keys/alice-ed25519 --from-ref feature --create-rsl-entry main",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
    ]:
        display_command(cmd)
        run_command(cmd)
    print(f"\nApproval signed with key2: {alice_2_id}")

    prompt_key("Alice merges into main and signs the RSL entry (signed with key1)")
    for cmd in [
        "git checkout main",
        "git merge --ff-only feature",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    print(f"\nRSL entry signed with key1: {alice_1_id}")

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    print("\nHow gittuf counted toward protect-main (threshold 2):")
    print(f"  RSL entry -> principal {alice_1_id} (1)")
    print(f"  approval  -> principal {alice_2_id} (2)")
    print("  humans involved: 1 (Alice)")
    prompt_key("Verification succeeded: gittuf counts two key principals (2 of 2), although one person signed both")


def scenario_8():
    print_section("SCENARIO 8")

    prompt_key("SCENARIO 8: signature thresholds on the root of trust and the primary rule file")
    setup_repo("s08-metadata-thresholds", ["alice"])

    prompt_key("Add rule: main needs Alice")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --threshold 1",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Require 2 of {policy, policy2} to sign the primary rule file")
    for cmd in [
        "gittuf trust add-policy-key -k ../keys/root --policy-key ../keys/policy2.pub",
        "gittuf trust update-policy-threshold -k ../keys/root --threshold 2",
        "gittuf trust stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf trust apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: the primary rule file has 1 of 2 policy signatures")

    prompt_key("policy2 co-signs the primary rule file")
    for cmd in [
        "gittuf policy sign -k ../keys/policy2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf trust inspect-root",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Any later rule file change needs both policy keys again: add Bob, signed by policy only")
    for cmd in [
        "gittuf policy add-person -k ../keys/policy --person-ID bob --public-key ../keys/bob.pub",
        "gittuf policy stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf policy apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: the edit replaced the rule file's signatures with one")

    prompt_key("policy2 co-signs again")
    for cmd in [
        "gittuf policy sign -k ../keys/policy2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("A policy key tries to change the root of trust")
    cmd = (
        "gittuf trust add-global-rule -k ../keys/policy --rule-name main-no-force-push"
        " --type block-force-pushes --rule-pattern git:refs/heads/main"
    )
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the change: only root keys can sign the root of trust")

    prompt_key("Require 2 of {root, root2} to sign the root of trust")
    for cmd in [
        "gittuf trust add-root-key -k ../keys/root --root-key ../keys/root2.pub",
        "gittuf trust update-root-threshold -k ../keys/root --threshold 2",
        "gittuf trust stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf trust apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: the new root has 1 of 2 root signatures")

    prompt_key("root2 co-signs the root of trust")
    for cmd in [
        "gittuf trust sign -k ../keys/root2",
        "gittuf trust stage --local-only",
        "gittuf trust apply --local-only",
        "gittuf trust inspect-root",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Next root change, signed by root only")
    for cmd in [
        "gittuf trust add-global-rule -k ../keys/root --rule-name main-no-force-push"
        " --type block-force-pushes --rule-pattern git:refs/heads/main",
        "gittuf trust stage --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf trust apply --local-only"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf rejected the policy: the current root requires 2 signatures on the next root")

    prompt_key("root2 co-signs")
    for cmd in [
        "gittuf trust sign -k ../keys/root2",
        "gittuf trust stage --local-only",
        "gittuf trust apply --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice updates main")
    display_command("echo 'Change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: every applied policy change checks out against the previous one")


def scenario_9():
    print_section("SCENARIO 9")

    prompt_key("SCENARIO 9: full history, --latest-only, recovery with annotations, policy rollback")
    setup_repo("s09-rsl-history", ["alice"])

    prompt_key("Add rule: main needs Alice")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --threshold 1",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice updates main")
    display_command("echo 'Change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Alice)'",
        "gittuf rsl record main --local-only",
        "gittuf verify-ref main",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Mallory updates main")
    cmd = "git config --local user.signingkey ../keys/mallory"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Change by Mallory' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Mallory\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Mallory)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    bad_entry = subprocess.check_output(
        shlex.split("git rev-parse refs/gittuf/reference-state-log")
    ).decode().strip()
    display_command(f"# Mallory's RSL entry: {bad_entry}")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation")

    prompt_key("Alice commits on top without noticing")
    cmd = "git config --local user.signingkey ../keys/alice"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Changelog by Alice' >> CHANGELOG.md")
    with open("CHANGELOG.md", "a") as fp:
        fp.write("Changelog by Alice\n")
    for cmd in [
        "git add CHANGELOG.md",
        "git commit -m 'Add changelog (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)
    dependent_entry = subprocess.check_output(
        shlex.split("git rev-parse refs/gittuf/reference-state-log")
    ).decode().strip()
    display_command(f"# Alice's dependent RSL entry: {dependent_entry}")

    prompt_key("Verify only the latest entry, then the full history")
    cmd = "gittuf verify-ref --latest-only main"
    display_command(cmd)
    run_command(cmd)
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("--latest-only passed, but the full history still contains Mallory's entry")

    prompt_key("Skip Mallory's entry and record a fix that restores the last good tree")
    for cmd in [
        f"gittuf rsl annotate --skip --local-only -m 'Unauthorized change' {bad_entry}",
        "git revert --no-edit HEAD~2..HEAD",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("Still failing: Alice's entry between the violation and the fix is not skipped")

    prompt_key("Skip Alice's dependent entry too")
    for cmd in [
        f"gittuf rsl annotate --skip --local-only -m 'Built on an unauthorized change' {dependent_entry}",
        "gittuf verify-ref main",
        "gittuf rsl log --ref main",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key("Verification succeeded: the history is recovered")

    prompt_key("Record an older policy in the RSL (rollback), then update main")
    policy_head = subprocess.check_output(
        shlex.split("git rev-parse refs/gittuf/policy")
    ).decode().strip()
    display_command(f"# current policy: {policy_head}")
    for cmd in [
        "git update-ref refs/gittuf/policy refs/gittuf/policy~1",
        "gittuf rsl record refs/gittuf/policy --local-only",
        f"git update-ref refs/gittuf/policy {policy_head}",
    ]:
        display_command(cmd)
        run_command(cmd)
    display_command("echo 'Change after rollback' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change after rollback\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README after rollback (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the policy rollback")


def run_demo():
    global TMP_DIR
    current_dir = os.getcwd()
    tmp_dir = tempfile.TemporaryDirectory()
    TMP_DIR = tmp_dir.name
    os.chdir(TMP_DIR)

    prompt_key("Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command("export PAGER=cat")

    prompt_key("Generate SSH signing keys")
    os.mkdir("keys")
    for key in KEYS:
        key_type = "ed25519" if key == "alice-ed25519" else "ecdsa"
        cmd = f"ssh-keygen -q -t {key_type} -N '' -C {key} -f keys/{key}"
        display_command(cmd)
        run_command(cmd)

    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    scenario_5()
    scenario_6()
    scenario_7()
    scenario_8()
    scenario_9()

    os.chdir(current_dir)
    prompt_key("Policy demo complete!")


if __name__ == "__main__":
    check_binaries(REQUIRED_BINARIES)
    run_demo()
