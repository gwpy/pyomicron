#! /usr/bin/env bash
# vim: nu:ai:ts=4:sw=4

# this fixes an omicron bug specifying unsigned iny data type
for x in $@
do
  sed -i -e 's/uint_8s/int_8u/' $x
done