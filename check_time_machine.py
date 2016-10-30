#!/usr/bin/env python

"""
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
    current_datetime = None
    initial_snapshot = None
    current_snapshot = None
    snapshot_list = {}
    ssh_connection = None
    configuration = None

    def __init__(self, configuration, logger):
        self.__configuration = configuration
        self.__ssh_connection = SSHClient()
        self.__ssh_connection.load_system_host_keys()
        self.__ssh_connection.connect(self.__configuration['freenas_host'])
        self.logger = logger
        self.__current_datetime = datetime.now()

    def create_initial_snapshot(self):
        """
        Create snapshot before changing any data
        """
        self.__initial_snapshot = self.__configuration['dataset'] + '@time-machine-fixer-' + self.__current_datetime.strftime('%Y%m%d-%H%M%S')
        self.logger.info('Initial snapshot name: %s', self.__initial_snapshot)

        create_snapshot_cmd = 'sudo zfs snapshot -r ' + self.__initial_snapshot
        self.logger.debug('Create snapshot command: %s', create_snapshot_cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(create_snapshot_cmd)
        self.logger.error("".join(stderr.readlines()))
        self.logger.info("".join(stdout.readlines()))

    def destroy_initial_snapshot(self):
        """
        Go back to the state before start of fixing process
        """
        destroy_snapshot_cmd = 'sudo zfs destroy -r ' + self.__initial_snapshot
        self.logger.debug('Destroy snapshot command: %s', destroy_snapshot_cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(destroy_snapshot_cmd)
        self.logger.error("".join(stderr.readlines()))
        self.logger.info("".join(stdout.readlines()))

    def get_snapshot_list(self):
        """
        Gets a list of snapshots from the dataset on FreeNAS
        """
        list_snapshots_cmd = 'ls -1 /mnt/' + self.__configuration['dataset'] + '/.zfs/snapshot/'
        self.logger.debug('List snapshots command: %s', list_snapshots_cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(list_snapshots_cmd)
        snapshot_list = [snapshot.strip() for snapshot in stdout.readlines() if snapshot.startswith('auto-')]
        self.logger.debug(",".join(snapshot_list))
        # auto-20160827.0003-2m
        for snapshot in snapshot_list:
            self.snapshot_list[datetime.strptime(snapshot.split('-')[1], '%Y%m%d.%H%M')] = snapshot
        self.logger.debug(self.snapshot_list)



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
    tmf.get_snapshot_list()
    tmf.destroy_initial_snapshot()
    tmf.get_snapshot_list()

if __name__ == '__main__':
    main()
