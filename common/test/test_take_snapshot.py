# Back In Time
# Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public Licensealong
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import unittest
import stat
from datetime import date, datetime, timedelta
from tempfile import TemporaryDirectory
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshots
import mount

class TestTakeSnapshot(generic.SnapshotsTestCase):
    def setUp(self):
        super(TestTakeSnapshot, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.include.name)

    def tearDown(self):
        super(TestTakeSnapshot, self).tearDown()
        self.include.cleanup()

    def remount(self):
        #dummy method only used in TestTakeSnapshotSSH
        pass

    def getInode(self, sid):
        return os.stat(sid.pathBackup(os.path.join(self.include.name, 'test'))).st_ino

    def test_take_snapshot(self):
        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertTrue(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertFalse(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

        # second _take_snapshot which should not create a new snapshot as nothing
        # has changed
        now = datetime.today() - timedelta(minutes = 4)
        sid2 = snapshots.SID(now, self.cfg)

        self.assertListEqual([False, False], self.sn._take_snapshot(sid2, now, [(self.include.name, 0),] ))
        self.assertFalse(sid2.exists())

        # third _take_snapshot
        self.remount()
        with open(os.path.join(self.include.name, 'lalala'), 'wt') as f:
            f.write('asdf')

        now = datetime.today() - timedelta(minutes = 2)
        sid3 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid3, now, [(self.include.name, 0),] ))
        self.assertTrue(sid3.exists())
        self.assertTrue(sid3.canOpenPath(os.path.join(self.include.name, 'lalala')))
        inode1 = self.getInode(sid1)
        inode3 = self.getInode(sid3)
        self.assertEqual(inode1, inode3)

        # fourth _take_snapshot with force create new snapshot even if nothing
        # has changed
        self.cfg.set_take_snapshot_regardless_of_changes(True)
        now = datetime.today()
        sid4 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid4, now, [(self.include.name, 0),] ))
        self.assertTrue(sid4.exists())
        self.assertTrue(sid4.canOpenPath(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid4.canOpenPath(os.path.join(self.include.name, 'test')))

    def test_take_snapshot_with_spaces_in_include(self):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        include = os.path.join(self.include.name, 'test path with spaces')
        generic.create_test_files(include)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(include, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.canOpenPath(os.path.join(include, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.canOpenPath(os.path.join(include, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertTrue(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertFalse(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

    def test_take_snapshot_exclude(self):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        self.cfg.set_exclude(['bar/baz'])

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'foo', 'bar')))
        self.assertFalse(sid1.canOpenPath(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertTrue(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertFalse(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

    def test_take_snapshot_with_spaces_in_exclude(self):
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)
        exclude = os.path.join(self.include.name, 'test path with spaces')
        generic.create_test_files(exclude)
        self.cfg.set_exclude([exclude])

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'test')))
        self.assertFalse(sid1.canOpenPath(exclude))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2'):
            self.assertTrue(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

        for f in ('failed',
                  'save_to_continue'):
            self.assertFalse(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

    def test_take_snapshot_error(self):
        os.chmod(os.path.join(self.include.name, 'test'), 0o000)
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, True], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(sid1.canOpenPath(os.path.join(self.include.name, 'foo', 'bar', 'baz')))
        self.assertFalse(sid1.canOpenPath(os.path.join(self.include.name, 'test')))
        for f in ('config',
                  'fileinfo.bz2',
                  'info',
                  'takesnapshot.log.bz2',
                  'failed'):
            self.assertTrue(os.path.exists(sid1.path(f)), msg = 'file = {}'.format(f))

    def test_take_snapshot_error_without_continue(self):
        os.chmod(os.path.join(self.include.name, 'test'), 0o000)
        self.cfg.set_continue_on_errors(False)
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([False, True], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertFalse(sid1.exists())

    def test_take_snapshot_new_exists(self):
        new_snapshot = snapshots.NewSnapshot(self.cfg)
        new_snapshot.makeDirs()
        with open(new_snapshot.path('leftover'), 'wt') as f:
            f.write('foo')

        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertFalse(os.path.exists(sid1.path('leftover')))

    def test_take_snapshot_new_exists_continue(self):
        new_snapshot = snapshots.NewSnapshot(self.cfg)
        new_snapshot.makeDirs()
        with open(new_snapshot.path('leftover'), 'wt') as f:
            f.write('foo')
        new_snapshot.saveToContinue = True

        now = datetime.today() - timedelta(minutes = 6)
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([True, False], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))
        self.assertTrue(sid1.exists())
        self.assertTrue(os.path.exists(sid1.path('leftover')))

    def test_take_snapshot_fail_create_new_snapshot(self):
        os.chmod(self.snapshotPath, 0o500)
        now = datetime.today()
        sid1 = snapshots.SID(now, self.cfg)

        self.assertListEqual([False, True], self.sn._take_snapshot(sid1, now, [(self.include.name, 0),] ))

        # fix permissions because cleanup would fial otherwise
        os.chmod(self.snapshotPath, 0o700)

@unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestTakeSnapshotSSH(generic.SSHSnapshotTestCase, TestTakeSnapshot):
    def setUp(self):
        super(TestTakeSnapshotSSH, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.include.name)

        #mount
        self.cfg.set_current_hash_id(mount.Mount(cfg = self.cfg).mount())

    def tearDown(self):
        #unmount
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        super(TestTakeSnapshotSSH, self).tearDown()

        self.include.cleanup()

    def remount(self):
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        hash_id = mount.Mount(cfg = self.cfg).mount()

    def getInode(self, sid):
        return os.stat(os.path.join(self.snapshotPath, sid.sid, 'backup', self.include.name[1:], 'test')).st_ino
