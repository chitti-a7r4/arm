#!/bin/sh
# Run from the project root on Linux. Pass the same asset flags as the app.
set -eu
uname -smr
cat /etc/os-release
if test -r /proc/device-tree/model; then
    tr -d '\000' < /proc/device-tree/model
    echo
fi
python3 --version
for sample in 'Meet you at the library after lunch.' 'Account locked. Verify now at https://account.example.invalid'; do
    for repeat in 1 2 3; do
        echo "$sample" | /usr/bin/time -f 'wall_s=%e cpu=%P peak_process_kib=%M exit=%x' python3 -m sms_guard "$@"
    done
done
