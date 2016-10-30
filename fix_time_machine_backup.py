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
import subprocess

class TimeMachineFixer(object):

    def __init__(self, configuration, logger, sparsebundle):
        self.__configuration = configuration
        self.__ssh_connection = SSHClient()
        self.__ssh_connection.load_system_host_keys()
        self.__ssh_connection.connect(self.__configuration['freenas_host'])
        self.logger = logger
        self.__sparsebundle = sparsebundle
        self.__current_datetime = datetime.now()

    def create_rollback_snapshot(self):
        """
        Create snapshot before changing any data
        """
        self.__initial_snapshot = self.__configuration['dataset'] + '@time-machine-fixer-rollback-' + self.__current_datetime.strftime('%Y%m%d-%H%M%S')
        self.logger.info('Initial snapshot name: %s', self.__initial_snapshot)

        create_snapshot_cmd = 'sudo zfs snapshot -r ' + self.__initial_snapshot
        self.logger.debug('Create snapshot command: %s', create_snapshot_cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(create_snapshot_cmd)
        self.logger.error("".join(stderr.readlines()))
        self.logger.info("".join(stdout.readlines()))

    def destroy_rollback_snapshot(self):
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
        Gets a list of snapshots from the dataset on FreeNAS that have a size diff greater than 0
        """
        list_snapshots_cmd = 'zfs list -r -t snapshot -o name,used {0}'.format(self.__configuration['dataset'])
        self.logger.debug('List snapshots command: %s', list_snapshots_cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(list_snapshots_cmd)

        snapshot_list = []
        for snapshot in stdout.readlines():
            snapshot_name, snapshot_size = snapshot.split()
            if snapshot_size != '0' and '@auto' in snapshot_name:
                snapshot_list.append(snapshot_name)

        self.logger.debug('Snapshot list: %s', ",".join(snapshot_list))

        # snapshot names like auto-20160827.0003-2m
        snapshot_dict = {}
        for snapshot in snapshot_list:
            snapshot_dict[datetime.strptime(snapshot.split('-')[1], '%Y%m%d.%H%M')] = snapshot

        self.logger.debug(snapshot_dict)
        return snapshot_dict

    def revert_to_snapshot(self, snapshot):
        cmd = 'rsync -avPh --delete /{mount_prefix}/{dataset}/.zfs/snapshot/{snapshot}/{sparsebundle}.sparsebundle/ /{mount_prefix}/{dataset}/{sparsebundle}.sparsebundle/'.format(
            mount_prefix=self.__configuration['mount_prefix'],
            dataset=self.__configuration['dataset'],
            snapshot=snapshot,
            sparsebundle=self.__sparsebundle
        )
        self.logger.info('FreeNAS: %s', cmd)
        stdin, stdout, stderr = self.__ssh_connection.exec_command(cmd)
        self.logger.error("".join(stderr.readlines()))
        self.logger.debug("".join(stdout.readlines()))

    def fsck_sparsebundle(self):
        self._prepare_sparsebundle()
        self._mount_sparsebundle()
        self._do_fsck()
        self._unmount_sparsebundle()

    def _mount_sparsebundle(self):
        cmd = 'sudo hdiutil attach -nomount -noverify -noautofsck /Volumes/Time\ Machine/' + self.__sparsebundle + '.sparsebundle'
        self.logger.info(cmd)
        labels = subprocess.check_output(cmd, shell=True)
        self.logger.debug(labels)
        self.__disk = labels.split()[-2]

    def _unmount_sparsebundle(self):
        cmd = 'sudo hdiutil detach ' + self.__disk
        self.logger.info(cmd)
        output = subprocess.check_output(cmd, shell=True)
        self.logger.debug(output)
        self.__disk = None

    def _prepare_sparsebundle(self):
        sparsebundle_path = '/Volumes/Time Machine/' + self.__sparsebundle + '.sparsebundle'
        cmd = 'sudo chflags nouchg "{0}" "{0}/token"'.format(sparsebundle_path)
        self.logger.info(cmd)
        output = subprocess.check_output(cmd, shell=True)
        self.logger.debug(output)

    def _do_fsck(self):
        fsck_full_check_cmd = 'sudo time fsck_hfs -dfry -c 1g ' + self.__disk
        fsck_prune_cmd = 'sudo time fsck_hfs -p ' + self.__disk
        try:
            self.logger.info(fsck_full_check_cmd)
            output = subprocess.check_output(fsck_full_check_cmd, shell=True)
            self.logger.debug(output)
        except subprocess.CalledProcessError as e:
            self.logger.warning(e.output)
            try:
                self.logger.info(fsck_prune_cmd)
                output = subprocess.check_output(fsck_prune_cmd, shell=True)
                self.logger.info(fsck_full_check_cmd)
                output = subprocess.check_output(fsck_full_check_cmd, shell=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(e.output)
                return False

        return True

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

    tmf = TimeMachineFixer(configuration, logger, args.sparsebundle)
    tmf.create_rollback_snapshot()
    snapshots = tmf.get_snapshot_list()
    for timestamp, snapshot in snapshots.iteritems():
        try:
            tmf.revert_to_snapshot(snapshot)
            tmf.fsck_sparsebundle()
        except Exception:
            continue
        print 'Snapshot {0} contains a working sparsebundle'.format(snapshot)
        break
#    tmf.destroy_rollback_snapshot()
#    tmf.get_snapshot_list()

if __name__ == '__main__':
    main()