#!/usr/bin/env bash

# run a job in the omicron conda environment
# used to initialize environment for condor jobs that don't have
function usage()
{
    echo "$(basename $0) initializes the curren conda_omicron environment, ensures x509, scitoken and kerberos"
    echo "identities are current, then launches the specified tools"
    echo "usage: $(basename $0) <executable> <arguments>"
}
if [ $# -lt 1 ]
then
    usage
    ret=1
elif [ ! -x $1 ]
then
    echo " $1 is not executable"
    usage
    ret=1
else
    if [ -e ${HOME}/.bashrc ]
    then
        source ${HOME}/.bashrc
        echo "Using ${HOME}/.bashrc"
    elif [ -e ${HOME}/.bash_profile ]
    then
          source ${HOME}/.bash_profile
          echo "Using ${HOME}/.bash_profile"
    fi
    
    #source "${CONDA_PATH}/etc/profile.d/conda.sh"
    conda activate ligo-omicron-3.10-test
    export MPLCONFIDIR=/local/$USER/matplotlib
    export HDF5_USE_FILE_LOCKING=FALSE
    source /home/detchar/etc/ligo-omicron/scripts/functions
    get_kerberos_ticket
    get_x509_ticket
    if [ -z "${X509_USER_PROXY}" ] && [ ! -z "${X509_USER_CERT}" ]
    then
        export X509_USER_PROXY=${X509_USER_CERT}
    else
        X509_USER_PROXY=$(ecp-cert-info -path)
    fi
    eval $@
    ret=$?
fi
exit $ret

