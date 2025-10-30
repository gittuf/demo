prompt_key("Add policy file to delegate responsibility")
cmd = ( 
    "gittuf policy add-rule"
    "-k ../keys/targets"
    "--rule-name 'protect-main-delegated'"
    "--policy name protect-main"
    "--rule-pattern git:refs/heads/main"
    "--authorize authorized-user"
)
display_command(cmd)
run_command(cmd)
