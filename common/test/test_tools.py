# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raack
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about the tools module."""
import os
import sys
import subprocess
import random
import pathlib
import gzip
import stat
import signal
import unittest
from datetime import datetime
from time import sleep
from unittest.mock import patch
from copy import deepcopy
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tools
import configfile
from bitbase import TimeUnit

# chroot jails used for building may have no UUID devices (because of tmpfs)
# we need to skip tests that require UUIDs
DISK_BY_UUID_AVAILABLE = os.path.exists(tools.DISK_BY_UUID)

UDEVADM_HAS_UUID = subprocess.Popen(
    ['udevadm', 'info', '-e'],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL).communicate()[0].find(b'ID_FS_UUID=') > 0

RSYNC_INSTALLED = tools.checkCommand('rsync')

RSYNC_307_VERSION = """rsync  version 3.0.7  protocol version 30
Copyright (C) 1996-2009 by Andrew Tridgell, Wayne Davison, and others.
Web site: http://rsync.samba.org/
Capabilities:
    64-bit files, 64-bit inums, 32-bit timestamps, 64-bit long ints,
    socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
    append, ACLs, xattrs, iconv, symtimes

rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
are welcome to redistribute it under certain conditions.  See the GNU
General Public License for details.
"""

RSYNC_310_VERSION = """rsync  version 3.1.0  protocol version 31
Copyright (C) 1996-2013 by Andrew Tridgell, Wayne Davison, and others.
Web site: http://rsync.samba.org/
Capabilities:
    64-bit files, 64-bit inums, 64-bit timestamps, 64-bit long ints,
    socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
    append, ACLs, xattrs, iconv, symtimes, prealloc

rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
are welcome to redistribute it under certain conditions.  See the GNU
General Public License for details.
"""


class TestTools(generic.TestCase):
    """
    All functions test here come from tools.py
    """

    def setUp(self):
        super().setUp()
        self.subproc = None

    def tearDown(self):
        super().tearDown()
        self._kill_process()

    def _create_process(self, *args):
        dummyPath = os.path.join(os.path.dirname(__file__), generic.DUMMY)
        cmd = [dummyPath]
        cmd.extend(args)
        self.subproc = subprocess.Popen(cmd)
        sleep(0.1)
        return self.subproc.pid

    def _kill_process(self):
        if self.subproc:
            self.subproc.kill()
            self.subproc.wait()
        self.subproc = None

    def test_sharePath(self):
        share = tools.sharePath()
        self.assertTrue(share.endswith('share'), 'share = {}'.format(share))

    def test_backintimePath(self):
        path = tools.backintimePath('common')
        self.assertIn(path, __file__)

    def test_registerBackintimePath(self):
        path = tools.backintimePath('foo')
        tools.registerBackintimePath('foo')
        self.assertIn(path, sys.path)
        sys.path.remove(path)

    def test_runningFromSource(self):
        self.assertTrue(tools.runningFromSource())

    def test_addSourceToPathEnviron(self):
        source = tools.backintimePath('common')
        path = [x for x in os.getenv('PATH').split(':') if x != source]
        os.environ['PATH'] = ':'.join(path)

        tools.addSourceToPathEnviron()
        self.assertIn(source, os.environ['PATH'])

    def test_readFile(self):
        """
        Test the function readFile
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")

        self.assertIsInstance(tools.readFile(test_tools_file), str)
        self.assertIsNone(tools.readFile(non_existing_file))

        with NamedTemporaryFile('wt') as tmp:
            tmp.write('foo\nbar')
            tmp.flush()
            self.assertIsInstance(tools.readFile(tmp.name), str)
            self.assertEqual(tools.readFile(tmp.name), 'foo\nbar')

        tmp_gz = NamedTemporaryFile().name
        with gzip.open(tmp_gz + '.gz', 'wt') as f:
            f.write('foo\nbar')
            f.flush()
        self.assertIsInstance(tools.readFile(tmp_gz), str)
        self.assertEqual(tools.readFile(tmp_gz), 'foo\nbar')
        os.remove(tmp_gz + '.gz')

    def test_readFileLines(self):
        """
        Test the function readFileLines
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")

        output = tools.readFileLines(test_tools_file)
        self.assertIsInstance(output, list)
        self.assertGreaterEqual(len(output), 1)
        self.assertIsInstance(output[0], str)
        self.assertIsNone(tools.readFileLines(non_existing_file))

        with NamedTemporaryFile('wt') as tmp:
            tmp.write('foo\nbar')
            tmp.flush()
            self.assertIsInstance(tools.readFileLines(tmp.name), list)
            self.assertListEqual(tools.readFileLines(tmp.name), ['foo', 'bar'])

        tmp_gz = NamedTemporaryFile().name
        with gzip.open(tmp_gz + '.gz', 'wt') as f:
            f.write('foo\nbar')
            f.flush()
        self.assertIsInstance(tools.readFileLines(tmp_gz), list)
        self.assertEqual(tools.readFileLines(tmp_gz), ['foo', 'bar'])
        os.remove(tmp_gz + '.gz')

    def test_checkCommand(self):
        """
        Test the function checkCommand
        """
        self.assertFalse(tools.checkCommand(''))
        self.assertFalse(tools.checkCommand("notExistedCommand"))
        self.assertTrue(tools.checkCommand("ls"))
        self.assertTrue(tools.checkCommand('backintime'))

    def test_which(self):
        """
        Test the function which
        """
        self.assertRegex(tools.which("ls"), r'/.*/ls')
        self.assertEqual(tools.which('backintime'),
                         os.path.join(os.getcwd(), 'backintime'))
        self.assertIsNone(tools.which("notExistedCommand"))

    def test_makeDirs(self):
        self.assertFalse(tools.makeDirs('/'))
        self.assertTrue(tools.makeDirs(os.getcwd()))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo', 'bar')
            self.assertTrue(tools.makeDirs(path))

    def test_makeDirs_not_writable(self):
        with TemporaryDirectory() as d:
            os.chmod(d, stat.S_IRUSR)
            path = os.path.join(
                d, 'foobar{}'.format(random.randrange(100, 999)))
            self.assertFalse(tools.makeDirs(path))

    def test_mkdir(self):
        self.assertFalse(tools.mkdir('/'))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo')
            self.assertTrue(tools.mkdir(path))
            for mode in (0o700, 0o644, 0o777):
                msg = 'new path should have octal permissions {0:#o}' \
                      .format(mode)
                path = os.path.join(d, '{0:#o}'.format(mode))
                self.assertTrue(tools.mkdir(path, mode), msg)
                self.assertEqual(
                    '{0:o}'.format(os.stat(path).st_mode & 0o777),
                    '{0:o}'.format(mode), msg)

    def test_pids(self):
        pids = tools.pids()
        self.assertGreater(len(pids), 0)
        self.assertIn(os.getpid(), pids)

    def test_processStat(self):
        pid = self._create_process()
        stat = tools.processStat(pid)
        self.assertRegex(
            stat, r'{} \({}\) \w .*'.format(pid, generic.DUMMY[:15]))

    @patch('builtins.open')
    def test_processStat_exception(self, mock_open):
        mock_open.side_effect = OSError()
        pid = self._create_process()
        self.assertEqual(tools.processStat(pid), '')

    def test_processPaused(self):
        pid = self._create_process()
        self.assertFalse(tools.processPaused(pid))
        self.subproc.send_signal(signal.SIGSTOP)
        sleep(0.01)
        self.assertTrue(tools.processPaused(pid))
        self.subproc.send_signal(signal.SIGCONT)
        sleep(0.01)
        self.assertFalse(tools.processPaused(pid))

    def test_processName(self):
        pid = self._create_process()
        self.assertEqual(tools.processName(pid), generic.DUMMY[:15])

    def test_processCmdline(self):
        pid = self._create_process()
        self.assertRegex(tools.processCmdline(pid),
                         r'.*/sh.*/common/test/dummy_test_process\.sh')
        self._kill_process()
        pid = self._create_process('foo', 'bar')
        self.assertRegex(tools.processCmdline(pid),
                         r'.*/sh.*/common/test/dummy_test_process\.sh.foo.bar')

    @patch('builtins.open')
    def test_processCmdline_exception(self, mock_open):
        mock_open.side_effect = OSError()
        pid = self._create_process()
        self.assertEqual(tools.processCmdline(pid), '')

    def test_pidsWithName(self):
        self.assertEqual(len(tools.pidsWithName('nonExistingProcess')), 0)
        pid = self._create_process()
        pids = tools.pidsWithName(generic.DUMMY)
        self.assertGreaterEqual(len(pids), 1)
        self.assertIn(pid, pids)

    def test_processExists(self):
        self.assertFalse(tools.processExists('nonExistingProcess'))
        self._create_process()
        self.assertTrue(tools.processExists(generic.DUMMY))

    def test_processAlive(self):
        """
        Test the function processAlive
        """
        # TODO: add test (in chroot) running proc as root and kill as non-root
        self.assertTrue(tools.processAlive(os.getpid()))
        pid = self._create_process()
        self.assertTrue(tools.processAlive(pid))
        self._kill_process()
        self.assertFalse(tools.processAlive(pid))
        self.assertFalse(tools.processAlive(999999))
        with self.assertRaises(ValueError):
            tools.processAlive(0)
        self.assertFalse(tools.processAlive(-1))

    def test_checkXServer(self):
        try:
            tools.checkXServer()
        except Exception as e:
            self.fail(
                'tools.ckeck_x_server() raised exception {}'.format(str(e)))

    def test_preparePath(self):
        path_with_slash_at_begin = "/test/path"
        path_without_slash_at_begin = "test/path"
        path_with_slash_at_end = "/test/path/"
        path_without_slash_at_end = "/test/path"
        self.assertEqual(
            tools.preparePath(path_with_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEqual(
            tools.preparePath(path_without_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEqual(
            tools.preparePath(path_without_slash_at_end),
            path_without_slash_at_end)
        self.assertEqual(
            tools.preparePath(path_with_slash_at_end),
            path_without_slash_at_end)

    def test_powerStatusAvailable(self):
        if tools.processExists('upowerd') and not generic.ON_TRAVIS:
            self.assertTrue(tools.powerStatusAvailable())
        else:
            self.assertFalse(tools.powerStatusAvailable())
        self.assertIsInstance(tools.onBattery(), bool)

    def test_rsyncCaps(self):
        if RSYNC_INSTALLED:
            caps = tools.rsyncCaps()
            self.assertIsInstance(caps, list)
            self.assertGreaterEqual(len(caps), 1)

        self.assertListEqual(tools.rsyncCaps(data=RSYNC_307_VERSION),
                             ['64-bit files',
                              '64-bit inums',
                              '32-bit timestamps',
                              '64-bit long ints',
                              'socketpairs',
                              'hardlinks',
                              'symlinks',
                              'IPv6',
                              'batchfiles',
                              'inplace',
                              'append',
                              'ACLs',
                              'xattrs',
                              'iconv',
                              'symtimes'])

        self.assertListEqual(tools.rsyncCaps(data=RSYNC_310_VERSION),
                             ['progress2',
                              '64-bit files',
                              '64-bit inums',
                              '64-bit timestamps',
                              '64-bit long ints',
                              'socketpairs',
                              'hardlinks',
                              'symlinks',
                              'IPv6',
                              'batchfiles',
                              'inplace',
                              'append',
                              'ACLs',
                              'xattrs',
                              'iconv',
                              'symtimes',
                              'prealloc'])

    def test_md5sum(self):
        with NamedTemporaryFile() as f:
            f.write(b'foo')
            f.flush()

            self.assertEqual(tools.md5sum(f.name),
                             'acbd18db4cc2f85cedef654fccc4a4d8')

    def test_checkCronPattern(self):
        self.assertTrue(tools.checkCronPattern('0'))
        self.assertTrue(tools.checkCronPattern('0,10,13,15,17,20,23'))
        self.assertTrue(tools.checkCronPattern('*/6'))
        self.assertFalse(tools.checkCronPattern('a'))
        self.assertFalse(tools.checkCronPattern(' 1'))
        self.assertFalse(tools.checkCronPattern('0,10,13,1a,17,20,23'))
        self.assertFalse(tools.checkCronPattern('0,10,13, 15,17,20,23'))
        self.assertFalse(tools.checkCronPattern('*/6,8'))
        self.assertFalse(tools.checkCronPattern('*/6 a'))

    def test_mountpoint(self):
        self.assertEqual(tools.mountpoint('/nonExistingFolder/foo/bar'), '/')
        proc = os.path.join('/proc', str(os.getpid()), 'fd')
        self.assertEqual(tools.mountpoint(proc), '/proc')

    def test_decodeOctalEscape(self):
        self.assertEqual(tools.decodeOctalEscape('/mnt/normalPath'),
                         '/mnt/normalPath')
        self.assertEqual(
            tools.decodeOctalEscape('/mnt/path\\040with\\040space'),
            '/mnt/path with space')

    def test_mountArgs(self):
        rootArgs = tools.mountArgs('/')
        self.assertIsInstance(rootArgs, list)
        self.assertGreaterEqual(len(rootArgs), 3)
        self.assertEqual(rootArgs[1], '/')

        procArgs = tools.mountArgs('/proc')
        self.assertGreaterEqual(len(procArgs), 3)
        self.assertEqual(procArgs[0], 'proc')
        self.assertEqual(procArgs[1], '/proc')
        self.assertEqual(procArgs[2], 'proc')

    def test_isRoot(self):
        self.assertIsInstance(tools.isRoot(), bool)

    def test_usingSudo(self):
        self.assertIsInstance(tools.usingSudo(), bool)

    def test_patternHasNotEncryptableWildcard(self):
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/*/bar'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/**/bar'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('*/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('**/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/*'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/**'))

        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo?'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo[1-2]'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('**foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*.foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo**bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*/bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo**/bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/*bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/**bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/*/bar*'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*foo/*/bar'))

    def test_readTimeStamp(self):
        with NamedTemporaryFile('wt') as f:
            f.write('20160127 0124')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 1, 24))

        with NamedTemporaryFile('wt') as f:
            f.write('20160127')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 0, 0))

    def test_writeTimeStamp(self):
        with NamedTemporaryFile('rt') as f:
            tools.writeTimeStamp(f.name)
            s = f.read().strip('\n')
            self.assertTrue(s.replace(' ', '').isdigit())
            self.assertEqual(len(s), 13)

    def test_splitCommands(self):
        ret = list(tools.splitCommands(['echo foo;'],
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=40))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=40))
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0], 'echo start;echo foo;echo foo;echo end')
        self.assertEqual(ret[1], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=0))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0],
                         'echo start;echo foo;echo foo;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;'] * 3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=-10))
        self.assertEqual(len(ret), 1)
        self.assertEqual(
            ret[0],
            'echo start;echo foo;echo foo;echo foo;echo end')


class EscapeIPv6(generic.TestCase):
    def test_escaped(self):
        values_and_expected = (
            ('fd00:0::5', '[fd00:0::5]'),
            (
                '2001:db8:0:8d3:0:8a2e:70:7344',
                '[2001:db8:0:8d3:0:8a2e:70:7344]'
            ),
            ('::', '[::]'),
            ('::1', '[::1]'),
            ('::ffff:192.0.2.128', '[::ffff:192.0.2.128]'),
            ('fe80::1', '[fe80::1]'),
        )

        for val, exp in values_and_expected:
            with self.subTest(val=val, exp=exp):
                self.assertEqual(tools.escapeIPv6Address(val), exp)

    def test_passed(self):
        test_values = (
            '192.168.1.1',
            '172.17.1.133',
            '255.255.255.255',
            '169.254.0.1',
        )

        for val in test_values:
            with self.subTest(val=val):
                # IPv4 addresses are not escaped
                self.assertEqual(tools.escapeIPv6Address(val), val)

    def test_invalid(self):
        """Invalid IP addresses and hostnames"""
        test_values = (
            'foo.bar',
            'fd00',
            '2001:0db8:::0000:0000:8a2e:0370:7334',
            ':2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            '2001:0gb8:85a3:0000:0000:8a2e:0370:7334',
            '2001:0db8:85a3:0000:0000:8a2e:0370:7334:abcd',
            'localhost',
        )

        for val in test_values:
            with self.subTest(val=val):
                self.assertEqual(tools.escapeIPv6Address(val), val)


class Environ(generic.TestCase):
    """???
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = deepcopy(os.environ)

    def setUp(self):
        super().setUp()
        self.temp_file = '/tmp/temp.txt'
        os.environ = deepcopy(self.env)

    def tearDown(self):
        super().tearDown()
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        os.environ = deepcopy(self.env)

    def test_envLoad_without_previous_values(self):
        test_env = configfile.ConfigFile()
        test_env.setStrValue('FOO', 'bar')
        test_env.setStrValue('ASDF', 'qwertz')
        test_env.save(self.temp_file)

        # make sure environ is clean
        self.assertNotIn('FOO', os.environ)
        self.assertNotIn('ASDF', os.environ)

        tools.envLoad(self.temp_file)
        self.assertIn('FOO', os.environ)
        self.assertIn('ASDF', os.environ)
        self.assertEqual(os.environ['FOO'], 'bar')
        self.assertEqual(os.environ['ASDF'], 'qwertz')

    def test_envLoad_do_not_overwrite_previous_values(self):
        test_env = configfile.ConfigFile()
        test_env.setStrValue('FOO', 'bar')
        test_env.setStrValue('ASDF', 'qwertz')
        test_env.save(self.temp_file)

        # add some environ vars that should not get overwritten
        os.environ['FOO'] = 'defaultFOO'
        os.environ['ASDF'] = 'defaultASDF'

        tools.envLoad(self.temp_file)
        self.assertIn('FOO', os.environ)
        self.assertIn('ASDF', os.environ)
        self.assertEqual(os.environ['FOO'], 'defaultFOO')
        self.assertEqual(os.environ['ASDF'], 'defaultASDF')

    def test_envSave(self):
        keys = (
            'GNOME_KEYRING_CONTROL',
            'DBUS_SESSION_BUS_ADDRESS',
            'DBUS_SESSION_BUS_PID',
            'DBUS_SESSION_BUS_WINDOWID',
            'DISPLAY',
            'XAUTHORITY',
            'GNOME_DESKTOP_SESSION_ID',
            'KDE_FULL_SESSION')

        for i, k in enumerate(keys):
            os.environ[k] = str(i)

        tools.envSave(self.temp_file)

        self.assertIsFile(self.temp_file)

        test_env = configfile.ConfigFile()
        test_env.load(self.temp_file)
        for i, k in enumerate(keys):
            with self.subTest(i=i, k=k):
                # workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'i = %s, k = %s' % (i, k)
                self.assertEqual(test_env.strValue(k), str(i), msg)


class ExecuteSubprocess(generic.TestCase):
    # new method with subprocess
    def test_returncode(self):
        self.assertEqual(tools.Execute(['true']).run(), 0)
        self.assertEqual(tools.Execute(['false']).run(), 1)

    def test_callback(self):
        c = lambda x, y: self.callback(self.assertEqual, x, 'foo')
        tools.Execute(['echo', 'foo'], callback=c).run()
        self.assertTrue(self.run)
        self.run = False

        # give extra user_data for callback
        c = lambda x, y: self.callback(self.assertEqual, x, y)
        tools.Execute(['echo', 'foo'], callback=c, user_data='foo').run()
        self.assertTrue(self.run)
        self.run = False

        # no output
        c = lambda x, y: self.callback(self.fail,
                                       'callback was called unexpectedly')
        tools.Execute(['true'], callback=c).run()
        self.assertFalse(self.run)
        self.run = False

    def test_pausable(self):
        proc = tools.Execute(['true'])
        self.assertTrue(proc.pausable)


class Tools_FakeFS(pyfakefs_ut.TestCase):
    """Tests using a fake filesystem."""

    def setUp(self):
        self.setUpPyfakefs(allow_root_user=False)

    def test_git_repo_info_none(self):
        """Actually not a git repo"""

        self.assertEqual(tools.get_git_repository_info(), None)

    def test_git_repo_info(self):
        """Simulate a git repo"""

        path = pathlib.Path('.git')
        path.mkdir()

        # Branch folders and hash containing file
        foobar = path / 'refs' / 'heads' / 'fix' / 'foobar'
        foobar.parent.mkdir(parents=True)

        with foobar.open('w') as handle:
            handle.write('01234')

        # HEAD file
        head = path / 'HEAD'

        with head.open('w') as handle:
            handle.write('ref: refs/heads/fix/foobar')

        # Test
        self.assertEqual(
            tools.get_git_repository_info(),
            {
                'hash': '01234',
                'branch': 'fix/foobar'
            }
        )


class ValidateSnapshotsPath(generic.TestCaseCfg):
    def test_writes(self):
        with TemporaryDirectory() as dirpath:
            ret = tools.validate_and_prepare_snapshots_path(
                path=dirpath,
                host_user_profile=self.cfg.hostUserProfile(),
                mode=self.cfg.snapshotsMode(),
                copy_links=self.cfg.copyLinks(),
                error_handler=self.cfg.notifyError)
            self.assertTrue(ret)

    def test_fails_on_ro(self):
        with TemporaryDirectory() as dirpath:
            # set directory to read only
            ro_dir_stats = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            with generic.mockPermissions(dirpath, ro_dir_stats):
                ret = tools.validate_and_prepare_snapshots_path(
                    path=dirpath,
                    host_user_profile=self.cfg.hostUserProfile(),
                    mode=self.cfg.snapshotsMode(),
                    copy_links=self.cfg.copyLinks(),
                    error_handler=self.cfg.notifyError)
                self.assertFalse(ret)

    @patch('os.chmod')
    def test_permission_fail(self, mock_chmod):
        mock_chmod.side_effect = PermissionError()
        with TemporaryDirectory() as dirpath:
            ret = tools.validate_and_prepare_snapshots_path(
                path=dirpath,
                host_user_profile=self.cfg.hostUserProfile(),
                mode=self.cfg.snapshotsMode(),
                copy_links=self.cfg.copyLinks(),
                error_handler=self.cfg.notifyError)
            self.assertTrue(ret)


@patch(f'{tools.__name__}.datetime', wraps=datetime)
class OlderThan(unittest.TestCase):

    def test_hours_not_older(self, mock_dt):
        """Exact two hours

        Keep in mind: 20:23:00 is NOT two hours older than 18:23:00. But
        20:23:01 IS OLDER than two hours.
        """
        # year, month, day, hour=0, minute=0, second=0, microsecond=0
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # exact two hours
        mock_dt.now.return_value = datetime(1982, 8, 6, 20, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 2, TimeUnit.HOUR))

    def test_hours_older(self, mock_dt):
        """Two hours plus one ms"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # two hours + 1 ms
        mock_dt.now.return_value = datetime(1982, 8, 6, 20, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 2, TimeUnit.HOUR))

    def test_days_not_older(self, mock_dt):
        """Two days"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 8, 8, 18, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 2, TimeUnit.DAY))

    def test_days_older(self, mock_dt):
        """Two days plus one ms"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 8, 8, 18, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 2, TimeUnit.DAY))

    def test_week_not_older(self, mock_dt):
        """Two weeks"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 8, 20, 18, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 2, TimeUnit.WEEK))

    def test_week_older(self, mock_dt):
        """Two weeks plus one ms"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 8, 20, 18, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 2, TimeUnit.WEEK))

    def test_month_not_older(self, mock_dt):
        """Two months."""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 10, 6, 18, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 2, TimeUnit.MONTH))

    def test_month_older(self, mock_dt):
        """Two months plus one ms."""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 10, 6, 18, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 2, TimeUnit.MONTH))

    def test_month_31th(self, mock_dt):
        """From May with 31th as last day to September with 30th as last day."""
        birth = datetime(1982, 5, 31, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 9, 30, 18, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 4, TimeUnit.MONTH))

    def test_month_31th_plus_ms(self, mock_dt):
        """Plus one ms"""
        birth = datetime(1982, 5, 31, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1982, 9, 30, 18, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 4, TimeUnit.MONTH))

    def test_month_next_year(self, mock_dt):
        """Into next year with 7 months."""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1983, 3, 6, 18, 23, 0, 0)

        self.assertFalse(tools.older_than(birth, 7, TimeUnit.MONTH))

    def test_month_next_year_plus_ms(self, mock_dt):
        """Into next year with 7 months plus 1 ms."""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime(1983, 3, 6, 18, 23, 0, 1)

        self.assertTrue(tools.older_than(birth, 7, TimeUnit.MONTH))
