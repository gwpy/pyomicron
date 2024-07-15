#!/bin/bash
# -*- coding: utf-8 -*-
# vim: nu:ai:ts=4:sw=4
#  Copyright (C) 2024 Joseph Areeda <joseph.areeda@ligo.org>

# Licensed under GPL3, free software

# default values
ENV_NAME=ligo-omicron-3.10
CONDA_SH=${HOME}/.conda/envs/${ENV_NAME}/etc/profile.d/conda.sh
DEBUG=1

function usage()
{
  echo "$0 is a script that enables programs to run in a conda environment under cron or condor"
  echo "$0 <options> <path to program> [<program options>]"
  echo "Options:"
  echo "    -c <path to conda.sh> default: ${CONDA_SH}"
  echo "    -h show this message"
  echo "    -n <name of conda environment> default: ${ENV_NAME}"
  echo "    -v verbose"
}

function log()
{
  if [[ ${DEBUG} != 0 ]]
  then
    echo "$@" 1>&2
  fi
}

new_sh=0


while getopts "hvn:c:" opt
do
    case "${opt}" in
      h)
        usage
        exit 1
        ;;
      v)
        DEBUG=1
        ;;
      n)
        ENV_NAME="${OPTARG}"
        ;;
      c)
        CONDA_SH="${OPTARG}"
        new_sh=1
        ;;
      *)
        echo "Unknown option ${opt}"
        usage
        exit 2
    esac
done

if [[ ${new_sh} == 0 ]]
then
  CONDA_SH=${HOME}/.conda/envs/${ENV_NAME}/etc/profile.d/conda.sh
fi
log "conda init script: ${CONDA_SH}"
log "conda env: ${ENV_NAME}"

if [[ ${OPTIND} -gt $# ]]
then
  usage
  echo "No program specified"
  exit 3
fi

log "Positional arguments"
for p in $(seq ${OPTIND} $#)
do
  log "arg ${p}: ${@:$p:1}"
done
