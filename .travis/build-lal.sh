#!/bin/bash

set -e
set -x

LAL_TAG="lal-${LAL_VERSION}"
LAL_TARBALL="${LAL_TAG}.tar.xz"
LAL_SOURCE="http://software.ligo.org/lscsoft/source/lalsuite"

target=`python -c "import sys; print(sys.prefix)"`

echo "----------------------------------------------------------------------"
echo "Installing from ${LAL_TARBALL}"

if [ -f ${LAL_TAG}/.travis-src-file ] && [ `cat ${LAL_TAG}/.travis-src-file` == "${LAL_TARBALL}" ]; then
    cd ${LAL_TAG}
else
    wget ${LAL_SOURCE}/${LAL_TARBALL} -O ${LAL_TARBALL} --quiet
    mkdir -p ${LAL_TAG}
    tar -xf ${LAL_TARBALL} --strip-components=1 -C ${LAL_TAG}
    cd ${LAL_TAG}
    ./configure --enable-silent-rules --enable-swig-python --quiet --prefix=${target}
fi

# configure if the makefile still doesn't exist
if [ ! -f ./Makefile ]; then
    ./configure --enable-silent-rules --prefix=$target $@
fi

make --silent
make install --silent
