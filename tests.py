#!/usr/bin/env python

import unittest
from fix_time_machine_backup import SnapshotList

class TestSnapshotList(unittest.TestCase):
    def setUp(self):
        self.snapshot_list = SnapshotList([
            'auto-20160820.2103-2m', 
            'auto-20160821.0003-2m', 
            'auto-20160821.1503-2m', 
            'auto-20160821.2303-2m', 
            'auto-20160823.1003-2m', 
            'auto-20160825.1003-2m', 
            'auto-20160827.0003-2m', 
            'auto-20160827.1003-2m', 
            'auto-20160828.0603-2m',
        ])

    def test_get_next_snapshot(self):
        self.assertEqual(self.snapshot_list.get_current_snapshot(), 'auto-20160828.0603-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160821.0003-2m')


if __name__ == '__main__':
    unittest.main()