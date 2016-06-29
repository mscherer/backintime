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
import shutil
import stat
import pwd
import grp
import re
from datetime import date, datetime, timedelta
from threading import Thread
from tempfile import TemporaryDirectory, NamedTemporaryFile
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config
import configfile
import snapshots
import tools
from snapshotlog import LogFilter

CURRENTUID = os.geteuid()
CURRENTUSER = pwd.getpwuid(CURRENTUID).pw_name

CURRENTGID = os.getegid()
CURRENTGROUP = grp.getgrgid(CURRENTGID).gr_name

#all groups the current user is member in
GROUPS = [i.gr_name for i in grp.getgrall() if CURRENTUSER in i.gr_mem]
NO_GROUPS = not GROUPS

IS_ROOT = os.geteuid() == 0

class TestSnapshots(generic.SnapshotsTestCase):
    def setUp(self):
        super(TestSnapshots, self).setUp()

        for f in (self.cfg.get_take_snapshot_log_file(), self.cfg.get_take_snapshot_message_file()):
            if os.path.exists(f):
                os.remove(f)

    ############################################################################
    ###                              get_uid                                 ###
    ############################################################################
    def test_get_uid_valid(self):
        self.assertEqual(self.sn.get_uid('root'), 0)
        self.assertEqual(self.sn.get_uid(b'root'), 0)

        self.assertEqual(self.sn.get_uid(CURRENTUSER), CURRENTUID)
        self.assertEqual(self.sn.get_uid(CURRENTUSER.encode()), CURRENTUID)

    def test_get_uid_invalid(self):
        self.assertEqual(self.sn.get_uid('nonExistingUser'), -1)
        self.assertEqual(self.sn.get_uid(b'nonExistingUser'), -1)

    def test_get_uid_backup(self):
        self.assertEqual(self.sn.get_uid('root', backup = 99999), 0)
        self.assertEqual(self.sn.get_uid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_uid('nonExistingUser', backup = 99999), 99999)
        self.assertEqual(self.sn.get_uid(b'nonExistingUser', backup = 99999), 99999)

        self.assertEqual(self.sn.get_uid(CURRENTUSER,  backup = 99999), CURRENTUID)
        self.assertEqual(self.sn.get_uid(CURRENTUSER.encode(),  backup = 99999), CURRENTUID)

    ############################################################################
    ###                              get_gid                                 ###
    ############################################################################
    def test_get_gid_valid(self):
        self.assertEqual(self.sn.get_gid('root'), 0)
        self.assertEqual(self.sn.get_gid(b'root'), 0)

        self.assertEqual(self.sn.get_gid(CURRENTGROUP), CURRENTGID)
        self.assertEqual(self.sn.get_gid(CURRENTGROUP.encode()), CURRENTGID)

    def test_get_gid_invalid(self):
        self.assertEqual(self.sn.get_gid('nonExistingGroup'), -1)
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup'), -1)

    def test_get_gid_backup(self):
        self.assertEqual(self.sn.get_gid('root', backup = 99999), 0)
        self.assertEqual(self.sn.get_gid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_gid('nonExistingGroup', backup = 99999), 99999)
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup', backup = 99999), 99999)

        self.assertEqual(self.sn.get_gid(CURRENTGROUP,  backup = 99999), CURRENTGID)
        self.assertEqual(self.sn.get_gid(CURRENTGROUP.encode(),  backup = 99999), CURRENTGID)

    ############################################################################
    ###                          get_user_name                               ###
    ############################################################################
    def test_get_user_name_valid(self):
        self.assertEqual(self.sn.get_user_name(0), 'root')

        self.assertEqual(self.sn.get_user_name(CURRENTUID), CURRENTUSER)

    def test_get_user_name_invalid(self):
        self.assertEqual(self.sn.get_user_name(99999), '-')

    ############################################################################
    ###                         get_group_name                               ###
    ############################################################################
    def test_get_group_name_valid(self):
        self.assertEqual(self.sn.get_group_name(0), 'root')

        self.assertEqual(self.sn.get_group_name(CURRENTGID), CURRENTGROUP)

    def test_get_group_name_invalid(self):
        self.assertEqual(self.sn.get_group_name(99999), '-')

    ############################################################################
    ###                     take_snapshot helper scripts                     ###
    ############################################################################
    def test_rsync_remote_path(self):
        self.assertEqual(self.sn.rsync_remote_path('/foo'),
                         '/foo')
        self.assertEqual(self.sn.rsync_remote_path('/foo', quote = '\\\"'),
                         '\\\"/foo\\\"')
        self.assertEqual(self.sn.rsync_remote_path('/foo', use_mode = ['local']),
                         '/foo')
        self.assertEqual(self.sn.rsync_remote_path('/foo', use_mode = ['local'], quote = '\\\"'),
                         '\\\"/foo\\\"')

        #set up SSH profile
        self.cfg.set_snapshots_mode('ssh')
        self.cfg.set_ssh_host('localhost')
        self.cfg.set_ssh_user('foo')
        self.assertEqual(self.sn.rsync_remote_path('/bar'),
                         'foo@localhost:/bar')
        self.assertEqual(self.sn.rsync_remote_path('/bar', quote = '\\\"'),
                         'foo@localhost:\\\"/bar\\\"')

        self.assertEqual(self.sn.rsync_remote_path('/bar', use_mode = []),
                         '/bar')

    def test_create_last_snapshot_symlink(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid1.makeDirs()
        symlink = self.cfg.get_last_snapshot_symlink()
        self.assertFalse(os.path.exists(symlink))

        self.assertTrue(self.sn.create_last_snapshot_symlink(sid1))
        self.assertTrue(os.path.islink(symlink))
        self.assertEqual(os.path.realpath(symlink), sid1.path())

        sid2 = snapshots.SID('20151219-020324-123', self.cfg)
        sid2.makeDirs()
        self.assertTrue(self.sn.create_last_snapshot_symlink(sid2))
        self.assertTrue(os.path.islink(symlink))
        self.assertEqual(os.path.realpath(symlink), sid2.path())

    def flockSecondInstance(self):
        cfgFile = os.path.abspath(os.path.join(__file__, os.pardir, 'config'))
        cfg = config.Config(cfgFile)
        sn = snapshots.Snapshots(cfg)
        sn.GLOBAL_FLOCK = self.sn.GLOBAL_FLOCK

        cfg.set_use_global_flock(True)
        sn.flockExclusive()
        sn.flockRelease()

    def test_flockExclusive(self):
        RWUGO = 33206 #-rw-rw-rw
        self.cfg.set_use_global_flock(True)
        thread = Thread(target = self.flockSecondInstance, args = ())
        self.sn.flockExclusive()

        self.assertTrue(os.path.exists(self.sn.GLOBAL_FLOCK))
        mode = os.stat(self.sn.GLOBAL_FLOCK).st_mode
        self.assertEqual(mode, RWUGO)

        thread.start()
        thread.join(0.01)
        self.assertTrue(thread.is_alive())

        self.sn.flockRelease()
        thread.join()
        self.assertFalse(thread.is_alive())

    def test_stat_free_space_local(self):
        self.assertIsInstance(self.sn._stat_free_space_local('/'), int)

    ############################################################################
    ###                   rsync Ex-/Include and suffix                       ###
    ############################################################################
    def test_rsyncExclude_unique_items(self):
        exclude = self.sn.rsyncExclude(['/foo', '*bar', '/baz/1'])
        self.assertListEqual(list(exclude), ['--exclude=/foo',
                                             '--exclude=*bar',
                                             '--exclude=/baz/1'])

    def test_rsyncExclude_duplicate_items(self):
        exclude = self.sn.rsyncExclude(['/foo', '*bar', '/baz/1', '/foo', '/baz/1'])
        self.assertListEqual(list(exclude), ['--exclude=/foo',
                                             '--exclude=*bar',
                                             '--exclude=/baz/1'])

    def test_rsyncInclude_unique_items(self):
        i1, i2 = self.sn.rsyncInclude([('/foo', 0),
                                       ('/bar', 1),
                                       ('/baz/1/2', 1)])
        self.assertListEqual(list(i1), ['--include=/foo/',
                                        '--include=/baz/1/',
                                        '--include=/baz/'])
        self.assertListEqual(list(i2), ['--include=/foo/**',
                                        '--include=/bar',
                                        '--include=/baz/1/2'])

    def test_rsyncInclude_duplicate_items(self):
        i1, i2 = self.sn.rsyncInclude([('/foo', 0),
                                       ('/bar', 1),
                                       ('/foo', 0),
                                       ('/baz/1/2', 1),
                                       ('/baz/1/2', 1)])
        self.assertListEqual(list(i1), ['--include=/foo/',
                                        '--include=/baz/1/',
                                        '--include=/baz/'])
        self.assertListEqual(list(i2), ['--include=/foo/**',
                                        '--include=/bar',
                                        '--include=/baz/1/2'])

    def test_rsyncInclude_root(self):
        i1, i2 = self.sn.rsyncInclude([('/', 0), ])
        self.assertListEqual(list(i1), [])
        self.assertListEqual(list(i2), ['--include=/',
                                        '--include=/**'])

    def test_rsyncSuffix(self):
        suffix = self.sn.rsyncSuffix(includeFolders = [('/foo', 0),
                                                       ('/bar', 1),
                                                       ('/baz/1/2', 1)],
                                     excludeFolders = ['/foo/bar',
                                                       '*blub',
                                                       '/bar/2'])
        self.assertIsInstance(suffix, list)
        self.assertRegex(' '.join(suffix), r'^--chmod=Du\+wx '      +
                                           r'--exclude=/tmp/.*? '   +
                                           r'--exclude=.*?\.local/share/backintime '  +
                                           r'--exclude=\.local/share/backintime/mnt ' +
                                           r'--include=/foo/ '      +
                                           r'--include=/baz/1/ '    +
                                           r'--include=/baz/ '      +
                                           r'--exclude=/foo/bar '   +
                                           r'--exclude=\*blub '     +
                                           r'--exclude=/bar/2 '     +
                                           r'--include=/foo/\*\* '  +
                                           r'--include=/bar '       +
                                           r'--include=/baz/1/2 '   +
                                           r'--exclude=\* /$')

    ############################################################################
    ###                            callback                                  ###
    ############################################################################
    def test_restore_callback(self):
        msg = 'foo'
        callback = lambda x: self.callback(self.assertEqual, x, msg)
        self.sn.restore_callback(callback, True, msg)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        self.run = False
        callback = lambda x: self.callback(self.assertRegex, x, r'{} : \w+'.format(msg))
        self.sn.restore_callback(callback, False, msg)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)

    @unittest.skip('Not yet implemented')
    def test_filter_rsync_progress(self):
        pass

    def test_exec_rsync_callback(self):
        params = [False, False]

        self.sn._exec_rsync_callback('foo', params)
        self.assertListEqual([False, False], params)
        with open(self.cfg.get_take_snapshot_message_file(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: foo)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.get_take_snapshot_log_file(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: foo)\n', f.read())

    def test_exec_rsync_callback_keep_params(self):
        params = [True, True]

        self.sn._exec_rsync_callback('foo', params)
        self.assertListEqual([True, True], params)

    def test_exec_rsync_callback_transfer(self):
        params = [False, False]

        self.sn._exec_rsync_callback('BACKINTIME: <f+++++++++ /foo/bar', params)
        self.assertListEqual([False, True], params)
        with open(self.cfg.get_take_snapshot_message_file(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: BACKINTIME: <f+++++++++ /foo/bar)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.get_take_snapshot_log_file(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: BACKINTIME: <f+++++++++ /foo/bar)\n[C] <f+++++++++ /foo/bar\n', f.read())

    def test_exec_rsync_callback_dir(self):
        params = [False, False]

        self.sn._exec_rsync_callback('BACKINTIME: cd..t...... /foo/bar', params)
        self.assertListEqual([False, False], params)
        with open(self.cfg.get_take_snapshot_message_file(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: BACKINTIME: cd..t...... /foo/bar)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.get_take_snapshot_log_file(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: BACKINTIME: cd..t...... /foo/bar)\n', f.read())

    def test_exec_rsync_callback_error(self):
        params = [False, False]

        self.sn._exec_rsync_callback('rsync: send_files failed to open "/foo/bar": Operation not permitted (1)', params)
        self.assertListEqual([True, False], params)
        with open(self.cfg.get_take_snapshot_message_file(), 'rt') as f:
            self.assertEqual('1\nError: rsync: send_files failed to open "/foo/bar": Operation not permitted (1)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.get_take_snapshot_log_file(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: rsync: send_files failed to open "/foo/bar": Operation not permitted (1))\n' \
                             '[E] Error: rsync: send_files failed to open "/foo/bar": Operation not permitted (1)\n', f.read())

    ############################################################################
    ###                          smart remove                                ###
    ############################################################################
    def test_inc_month(self):
        self.assertEqual(self.sn.inc_month(date(2016,  4, 21)), date(2016, 5, 1))
        self.assertEqual(self.sn.inc_month(date(2016, 12, 24)), date(2017, 1, 1))

    def test_dec_month(self):
        self.assertEqual(self.sn.dec_month(date(2016, 4, 21)), date(2016,  3, 1))
        self.assertEqual(self.sn.dec_month(date(2016, 1, 14)), date(2015, 12, 1))

    def test_smart_remove_keep_all(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        keep = self.sn._smart_remove_keep_all_(sids,
                                               date(2016, 4, 20),
                                               date(2016, 4, 23))
        self.assertSetEqual(keep, set((sid2, sid3, sid4, sid5)))

        keep = self.sn._smart_remove_keep_all_(sids,
                                               date(2016, 4, 11),
                                               date(2016, 4, 18))
        self.assertSetEqual(keep, set())

    def test_smart_remove_keep_first(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        keep = self.sn._smart_remove_keep_first_(sids,
                                                 date(2016, 4, 20),
                                                 date(2016, 4, 23))
        self.assertSetEqual(keep, set((sid2,)))

        keep = self.sn._smart_remove_keep_first_(sids,
                                                 date(2016, 4, 11),
                                                 date(2016, 4, 18))
        self.assertSetEqual(keep, set())

    def test_smart_remove_list(self):
        sid1  = snapshots.SID('20160424-215134-123', self.cfg)
        sid2  = snapshots.SID('20160422-030324-123', self.cfg)
        sid3  = snapshots.SID('20160422-020324-123', self.cfg)
        sid4  = snapshots.SID('20160422-010324-123', self.cfg)
        sid5  = snapshots.SID('20160421-033218-123', self.cfg)
        sid6  = snapshots.SID('20160421-013218-123', self.cfg)
        sid7  = snapshots.SID('20160420-013218-123', self.cfg)
        sid8  = snapshots.SID('20160419-013218-123', self.cfg)
        sid9  = snapshots.SID('20160419-003218-123', self.cfg)
        sid10 = snapshots.SID('20160418-003218-123', self.cfg)
        sid11 = snapshots.SID('20160417-033218-123', self.cfg)
        sid12 = snapshots.SID('20160417-003218-123', self.cfg)
        sid13 = snapshots.SID('20160416-134327-123', self.cfg)
        sid14 = snapshots.SID('20160416-114327-123', self.cfg)
        sid15 = snapshots.SID('20160415-134327-123', self.cfg)
        sid16 = snapshots.SID('20160411-134327-123', self.cfg)
        sid17 = snapshots.SID('20160410-134327-123', self.cfg)
        sid18 = snapshots.SID('20160409-134327-123', self.cfg)
        sid19 = snapshots.SID('20160407-134327-123', self.cfg)
        sid20 = snapshots.SID('20160403-134327-123', self.cfg)
        sid21 = snapshots.SID('20160402-134327-123', self.cfg)
        sid22 = snapshots.SID('20160401-134327-123', self.cfg)
        sid23 = snapshots.SID('20160331-134327-123', self.cfg)
        sid24 = snapshots.SID('20160330-134327-123', self.cfg)
        sid25 = snapshots.SID('20160323-133715-123', self.cfg)
        sid26 = snapshots.SID('20160214-134327-123', self.cfg)
        sid27 = snapshots.SID('20160205-134327-123', self.cfg)
        sid28 = snapshots.SID('20160109-134327-123', self.cfg)
        sid29 = snapshots.SID('20151224-134327-123', self.cfg)
        sid30 = snapshots.SID('20150904-134327-123', self.cfg)
        sid31 = snapshots.SID('20140904-134327-123', self.cfg)

        sids = [       sid1,  sid2,  sid3,  sid4,  sid5,  sid6,  sid7,  sid8,  sid9,
                sid10, sid11, sid12, sid13, sid14, sid15, sid16, sid17, sid18, sid19,
                sid20, sid21, sid22, sid23, sid24, sid25, sid26, sid27, sid28, sid29,
                sid30, sid31]
        for sid in sids:
            sid.makeDirs()
        now = datetime(2016, 4, 24, 21, 51, 34)

        del_snapshots = self.sn._smart_remove_list(now,
                                                   3, #keep_all
                                                   7, #keep_one_per_day
                                                   5, #keep_one_per_week
                                                   3  #keep_one_per_month
                                                   )
        self.assertListEqual(del_snapshots, [sid6, sid9, sid12, sid13, sid14,
                                             sid15, sid16, sid18, sid19, sid21,
                                             sid22, sid24, sid27, sid28, sid30])

    @unittest.skip('Not yet implemented')
    def test_smart_remove(self):
        pass

class TestSnapshotWithSID(generic.SnapshotsWithSidTestCase):
    def test_save_config_file(self):
        self.sn.save_config_file(self.sid)
        self.assertTrue(os.path.isfile(self.sid.path('config')))
        self.assertEqual(tools._get_md5sum_from_path(self.sid.path('config')),
                         tools._get_md5sum_from_path(self.cfgFile))

    def test_save_snapshot_info(self):
        self.sn.save_snapshot_info(self.sid)
        self.assertTrue(os.path.isfile(self.sid.path('info')))
        with open(self.sid.path('info'), 'rt') as f:
            self.assertRegex(f.read(), re.compile('''filesystem_mounts=.+
group.size=.+
snapshot_date=20151219-010324
snapshot_machine=.+
snapshot_profile_id=1
snapshot_tag=123
snapshot_user=.+
snapshot_version=.+
user.size=.+''', re.MULTILINE))

    def test_save_permissions(self):
        #TODO: add test for save permissions over SSH (and one SSH-test for path with spaces)
        infoFilePath = os.path.join(self.snapshotPath,
                                    '20151219-010324-123',
                                    'fileinfo.bz2')

        include = self.cfg.get_include()[0][0]
        with TemporaryDirectory(dir = include) as tmp:
            file_path = os.path.join(tmp, 'foo')
            with open(file_path, 'wt') as f:
                f.write('bar')
                f.flush()

            self.sid.makeDirs(tmp)
            with open(self.sid.pathBackup(file_path), 'wt') as snapshot_f:
                snapshot_f.write('bar')
                snapshot_f.flush()

            self.sn.save_permissions(self.sid)

            fileInfo = self.sid.fileInfo
            self.assertTrue(os.path.isfile(infoFilePath))
            self.assertIn(include.encode(), fileInfo)
            self.assertIn(tmp.encode(), fileInfo)
            self.assertIn(file_path.encode(), fileInfo)

    def test_save_path_info(self):
        # force permissions because different distributions will have different umask
        os.chmod(self.testDirFullPath, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        os.chmod(self.testFileFullPath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

        d = snapshots.FileInfoDict()
        testDir  = self.testDirFullPath.encode()
        testFile = self.testFileFullPath.encode()
        self.sn._save_path_info(d, testDir)
        self.sn._save_path_info(d, testFile)

        self.assertIn(testDir, d)
        self.assertIn(testFile, d)
        self.assertTupleEqual(d[testDir],  (16893, CURRENTUSER.encode(), CURRENTGROUP.encode()))
        self.assertTupleEqual(d[testFile], (33204, CURRENTUSER.encode(), CURRENTGROUP.encode()))

class TestRestorePathInfo(generic.SnapshotsTestCase):
    def setUp(self):
        self.pathFolder = '/tmp/test/foo'
        self.pathFile   = '/tmp/test/bar'
        if os.path.exists(self.pathFolder):
            shutil.rmtree(self.pathFolder)
        if os.path.exists(self.pathFile):
            os.remove(self.pathFile)
        os.makedirs(self.pathFolder)
        with open(self.pathFile, 'wt') as f:
            pass

        self.modeFolder = os.stat(self.pathFolder).st_mode
        self.modeFile   = os.stat(self.pathFile).st_mode

        super(TestRestorePathInfo, self).setUp()

    def tearDown(self):
        super(TestRestorePathInfo, self).tearDown()
        if os.path.exists(self.pathFolder):
            shutil.rmtree(self.pathFolder)
        if os.path.exists(self.pathFile):
            os.remove(self.pathFile)

    def test_no_changes(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.fail,
                             'callback function was called unexpectedly')
        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    #TODO: add fakeroot tests with https://github.com/yaybu/fakechroot
    @unittest.skipIf(IS_ROOT, "We're running as root. So this test won't work.")
    def test_change_owner_without_root(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chown /tmp/test/(?:foo|bar) 0 : {} : \w+$'.format(CURRENTGID))

        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)
        self.run, self.sn.restore_permission_failed = False, False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    @unittest.skipIf(NO_GROUPS, "Current user is in no other group. So this test won't work.")
    def test_change_group(self):
        newGroup = GROUPS[0]
        newGID = grp.getgrnam(newGroup).gr_gid
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chgrp /tmp/test/(?:foo|bar) {}$'.format(newGID))

        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)
        self.run = False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, newGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, newGID)

    def test_change_permissions(self):
        newModeFolder = 16832 #rwx------
        newModeFile   = 33152 #rw-------
        d = snapshots.FileInfoDict()
        d[b'foo'] = (newModeFolder, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (newModeFile, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chmod /tmp/test/(?:foo|bar) \d+$')
        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)
        self.run = False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, newModeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, newModeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

class TestDeletePath(generic.SnapshotsWithSidTestCase):
    def test_delete_file(self):
        self.assertTrue(os.path.exists(self.testFileFullPath))
        self.sn.delete_path(self.sid, self.testFile)
        self.assertFalse(os.path.exists(self.testFileFullPath))

    def test_delete_file_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        self.sn.delete_path(self.sid, self.testFile)
        self.assertFalse(os.path.exists(self.testFileFullPath))

    def test_delete_dir(self):
        self.assertTrue(os.path.exists(self.testDirFullPath))
        self.sn.delete_path(self.sid, self.testDir)
        self.assertFalse(os.path.exists(self.testDirFullPath))

    def test_delete_dir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.delete_path(self.sid, self.testDir)
        self.assertFalse(os.path.exists(self.testDirFullPath))

    def test_delete_pardir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.delete_path(self.sid, 'foo')
        self.assertFalse(os.path.exists(self.testDirFullPath))

class TestRemoveSnapshot(generic.SnapshotsWithSidTestCase):
    #TODO: add test with SSH
    def test_remove_snapshot(self):
        self.assertTrue(self.sid.exists())
        self.sn.remove_snapshot(self.sid)
        self.assertFalse(self.sid.exists())

    def test_remove_snapshot_read_only(self):
        for path in (self.sid.pathBackup(), self.testDirFullPath):
            os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)
        os.chmod(self.testFileFullPath, stat.S_IRUSR)

        self.assertTrue(self.sid.exists())
        self.sn.remove_snapshot(self.sid)
        self.assertFalse(self.sid.exists())

@unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestSshSnapshots(generic.SSHTestCase):
    def setUp(self):
        super(TestSshSnapshots, self).setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        os.mkdir(self.remotePath)

    def test_stat_free_space_ssh(self):
        self.assertIsInstance(self.sn._stat_free_space_ssh(), int)

class TestSID(generic.SnapshotsTestCase):
    def test_new_object_with_valid_date(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid2 = snapshots.SID('20151219-010324', self.cfg)
        sid3 = snapshots.SID(datetime(2015, 12, 19, 1, 3, 24), self.cfg)
        sid4 = snapshots.SID(date(2015, 12, 19), self.cfg)

        self.assertEqual(sid1.sid,  '20151219-010324-123')
        self.assertEqual(sid2.sid,  '20151219-010324')
        self.assertRegex(sid3.sid, r'20151219-010324-\d{3}')
        self.assertRegex(sid4.sid, r'20151219-000000-\d{3}')

    def test_new_object_with_invalid_value(self):
        with self.assertRaises(ValueError):
            snapshots.SID('20151219-010324-1234', self.cfg)
        with self.assertRaises(ValueError):
            snapshots.SID('20151219-01032', self.cfg)
        with self.assertRaises(ValueError):
            snapshots.SID('2015121a-010324-1234', self.cfg)

    def test_new_object_with_invalid_type(self):
        with self.assertRaises(TypeError):
            snapshots.SID(123, self.cfg)

    def test_equal_sid(self):
        sid1a = snapshots.SID('20151219-010324-123', self.cfg)
        sid1b = snapshots.SID('20151219-010324-123', self.cfg)
        sid2  = snapshots.SID('20151219-020324-123', self.cfg)

        self.assertIsNot(sid1a, sid1b)
        self.assertTrue(sid1a == sid1b)
        self.assertTrue(sid1a == '20151219-010324-123')
        self.assertTrue(sid1a != sid2)
        self.assertTrue(sid1a != '20151219-020324-123')

    def test_sort_sids(self):
        root = snapshots.RootSnapshot(self.cfg)
        new  = snapshots.NewSnapshot(self.cfg)
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid2 = snapshots.SID('20151219-020324-123', self.cfg)
        sid3 = snapshots.SID('20151219-030324-123', self.cfg)
        sid4 = snapshots.SID('20151219-040324-123', self.cfg)

        sids1 = [sid3, sid1, sid4, sid2]
        sids1.sort()
        self.assertEqual(sids1, [sid1, sid2, sid3, sid4])

        #RootSnapshot 'Now' should always stay on top
        sids2 = [sid3, sid1, root, sid4, sid2]
        sids2.sort()
        self.assertEqual(sids2, [sid1, sid2, sid3, sid4, root])

        sids2.sort(reverse = True)
        self.assertEqual(sids2, [root, sid4, sid3, sid2, sid1])

        #new_snapshot should always be the last
        sids3 = [sid3, sid1, new, sid4, sid2]
        sids3.sort()
        self.assertEqual(sids3, [sid1, sid2, sid3, sid4, new])

        sids3.sort(reverse = True)
        self.assertEqual(sids3, [new, sid4, sid3, sid2, sid1])

    def test_hash(self):
        sid1a = snapshots.SID('20151219-010324-123', self.cfg)
        sid1b = snapshots.SID('20151219-010324-123', self.cfg)
        sid2  = snapshots.SID('20151219-020324-123', self.cfg)

        self.assertEqual(sid1a.__hash__(), sid1b.__hash__())
        self.assertNotEqual(sid1a.__hash__(), sid2.__hash__())

        s = set()
        s.add(sid1a)
        self.assertEqual(len(s), 1)
        s.add(sid2)
        self.assertEqual(len(s), 2)
        s.add(sid1b)
        self.assertEqual(len(s), 2)

    def test_split(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertTupleEqual(sid.split(), (2015, 12, 19, 1, 3, 24))

    def test_displayID(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.displayID, '2015-12-19 01:03:24')

    def test_displayName(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        with open(sid.path('name'), 'wt') as f:
            f.write('foo')

        self.assertEqual(sid.displayName, '2015-12-19 01:03:24 - foo')

        with open(sid.path('failed'), 'wt') as f:
            pass

        self.assertRegex(sid.displayName, r'2015-12-19 01:03:24 - foo (.+?)')

    def test_withoutTag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.withoutTag, '20151219-010324')

    def test_tag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.tag, '123')

    def test_path(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.path(),
                         os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertEqual(sid.path('foo', 'bar', 'baz'),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'foo', 'bar', 'baz'))
        self.assertEqual(sid.pathBackup(),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'backup'))
        self.assertEqual(sid.pathBackup('/foo'),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'backup', 'foo'))

    def test_makeDirs(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertTrue(sid.makeDirs())
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   '20151219-010324-123',
                                                   'backup')))

        self.assertTrue(sid.makeDirs('foo', 'bar', 'baz'))
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   '20151219-010324-123',
                                                   'backup',
                                                   'foo', 'bar', 'baz')))

    def test_exists(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertFalse(sid.exists())

        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertFalse(sid.exists())

        os.makedirs(os.path.join(self.snapshotPath,
                                 '20151219-010324-123',
                                 'backup'))
        self.assertTrue(sid.exists())

    def test_canOpenPath(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        backupPath = os.path.join(self.snapshotPath,
                                  '20151219-010324-123',
                                  'backup')
        os.makedirs(os.path.join(backupPath, 'foo'))

        #test existing file and non existing file
        self.assertTrue(sid.canOpenPath('/foo'))
        self.assertFalse(sid.canOpenPath('/tmp'))

        #test valid absolut symlink inside snapshot
        os.symlink(os.path.join(backupPath, 'foo'),
                   os.path.join(backupPath, 'bar'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'bar')))
        self.assertTrue(sid.canOpenPath('/bar'))

        #test valid relativ symlink inside snapshot
        os.symlink('./foo',
                   os.path.join(backupPath, 'baz'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'baz')))
        self.assertTrue(sid.canOpenPath('/baz'))

        #test invalid symlink
        os.symlink(os.path.join(backupPath, 'asdf'),
                   os.path.join(backupPath, 'qwer'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'qwer')))
        self.assertFalse(sid.canOpenPath('/qwer'))

        #test valid symlink outside snapshot
        os.symlink('/tmp',
                   os.path.join(backupPath, 'bla'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'bla')))
        self.assertFalse(sid.canOpenPath('/bla'))

    def test_name(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertEqual(sid.name, '')

        sid.name = 'foo'
        with open(sid.path('name'), 'rt') as f:
            self.assertEqual(f.read(), 'foo')

        self.assertEqual(sid.name, 'foo')

    def test_lastChecked(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        #no info file
        self.assertEqual(sid.lastChecked, '2015-12-19 01:03:24')

        #set time manually to 2015-12-19 02:03:24
        with open(infoFile, 'wt'):
            pass
        d = datetime(2015, 12, 19, 2, 3, 24)
        os.utime(infoFile, (d.timestamp(), d.timestamp()))
        self.assertEqual(sid.lastChecked, '2015-12-19 02:03:24')

        #setLastChecked and check if it matches current date
        sid.setLastChecked()
        now = datetime.now()
        self.assertRegex(sid.lastChecked, now.strftime(r'%Y-%m-%d %H:%M:\d{2}'))

    def test_failed(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        snapshotPath = os.path.join(self.snapshotPath, '20151219-010324-123')
        failedPath   = os.path.join(snapshotPath, sid.FAILED)
        os.makedirs(snapshotPath)

        self.assertFalse(os.path.exists(failedPath))
        self.assertFalse(sid.failed)
        sid.failed = True
        self.assertTrue(os.path.exists(failedPath))
        self.assertTrue(sid.failed)

        sid.failed = False
        self.assertFalse(os.path.exists(failedPath))
        self.assertFalse(sid.failed)

    def test_info(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        i1 = configfile.ConfigFile()
        i1.set_str_value('foo', 'bar')
        sid1.info = i1

        #test if file exist and has correct content
        self.assertTrue(os.path.isfile(infoFile))
        with open(infoFile, 'rt') as f:
            self.assertEqual(f.read(), 'foo=bar\n')

        #new sid instance and test if correct value is returned
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        i2 = sid2.info
        self.assertEqual(i2.get_str_value('foo', 'default'), 'bar')

    def test_fileInfo(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath,
                                '20151219-010324-123',
                                'fileinfo.bz2')

        d = snapshots.FileInfoDict()
        d[b'/tmp']     = (123, b'foo', b'bar')
        d[b'/tmp/foo'] = (456, b'asdf', b'qwer')
        sid1.fileInfo = d

        self.assertTrue(os.path.isfile(infoFile))

        #load fileInfo in a new snapshot
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertDictEqual(sid2.fileInfo, d)

    def test_log(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        #no log available
        self.assertRegex('\n'.join(sid.log()), r'Failed to get snapshot log from.*')

        sid.setLog('foo bar\nbaz')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual('\n'.join(sid.log()), 'foo bar\nbaz')

    def test_log_filter(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        sid.setLog('foo bar\n[I] 123\n[C] baz\n[E] bla')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual('\n'.join(sid.log(mode = LogFilter.CHANGES)), 'foo bar\n[C] baz')

    def test_setLog_binary(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        sid.setLog(b'foo bar\nbaz')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual('\n'.join(sid.log()), 'foo bar\nbaz')

    def test_makeWriteable(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        sidPath = os.path.join(self.snapshotPath, '20151219-010324-123')
        testFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'test')

        #make only read and exploreable
        os.chmod(sidPath, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaises(PermissionError):
            with open(testFile, 'wt') as f:
                f.write('foo')

        sid.makeWriteable()

        self.assertEqual(os.stat(sidPath).st_mode & stat.S_IWUSR, stat.S_IWUSR)
        try:
            with open(testFile, 'wt') as f:
                f.write('foo')
        except PermissionError:
            msg = 'writing to {} raised PermissionError unexpectedly!'
            self.fail(msg.format(testFile))

class TestNewSnapshot(generic.SnapshotsTestCase):
    def test_create_new(self):
        new = snapshots.NewSnapshot(self.cfg)
        self.assertFalse(new.exists())

        self.assertTrue(new.makeDirs())
        self.assertTrue(new.exists())
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   new.NEWSNAPSHOT,
                                                   'backup')))

    def test_saveToContinue(self):
        new = snapshots.NewSnapshot(self.cfg)
        snapshotPath = os.path.join(self.snapshotPath, new.NEWSNAPSHOT)
        saveToContinuePath = os.path.join(snapshotPath, new.SAVETOCONTINUE)
        os.makedirs(snapshotPath)

        self.assertFalse(os.path.exists(saveToContinuePath))
        self.assertFalse(new.saveToContinue)

        new.saveToContinue = True
        self.assertTrue(os.path.exists(saveToContinuePath))
        self.assertTrue(new.saveToContinue)

        new.saveToContinue = False
        self.assertFalse(os.path.exists(saveToContinuePath))
        self.assertFalse(new.saveToContinue)

class TestRootSnapshot(generic.SnapshotsTestCase):
    #TODO: add test with 'sid.path(use_mode=['ssh_encfs'])'
    def test_create(self):
        sid = snapshots.RootSnapshot(self.cfg)
        self.assertTrue(sid.isRoot)
        self.assertEqual(sid.sid, '/')
        self.assertEqual(sid.name, 'Now')

    def test_path(self):
        sid = snapshots.RootSnapshot(self.cfg)
        self.assertEqual(sid.path(), '/')
        self.assertEqual(sid.path('foo', 'bar'), '/foo/bar')

class TestIterSnapshots(generic.SnapshotsTestCase):
    def setUp(self):
        super(TestIterSnapshots, self).setUp()

        for i in ('20151219-010324-123',
                  '20151219-020324-123',
                  '20151219-030324-123',
                  '20151219-040324-123'):
            os.makedirs(os.path.join(self.snapshotPath, i, 'backup'))

    def test_list_valid(self):
        l1 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l1, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])
        self.assertIsInstance(l1[0], snapshots.SID)

    def test_list_new_snapshot(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l2 = snapshots.listSnapshots(self.cfg, includeNewSnapshot = True)
        self.assertListEqual(l2, ['new_snapshot',
                                  '20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])
        self.assertIsInstance(l2[0], snapshots.NewSnapshot)
        self.assertIsInstance(l2[-1], snapshots.SID)

    def test_list_snapshot_without_backup(self):
        #new snapshot without backup folder should't be added
        os.makedirs(os.path.join(self.snapshotPath, '20151219-050324-123'))
        l3 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l3, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_invalid_snapshot(self):
        #invalid snapshot shouldn't be added
        os.makedirs(os.path.join(self.snapshotPath,
                                 '20151219-000324-abc',
                                 'backup'))
        l4 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l4, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_without_new_snapshot(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l5 = snapshots.listSnapshots(self.cfg, includeNewSnapshot = False)
        self.assertListEqual(l5, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_symlink_last_snapshot(self):
        os.symlink('./20151219-040324-123',
                   os.path.join(self.snapshotPath, 'last_snapshot'))
        l6 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l6, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_not_reverse(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l7 = snapshots.listSnapshots(self.cfg,
                                     includeNewSnapshot = True,
                                     reverse = False)
        self.assertListEqual(l7, ['20151219-010324-123',
                                  '20151219-020324-123',
                                  '20151219-030324-123',
                                  '20151219-040324-123',
                                  'new_snapshot'])
        self.assertIsInstance(l7[0], snapshots.SID)
        self.assertIsInstance(l7[-1], snapshots.NewSnapshot)

    def test_iter_snapshots(self):
        for i, sid in enumerate(snapshots.iterSnapshots(self.cfg)):
            self.assertIn(sid, ['20151219-040324-123',
                                '20151219-030324-123',
                                '20151219-020324-123',
                                '20151219-010324-123'])
            self.assertIsInstance(sid, snapshots.SID)
        self.assertEqual(i, 3)

    def test_lastSnapshot(self):
        self.assertEqual(snapshots.lastSnapshot(self.cfg),
                         '20151219-040324-123')

if __name__ == '__main__':
    unittest.main()
