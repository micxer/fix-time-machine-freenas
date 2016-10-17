#!/usr/bin/env python

"""
NAME=${1?:No sparsebundle name given}

labels=$(hdiutil attach -nomount -noverify -noautofsck /Volumes/Time\ Machine/$NAME.sparsebundle)

disk=$(echo $labels | tr " " "\n" | tail -n2 | head -n1)

time fsck_hfs -dfry -c 1g $disk

if [ $? -ne 0 ]
then
    time fsck_hfs -p $disk
    time fsck_hfs -dfry -c 1g $disk
fi

hdiutil detach $disk
#!/bin/bash

TM_BUNDLE="$1"

cd "/Volumes/Time Machine"
chflags nouchg "$TM_BUNDLE" "$TM_BUNDLE/token"
hdiutil attach -nomount -noverify -noautofsck "$TM_BUNDLE"
fsck_hfs -drfy -c 1024 /dev/disk2s2
if [ $? -ne 0 ]
then
    fsck_hfs -p /dev/disk2s2
    fsck_hfs -drfy -c 1024 /dev/disk2s2
fi
success = $?
hdiutil detach /dev/disk2s2

if [ $success -eq 0 ]
then
    sed -ibck 's/<key>RecoveryBackupDeclinedDate</key>//g' "$TM_BUNDLE/com.apple.TimeMachine.MachineID.plist"
fi
"""