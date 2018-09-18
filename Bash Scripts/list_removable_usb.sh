#!/bin/bash

echo -n 'Removable Drives: '; \lsblk -o NAME,TYPE,RM | grep disk | egrep '1$' | cut -d' ' -f1 | tr '\n' ' ' ; echo
