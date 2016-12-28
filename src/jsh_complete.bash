# this is the completion file for the jenkins shell.

_jsh()
{
    eval `jsh complete ${COMP_TYPE} ${COMP_CWORD} ${COMP_WORDS[@]}`
    if [[ $? != 0 ]]; then
        unset COMPREPLY
    fi
    return 0
}
complete -F _jsh jsh

