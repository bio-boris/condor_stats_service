#!/usr/bin/env bash

while true
do
    python /kb/module/lib/condor_stats/generate_condor_dump.py > generate_condor_dump.log
    sleep 60
done