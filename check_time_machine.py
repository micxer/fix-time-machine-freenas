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

from os import path
import argparse
import yaml
from paramiko.client import SSHClient

class TimeMachineFixer(object):
  initial_snapshot = None
  current_snapshot = None
  ssh_connection = None
  configuration = None

  def __init__(self, configuration):
    self.configuration = configuration
    self.ssh_connection = SSHClient()
    self.ssh_connection.load_system_host_keys()
    self.ssh_connection.connect(self.configuration['freenas_host'])

  def create_initial_snapshot(self):
    """
    Create snapshot before changing any data
    """
    self.initial_snapshot = self.configuration['dataset'] + '@time-machine-fixer'
    stdin, stdout, stderr = self.ssh_connection.exec_command('sudo zfs snapshot -r ' + self.initial_snapshot)
    for line in stdout.readlines():
      print line.strip()
    for line in stderr.readlines():
      print line.strip()
    stdin, stdout, stderr = self.ssh_connection.exec_command('ls -1 /mnt/' + self.configuration['dataset'] + '/.zfs/snapshot/')
    for line in stdout.readlines():
      print line.strip()

  def destroy_initial_snapshot(self):
    """
    Go back to the state before start of fixing process
    """
    stdin, stdout, stderr = self.ssh_connection.exec_command('sudo zfs destroy -r ' + self.initial_snapshot)
    for line in stdout.readlines():
      print line.strip()
    stdin, stdout, stderr = self.ssh_connection.exec_command('ls -1 /mnt/' + self.configuration['dataset'] + '/.zfs/snapshot/')
    for line in stdout.readlines():
      print line.strip()


def load_configuration(config_file):
  config_stream = open(config_file, "r")
  configuration = yaml.load(config_stream)
  return configuration

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("sparsebundle")
  args = parser.parse_args()
  configuration = load_configuration(path.expanduser("~") + "/.time-machine-fixer.yml")
  tmf = TimeMachineFixer(configuration)
  tmf.create_initial_snapshot()
  tmf.destroy_initial_snapshot()

if __name__ == '__main__':
  main()
