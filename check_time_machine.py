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

import logging
import argparse
import yaml
from datetime import datetime
from os import path
from paramiko.client import SSHClient

class TimeMachineFixer(object):
  initial_snapshot = None
  current_snapshot = None
  ssh_connection = None
  configuration = None

  def __init__(self, configuration, logger):
    self.configuration = configuration
    self.ssh_connection = SSHClient()
    self.ssh_connection.load_system_host_keys()
    self.ssh_connection.connect(self.configuration['freenas_host'])
    self.logger = logger

  def create_initial_snapshot(self):
    """
    Create snapshot before changing any data
    """
    self.initial_snapshot = self.configuration['dataset'] + '@time-machine-fixer-' + datetime.now().strftime('%Y%m%d-%H%M%S')
    self.logger.info('Initial snapshot name: %s', self.initial_snapshot)

    create_snapshot_cmd = 'sudo zfs snapshot -r ' + self.initial_snapshot
    self.logger.debug('Create snapshot command: %s', create_snapshot_cmd)
    stdin, stdout, stderr = self.ssh_connection.exec_command(create_snapshot_cmd)
    self.logger.error("".join(stderr.readlines()))
    self.logger.info("".join(stdout.readlines()))

    list_snapshots_cmd = 'ls -1 /mnt/' + self.configuration['dataset'] + '/.zfs/snapshot/'
    self.logger.debug('List snapshots command: %s', list_snapshots_cmd)
    stdin, stdout, stderr = self.ssh_connection.exec_command(list_snapshots_cmd)
    self.logger.debug(",".join([x.strip() for x in stdout.readlines()]))
    

  def destroy_initial_snapshot(self):
    """
    Go back to the state before start of fixing process
    """
    destroy_snapshot_cmd = 'sudo zfs destroy -r ' + self.initial_snapshot
    self.logger.debug('Destroy snapshot command: %s', destroy_snapshot_cmd)
    stdin, stdout, stderr = self.ssh_connection.exec_command(destroy_snapshot_cmd)
    self.logger.error("".join(stderr.readlines()))
    self.logger.info("".join(stdout.readlines()))

    list_snapshots_cmd = 'ls -1 /mnt/' + self.configuration['dataset'] + '/.zfs/snapshot/'
    self.logger.debug('List snapshots command: %s', list_snapshots_cmd)
    stdin, stdout, stderr = self.ssh_connection.exec_command(list_snapshots_cmd)
    self.logger.debug(",".join([x.strip() for x in stdout.readlines()]))


def load_configuration(config_file):
  config_stream = open(config_file, "r")
  configuration = yaml.load(config_stream)
  return configuration

def setup_logger(loglevel):
	numeric_level = getattr(logging, loglevel.upper(), None)
	if not isinstance(numeric_level, int):
		raise ValueError('Invalid log level: %s' % loglevel)
	logging.basicConfig(filename='fix-time-machine.log',format='%(levelname)s: %(asctime)s:%(message)s', datefmt='%b %d %H:%M:%S', level=numeric_level)
	return logging.getLogger(__name__)

def main():
  parser = argparse.ArgumentParser()

  parser.add_argument("sparsebundle", help='Name of the sparsebundle to fix (without the extension, e.g. "MyMacBook" for MyMacBook.sparsebundle)')
  parser.add_argument("--loglevel", help='Level of logging (CRITICAL, ERROR, WARNING (default), INFO, DEBUG)', default="WARNING")

  args = parser.parse_args()

  logger = setup_logger(args.loglevel)
  configuration = load_configuration(path.expanduser("~") + "/.time-machine-fixer.yml")

  tmf = TimeMachineFixer(configuration, logger)
  tmf.create_initial_snapshot()
  tmf.destroy_initial_snapshot()

if __name__ == '__main__':
  main()
