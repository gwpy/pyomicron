#! /usr/bin/env bash
# vim: nu:ai:ts=4:sw=4

# remove any files from input list that do not exist
# stderr report file counts
# stdout holds list of th existing files
filelist=$@
for x in ${filelist}
do
    if [ -e $x ]
    then
        infiles="${infiles} ${x}"
    fi
done
>&2 echo "infile count $(wc -w <<< ${filelist}) available $(wc -w <<<${infiles})"
echo ${infiles}
