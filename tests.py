#!/usr/bin/env python

import unittest
from datetime import datetime, timedelta
from fix_time_machine_backup import SnapshotList

class TestSnapshotList(unittest.TestCase):
    def setUp(self):
        snapshot_list = []
        snapshot_date = datetime(2016, 8, 20, hour=21, minute=3)
        for i in range(0, 671):
            snapshot_list.append(snapshot_date.strftime('auto-%Y%m%d.%H%M-2m'))
            snapshot_date = (snapshot_date + timedelta(hours=1))
        self.snapshot_list = SnapshotList(snapshot_list)

    def test_get_current_snapshot_returns_first_snapshot_on_first_invocation(self):
        self.assertEqual(self.snapshot_list.get_current_snapshot(), 'auto-20160917.1903-2m')
        #self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160910.0003-2m')

    def test_iterating_returns_snapshots_week_by_week(self):
        self.assertEqual(self.snapshot_list.get_current_snapshot(), 'auto-20160917.1903-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160910.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160903.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160827.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160820.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160823.0003-2m')

    def test_pass_working_switches_to_binary_search_mode(self):
        self.assertEqual(self.snapshot_list.get_current_snapshot(), 'auto-20160917.1903-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160910.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(), 'auto-20160903.0003-2m')
        self.assertEqual(self.snapshot_list.get_next_snapshot(True), 'auto-20160906.1203-2m')

if __name__ == '__main__':
    unittest.main()