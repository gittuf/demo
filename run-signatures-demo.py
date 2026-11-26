#!/usr/bin/env python

import os
import tempfile

from demo_utils import check_binaries, display_command, prompt_key, run_command

REQUIRED_BINARIES = ["git", "gittuf", "ssh-keygen"]

KEYS = ["root", "policy", "alice", "bob", "carol", "dave", "mallory"]
TMP_DIR = None


def print_section(text):
    """Prints the needed amount of dashes for each section heading"""
    print('\n' + text + ' ' + ('-' * (80 - len(text))))


def setup_repo(name, persons, signer="alice"):
    prompt_key(f"Create repository {name}: root of trust, policy, person(s) {', '.join(persons)}, no rules")
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
    prompt_key("Branch rules check the RSL entry signature, not the commit signature")
    
    setup_repo("s01-branch-rules", ["alice"])

    prompt_key("Add rule: main needs 1 signature from Alice")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --threshold 1",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice signs the commit and the RSL entry")
    display_command("echo 'Change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Alice)'",
        "gittuf rsl record main --local-only",
        "git cat-file -p refs/gittuf/reference-state-log",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: Alice signed the RSL entry")

    prompt_key("Mallory signs the commit, Alice signs the RSL entry")
    cmd = "git config --local user.signingkey ../keys/mallory"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Change by Mallory' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Change by Mallory\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Mallory)'",
        "git config --local user.signingkey ../keys/alice",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: no file rule exists, so the commit signature is not checked")

    prompt_key("Unsigned commit, Alice signs the RSL entry")
    display_command("echo 'Unsigned change' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Unsigned change\n")
    for cmd in [
        "git add README.md",
        "git -c commit.gpgsign=false commit -m 'Unsigned update'",
        "git cat-file -p HEAD",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: no file rule exists, so an unsigned commit is allowed")

    prompt_key("Alice signs the commit, Mallory signs the RSL entry")
    display_command("echo 'Another change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Another change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Update README (Alice again)'",
        "git config --local user.signingkey ../keys/mallory",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: Mallory is not authorized to sign RSL entries for main")


def scenario_2(): 
    print_section("SCENARIO 2")
    
    prompt_key("File rules check the signature of every commit")
    setup_repo("s02-file-rules", ["alice", "bob", "carol"])

    prompt_key("Add rules: main needs 1 of {Alice, Bob, Carol}; .github/* needs Carol; docs/* needs Alice or Bob")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --authorize carol --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-ci"
        " --rule-pattern 'file:.github/*' --authorize carol --threshold 1",
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-docs"
        " --rule-pattern 'file:docs/*' --authorize alice --authorize bob --threshold 1",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Bob changes docs/ and signs the commit and the RSL entry")
    cmd = "git config --local user.signingkey ../keys/bob"
    display_command(cmd)
    run_command(cmd)
    display_command("mkdir -p docs && echo 'Guide by Bob' >> docs/guide.md")
    os.makedirs("docs", exist_ok=True)
    with open("docs/guide.md", "a") as fp:
        fp.write("Guide by Bob\n")
    for cmd in [
        "git add docs/guide.md",
        "git commit -m 'Add guide (Bob)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: Bob is trusted for main and for docs/*")

    prompt_key("Mallory changes README.md (no file rule), Bob signs the RSL entry")
    cmd = "git config --local user.signingkey ../keys/mallory"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'Typo fix by Mallory' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Typo fix by Mallory\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Fix typo (Mallory)'",
        "git config --local user.signingkey ../keys/bob",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: README.md is not protected by any file rule")

    prompt_key("Unsigned commit to docs/, Bob signs the RSL entry")
    display_command("echo 'Unsigned docs change' >> docs/guide.md")
    with open("docs/guide.md", "a") as fp:
        fp.write("Unsigned docs change\n")
    for cmd in [
        "git add docs/guide.md",
        "git -c commit.gpgsign=false commit -m 'Unsigned docs change'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: docs/* needs a commit signed by Alice or Bob")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Bob changes .github/, Carol signs the RSL entry")
    display_command("mkdir -p .github/workflows && echo 'steps: []' >> .github/workflows/ci.yml")
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/ci.yml", "a") as fp:
        fp.write("steps: []\n")
    for cmd in [
        "git add .github/workflows/ci.yml",
        "git commit -m 'Edit CI (Bob)'",
        "git config --local user.signingkey ../keys/carol",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: the .github/ commit is Bob's, and only Carol is trusted there")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Carol commits to .github/, Bob commits to docs/, Bob records both in one RSL entry")
    display_command("mkdir -p .github/workflows && echo 'steps: [test]' >> .github/workflows/ci.yml")
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/ci.yml", "a") as fp:
        fp.write("steps: [test]\n")
    for cmd in [
        "git add .github/workflows/ci.yml",
        "git commit -m 'Edit CI (Carol)'",
        "git config --local user.signingkey ../keys/bob",
    ]:
        display_command(cmd)
        run_command(cmd)
    display_command("echo 'More docs by Bob' >> docs/guide.md")
    with open("docs/guide.md", "a") as fp:
        fp.write("More docs by Bob\n")
    for cmd in [
        "git add docs/guide.md",
        "git commit -m 'Extend guide (Bob)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd)
    prompt_key("Verification succeeded: each commit is checked only for the paths it changes")

    prompt_key("Carol changes .github/ and docs/ in one commit and signs the RSL entry")
    cmd = "git config --local user.signingkey ../keys/carol"
    display_command(cmd)
    run_command(cmd)
    display_command("echo 'steps: [test, lint]' >> .github/workflows/ci.yml")
    with open(".github/workflows/ci.yml", "a") as fp:
        fp.write("steps: [test, lint]\n")
    display_command("echo 'CI notes by Carol' >> docs/guide.md")
    with open("docs/guide.md", "a") as fp:
        fp.write("CI notes by Carol\n")
    for cmd in [
        "git add .github/workflows/ci.yml docs/guide.md",
        "git commit -m 'Edit CI and docs (Carol)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: Carol is not trusted for docs/*")


def scenario_3():
    print_section("SCENARIO 3")
    prompt_key("2 of 3 approvals, an untrusted approver, a stale approval, approving and merging yourself")
    setup_repo("s03-two-of-three", ["alice", "bob", "carol", "dave"])

    prompt_key("Initial commit on main, recorded before any rule exists")
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

    prompt_key("Add rule: main needs 2 of {Alice, Bob, Carol}")
    for cmd in [
        "gittuf policy add-rule -k ../keys/policy --rule-name protect-main"
        " --rule-pattern git:refs/heads/main --authorize alice --authorize bob --authorize carol --threshold 2",
        "gittuf policy stage --local-only",
        "gittuf policy apply --local-only",
        "gittuf policy list-rules",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice updates main on her own")
    display_command("echo 'Direct change by Alice' >> README.md")
    with open("README.md", "a") as fp:
        fp.write("Direct change by Alice\n")
    for cmd in [
        "git add README.md",
        "git commit -m 'Direct change (Alice)'",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: one RSL signature is 1 of 2")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~1",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice makes the change on a feature branch")
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

    prompt_key("Verify mergeability with no approvals")
    cmd = "gittuf verify-mergeable --base-branch main --feature-branch feature"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the missing approval")

    prompt_key("Dave approves the merge")
    for cmd in [
        "gittuf attest authorize -k ../keys/dave --from-ref feature main",
        "gittuf attest apply --local-only",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
    ]:
        display_command(cmd)
        run_command(cmd)
    cmd = "gittuf verify-mergeable --base-branch main --feature-branch feature"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("Still not mergeable: Dave is not a principal of protect-main")

    prompt_key("Bob approves the merge, then issues a duplicate approval")
    for cmd in [
        "gittuf attest authorize -k ../keys/bob --from-ref feature main",
        "gittuf attest apply --local-only",
        "gittuf attest authorize -k ../keys/bob --from-ref feature main",
        "gittuf attest apply --local-only",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
        "gittuf verify-mergeable --base-branch main --feature-branch feature",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key(
        "Mergeable: Bob's approval is 1 of 2 and the merger supplies the other."
        " Bob's second signature replaced his first one."
    )
    prompt_key("Alice adds a commit to feature after bob approved")
    display_command("echo 'Follow-up by Alice' >> feature.txt")
    with open("feature.txt", "a") as fp:
        fp.write("Follow-up by Alice\n")
    for cmd in [
        "git add feature.txt",
        "git commit -m 'Follow-up change (Alice)'",
        "gittuf rsl record feature --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify mergeability")
    cmd = "gittuf verify-mergeable --base-branch main --feature-branch feature"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the stale approval: Bob approved a different merge tree")

    prompt_key("Bob approves the new state")
    for cmd in [
        "gittuf attest authorize -k ../keys/bob --from-ref feature main",
        "gittuf attest apply --local-only",
        "git grep -o '\"keyid\":\"[^\"]*\"' refs/gittuf/attestations",
        "gittuf verify-mergeable --base-branch main --feature-branch feature",
    ]:
        display_command(cmd)
        run_command(cmd)
    prompt_key("Mergeable again: a new approval is issued for the updated merge tree")

    prompt_key("Bob, who already approved, merges and signs the RSL entry")
    for cmd in [
        "git checkout main",
        "git merge --ff-only feature",
        "git config --local user.signingkey ../keys/bob",
        "gittuf rsl record main --local-only",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Verify main")
    cmd = "gittuf verify-ref main"
    display_command(cmd)
    run_command(cmd, expected_retcode=1)
    prompt_key("gittuf detected the violation: Bob signed twice but is one principal, 1 of 2")

    prompt_key("Rewind to last good state")
    for cmd in [
        "git reset --hard HEAD~2",
        "git update-ref refs/gittuf/reference-state-log refs/gittuf/reference-state-log~1",
    ]:
        display_command(cmd)
        run_command(cmd)

    prompt_key("Alice merges the change Bob approved")
    for cmd in [
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
    prompt_key("Verification succeeded: Alice (RSL entry) + Bob (approval attestation) = 2 of 2")



def run_demo():
    global TMP_DIR
    current_dir = os.getcwd()
    tmp_dir = tempfile.TemporaryDirectory()
    TMP_DIR = tmp_dir.name
    os.chdir(TMP_DIR)

    prompt_key("Set PAGER")
    os.environ["PAGER"] = "cat"
    display_command("export PAGER=cat")

    prompt_key("Generate SSH signing keys (Mallory is never trusted)")
    os.mkdir("keys")
    for key in KEYS:
        cmd = f"ssh-keygen -q -t ecdsa -N '' -C {key} -f keys/{key}"
        display_command(cmd)
        run_command(cmd)

    scenario_1()
    scenario_2()
    scenario_3()

    os.chdir(current_dir)
    prompt_key("Signing demo complete!")


if __name__ == "__main__":
    check_binaries(REQUIRED_BINARIES)
    run_demo()
