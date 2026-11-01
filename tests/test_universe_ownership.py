"""Finite local ownership checks; no world solve, Genesis, GPU or UE imports."""
from dataclasses import replace
import errno
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from engine.universe_authority.codec import ContractError, DeploymentContext
from engine.universe_authority.ownership import acquire

_REPOSITORY = Path(__file__).resolve().parents[1]
_MODULE = 'engine.universe_authority.ownership'
_WORLD = 'ownership-fixture'
_CHILD = '''
import json, sys
from pathlib import Path
import stat
from engine.universe_authority.codec import ContractError
from engine.universe_authority.ownership import acquire
try:
    with acquire(Path(sys.argv[1]), 'ownership-fixture') as lease:
        lease.check()
    print(json.dumps({'code':'ACQUIRED'}))
except ContractError as exc:
    print(json.dumps({'code':exc.code}))
'''


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-i2-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / 'authority'

    def expect_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertIsInstance(caught.exception.detail, str)
        self.assertLessEqual(len(caught.exception.detail.encode('utf-8')), 4096)

    def files(self):
        """Capture names/bytes/inodes, excluding atime changed by legitimate reads."""
        result = {}
        for path in sorted(self.base.rglob('*')):
            info = path.lstat()
            result[str(path.relative_to(self.base))] = (
                info.st_dev, info.st_ino,
                os.readlink(path) if path.is_symlink()
                else path.read_bytes() if path.is_file() else None,
            )
        return result

    def initialized(self):
        lease = acquire(self.root, _WORLD, initialize=True)
        self.addCleanup(lease.close)
        return lease

    def child_code(self, root=None):
        result = subprocess.run(
            [sys.executable, '-c', _CHILD, str(root or self.root)],
            cwd=_REPOSITORY, check=True, capture_output=True,
            text=True, timeout=10,
        )
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)['code']

    def test_missing_read_creates_nothing(self):
        before = self.files()
        self.expect_code('UNINITIALIZED', acquire, self.root, _WORLD)
        self.assertEqual(self.files(), before)
        self.root.mkdir()
        before = self.files()
        self.expect_code('UNINITIALIZED', acquire, self.root, _WORLD)
        self.assertEqual(self.files(), before)

    def test_read_missing_lock_or_identity_never_repairs(self):
        lease = self.initialized()
        lease.close()
        (self.root / '.authority.lock').unlink()
        before = self.files()
        self.expect_code('UNINITIALIZED', acquire, self.root, _WORLD)
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD, initialize=True)
        self.assertEqual(self.files(), before)
        (self.root / 'identity.json').unlink()
        (self.root / '.authority.lock').write_bytes(b'')
        before = self.files()
        self.expect_code('UNINITIALIZED', acquire, self.root, _WORLD)
        self.assertEqual(self.files(), before)

    def test_registration_exact_bytes_and_frozen_metadata(self):
        lease = self.initialized()
        info = self.root.stat()
        expected = {
            'domain': 'edgeworld.universe.authority', 'version': '0.1',
            'world_id': _WORLD, 'profile': 'local-posix-sync-v0.1',
            'root_canonical': str(self.root.resolve()),
            'root_device': str(info.st_dev), 'root_inode': str(info.st_ino),
        }
        self.assertEqual((self.root / 'identity.json').read_bytes(),
                         json.dumps(expected, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode('ascii'))
        self.assertEqual(lease.root, self.root.resolve())
        self.assertEqual(lease.owner_pid, os.getpid())
        self.assertTrue(lease.initializing)
        self.assertEqual(lease.world_id, _WORLD)
        self.assertEqual(lease.profile, 'local-posix-sync-v0.1')
        self.assertEqual(lease.domain_version, '0.1')
        self.assertIsNone(lease.context)
        self.assertFalse((self.root / 'HEAD.json').exists())
        self.assertEqual((self.root / '.authority.lock').read_bytes(), b'')
        with self.assertRaises(AttributeError):
            lease.world_id = 'other'
        lease.check()

    def test_same_process_competitor_and_symlink_alias_are_locked(self):
        lease = self.initialized()
        alias = self.base / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.expect_code('LOCKED', acquire, self.root, _WORLD)
        self.expect_code('LOCKED', acquire, alias, _WORLD)
        lock_inode = (self.root / '.authority.lock').stat().st_ino
        lease.close()
        with acquire(alias, _WORLD) as next_lease:
            self.assertEqual(next_lease.root, self.root.resolve())
            self.assertFalse(next_lease.initializing)
        self.assertEqual((self.root / '.authority.lock').stat().st_ino, lock_inode)

    def test_independent_process_excludes_then_releases(self):
        lease = self.initialized()
        self.assertEqual(self.child_code(), 'LOCKED')
        lease.close()
        before = self.files()
        self.assertEqual(self.child_code(), 'ACQUIRED')
        self.assertEqual(self.files(), before)

    def test_close_idempotent_and_context_exception_keeps_lockfile(self):
        lease = self.initialized()
        before = self.files()
        marker = RuntimeError('intentional context exit')
        with self.assertRaises(RuntimeError) as caught:
            with lease:
                raise marker
        self.assertIs(caught.exception, marker)
        lease.close()
        self.expect_code('CLOSED', lease.check)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.child_code(), 'ACQUIRED')

    def test_wrong_world_does_not_mutate_registration(self):
        lease = self.initialized()
        lease.close()
        before = self.files()
        self.expect_code('ROOT_MISMATCH', acquire, self.root, 'different-world')
        self.assertEqual(self.files(), before)
        self.assertEqual(self.child_code(), 'ACQUIRED')

    def test_legacy_nonempty_directory_is_not_registered(self):
        self.root.mkdir()
        (self.root / 'legacy.json').write_bytes(b'{"tick":0}')
        before = self.files()
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD, initialize=True)
        self.assertEqual(self.files(), before)

    def test_head_without_identity_is_corrupt_not_initializable(self):
        self.root.mkdir()
        (self.root / 'HEAD.json').write_bytes(b'{}')
        before = self.files()
        for initialize in (False, True):
            self.expect_code('CORRUPT', acquire, self.root, _WORLD,
                             initialize=initialize)
        self.assertEqual(self.files(), before)

    def test_partial_identity_is_not_overwritten(self):
        lease = self.initialized()
        lease.close()
        (self.root / 'identity.json').write_bytes(b'{')
        before = self.files()
        for initialize in (False, True):
            self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD,
                             initialize=initialize)
        self.assertEqual(self.files(), before)

    def test_noncanonical_or_changed_identity_rejected(self):
        lease = self.initialized()
        lease.close()
        path = self.root / 'identity.json'
        original = path.read_bytes()
        path.write_bytes(original + b'\n')
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)
        changed = json.loads(original)
        changed['root_inode'] = '0'
        path.write_text(json.dumps(changed))
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)

    def test_partially_initialized_matching_root_can_resume(self):
        lease = self.initialized()
        lease.close()
        before = self.files()
        with acquire(self.root, _WORLD, initialize=True) as resumed:
            self.assertTrue(resumed.initializing)
            resumed.check()
        self.assertEqual(self.files(), before)

    def test_existing_head_requires_recovery(self):
        lease = self.initialized()
        lease.close()
        (self.root / 'HEAD.json').write_bytes(b'{}')
        before = self.files()
        self.expect_code('NOT_READY', acquire, self.root, _WORLD, initialize=True)
        with acquire(self.root, _WORLD) as recovery_lease:
            self.assertFalse(recovery_lease.initializing)
        self.assertEqual(self.files(), before)

    def test_lock_symlink_or_hardlink_is_refused(self):
        lease = self.initialized()
        lease.close()
        lock = self.root / '.authority.lock'
        lock.unlink()
        target = self.base / 'target'
        target.write_bytes(b'')
        lock.symlink_to(target)
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)
        lock.unlink()
        os.link(target, lock)
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)
        self.assertEqual(target.read_bytes(), b'')

    def test_fifo_identity_is_refused_without_blocking(self):
        lease = self.initialized()
        lease.close()
        path = self.root / 'identity.json'
        path.unlink()
        os.mkfifo(path)
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)

    def test_identity_hardlink_refused(self):
        lease = self.initialized()
        lease.close()
        os.link(self.root / 'identity.json', self.base / 'identity-link')
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)

    def test_lock_replacement_detected_by_live_lease(self):
        lease = self.initialized()
        (self.root / '.authority.lock').rename(self.root / 'old-lock')
        (self.root / '.authority.lock').write_bytes(b'')
        self.expect_code('ROOT_MISMATCH', lease.check)

    def test_root_replacement_detected_and_close_preserves_both_roots(self):
        lease = self.initialized()
        self.root.rename(self.base / 'original-authority')
        self.root.mkdir()
        self.expect_code('ROOT_MISMATCH', lease.check)
        before = self.files()
        lease.close()
        self.assertEqual(self.files(), before)

    def test_identity_inode_replacement_detected_by_live_lease(self):
        lease = self.initialized()
        path = self.root / 'identity.json'
        raw = path.read_bytes()
        path.rename(self.root / 'old-identity')
        path.write_bytes(raw)
        self.expect_code('ROOT_MISMATCH', lease.check)

    @unittest.skipUnless(hasattr(os, 'fork'), 'requires POSIX fork')
    def test_fork_cannot_use_lease_and_child_close_keeps_parent_lock(self):
        lease = self.initialized()
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                try:
                    lease.check()
                    code = 'UNEXPECTED_SUCCESS'
                except ContractError as exc:
                    code = exc.code
                lease.close()  # Must not LOCK_UN the parent's shared description.
                os.write(write_fd, code.encode('ascii'))
                os.close(write_fd)
                os._exit(0)
            except BaseException:
                os._exit(2)
        os.close(write_fd)
        try:
            code = os.read(read_fd, 128).decode('ascii')
        finally:
            os.close(read_fd)
        actual_pid, status = os.waitpid(pid, 0)
        self.assertEqual(actual_pid, pid)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        self.assertEqual(code, 'LOCKED')
        lease.check()
        self.assertEqual(self.child_code(), 'LOCKED')
        lease.close()
        self.assertEqual(self.child_code(), 'ACQUIRED')

    def assert_descriptors_closed(self, descriptors):
        self.assertTrue(descriptors)
        for descriptor in set(descriptors):
            with self.assertRaises(OSError) as caught:
                os.fstat(descriptor)
            self.assertEqual(caught.exception.errno, errno.EBADF)

    def test_directory_sync_unsupported_fails_closed(self):
        descriptors = []
        real_open = os.open
        def tracking_open(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with mock.patch(_MODULE + '.os.open', side_effect=tracking_open), \
                mock.patch(_MODULE + '.os.fsync', side_effect=OSError(errno.EINVAL, 'injected sync failure')):
            self.expect_code('SYNC_UNSUPPORTED', acquire, self.root, _WORLD, initialize=True)
        self.assert_descriptors_closed(descriptors)
        self.assertFalse((self.root / 'identity.json').exists())
        self.assertFalse((self.root / 'HEAD.json').exists())

    def test_post_registration_directory_sync_failure_releases_lock(self):
        self.root.mkdir()
        descriptors = []
        real_open, real_fsync = os.open, os.fsync
        def tracking_open(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        def failing_directory_sync(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError(errno.EIO, 'injected post-registration directory sync')
            return real_fsync(descriptor)
        with mock.patch(_MODULE + '.os.open', side_effect=tracking_open), \
                mock.patch(_MODULE + '.os.fsync', side_effect=failing_directory_sync):
            self.expect_code('SYNC_UNSUPPORTED', acquire, self.root, _WORLD, initialize=True)
        self.assert_descriptors_closed(descriptors)
        self.assertTrue((self.root / 'identity.json').is_file())
        self.assertFalse((self.root / 'HEAD.json').exists())
        before = self.files()
        self.assertEqual(self.child_code(), 'ACQUIRED')
        self.assertEqual(self.files(), before)

    def test_short_registration_write_preserves_failure_evidence(self):
        self.root.mkdir()  # Reach identity write without a new-root parent sync.
        descriptors = []
        real_open = os.open
        def tracking_open(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with mock.patch(_MODULE + '.os.open', side_effect=tracking_open), \
                mock.patch(_MODULE + '.os.write', return_value=0):
            self.expect_code('IO_BEFORE_VISIBILITY', acquire, self.root, _WORLD, initialize=True)
        self.assert_descriptors_closed(descriptors)
        self.assertEqual((self.root / 'identity.json').read_bytes(), b'')
        before = self.files()
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD, initialize=True)
        self.assertEqual(self.files(), before)

    def test_wrong_public_argument_types(self):
        self.expect_code('SCHEMA', acquire, str(self.root), _WORLD)
        self.expect_code('SCHEMA', acquire, self.root, _WORLD, initialize=1)
        self.expect_code('ID', acquire, self.root, 'BAD ID')
        self.expect_code('ID', acquire, self.root, True)


class OwnershipV02Tests(unittest.TestCase):
    setUp = OwnershipTests.setUp
    expect_code = OwnershipTests.expect_code
    files = OwnershipTests.files

    def context(self, **changes):
        values = dict(world_id=_WORLD, authority_root=str(self.root.resolve()),
                      trust_anchor='a' * 64, expected_build='b' * 64,
                      expected_options='c' * 64)
        values.update(changes)
        return DeploymentContext(**values)

    def acquire(self, *, root=None, context=None, initialize=False):
        return acquire(root or self.root, _WORLD, initialize=initialize,
                       domain_version='0.2', profile='local-posix-blob-sync-v0.2',
                       context=context if context is not None else self.context())

    def initialized(self):
        lease = self.acquire(initialize=True)
        self.addCleanup(lease.close)
        return lease

    def test_exact_registration_and_frozen_public_lease(self):
        context = self.context()
        with self.acquire(context=context, initialize=True) as lease:
            info = self.root.stat()
            expected = dict(
                domain='edgeworld.universe.authority', version='0.2',
                world_id=_WORLD, profile='local-posix-blob-sync-v0.2',
                root_canonical=str(self.root), root_device=str(info.st_dev),
                root_inode=str(info.st_ino), trust_algorithm=context.trust_algorithm,
                trust_anchor=context.trust_anchor, expected_build=context.expected_build,
                expected_options=context.expected_options, artifact_class=context.artifact_class,
                archive_profile=context.archive_profile)
            self.assertEqual((self.root / 'identity.json').read_bytes(),
                             json.dumps(expected, sort_keys=True, ensure_ascii=True,
                                        separators=(',', ':')).encode('ascii'))
            self.assertEqual(lease.domain_version, '0.2')
            self.assertIs(lease.context, context)
            with self.assertRaises(AttributeError):
                lease.domain_version = '0.1'
            with self.assertRaises(AttributeError):
                lease.context = None
            self.assertEqual(set(p.name for p in self.root.iterdir()),
                             {'.authority.lock', 'identity.json'})
        before = self.files()
        with self.acquire(context=context) as reopened:
            reopened.check()
        self.assertEqual(self.files(), before)

    def test_missing_read_does_not_create_and_context_required(self):
        before = self.files()
        self.expect_code('UNINITIALIZED', self.acquire)
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD,
                         initialize=True, domain_version='0.2',
                         profile='local-posix-blob-sync-v0.2')
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD,
                         initialize=True, domain_version='0.2',
                         profile='local-posix-blob-sync-v0.2', context={})
        self.assertEqual(self.files(), before)

    def test_version_profile_whitelist_and_old_context_rejection(self):
        before = self.files()
        for version, profile in [('0.2', 'local-posix-sync-v0.1'),
                                 ('0.1', 'local-posix-blob-sync-v0.2'),
                                 ('0.3', 'local-posix-blob-sync-v0.2'),
                                 (True, 'local-posix-sync-v0.1'), ('0.1', None)]:
            self.expect_code('PROFILE', acquire, self.root, _WORLD,
                             initialize=True, domain_version=version, profile=profile)
        self.expect_code('PROFILE', acquire, self.root, _WORLD,
                         initialize=True, context=self.context())
        self.assertEqual(self.files(), before)

    def test_wrong_world_or_root_rejected_before_creation(self):
        before = self.files()
        self.expect_code('ROOT_MISMATCH', self.acquire, initialize=True,
                         context=self.context(world_id='another-world'))
        self.expect_code('ROOT_MISMATCH', self.acquire, initialize=True,
                         context=self.context(authority_root=str(self.base / 'other')))
        self.assertEqual(self.files(), before)

    def test_alias_rejected_both_busy_and_released(self):
        lease = self.initialized()
        alias = self.base / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        before = self.files()
        self.expect_code('ROOT_MISMATCH', self.acquire, root=alias)
        self.expect_code('ROOT_MISMATCH', self.acquire, root=alias,
                         context=self.context(authority_root=str(alias)))
        lease.close()
        self.expect_code('ROOT_MISMATCH', self.acquire, root=alias)
        self.assertEqual(self.files(), before)
        with self.acquire() as reopened:
            reopened.check()

    def test_independent_v02_process_lock_and_read_nonmutation(self):
        lease = self.initialized()
        script = """
import json, sys
from pathlib import Path
from engine.universe_authority.codec import ContractError, DeploymentContext
from engine.universe_authority.ownership import acquire
root = Path(sys.argv[1])
context = DeploymentContext(world_id='ownership-fixture', authority_root=str(root),
    trust_anchor='a'*64, expected_build='b'*64, expected_options='c'*64)
try:
    with acquire(root, 'ownership-fixture', domain_version='0.2',
                 profile='local-posix-blob-sync-v0.2', context=context) as lease:
        lease.check()
    print('ACQUIRED')
except ContractError as exc:
    print(exc.code)
"""
        before = self.files()
        for expected in ('LOCKED', 'ACQUIRED'):
            result = subprocess.run([sys.executable, '-c', script, str(self.root)],
                                    cwd=_REPOSITORY, capture_output=True, text=True,
                                    check=True, timeout=10)
            self.assertEqual(result.stdout.strip(), expected)
            self.assertEqual(result.stderr, '')
            lease.close()
        self.assertEqual(self.files(), before)

    @unittest.skipUnless(hasattr(os, 'fork'), 'requires POSIX fork')
    def test_v02_fork_child_cannot_authorize_or_release_parent(self):
        lease = self.initialized()
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                try:
                    lease.check()
                    code = 'UNEXPECTED_SUCCESS'
                except ContractError as exc:
                    code = exc.code
                lease.close()
                os.write(write_fd, code.encode('ascii'))
                os.close(write_fd)
                os._exit(0)
            except BaseException:
                os._exit(2)
        os.close(write_fd)
        try:
            code = os.read(read_fd, 128).decode('ascii')
        finally:
            os.close(read_fd)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        self.assertEqual(code, 'LOCKED')
        lease.check()
        self.expect_code('LOCKED', self.acquire)

    def test_copied_registration_cannot_reregister(self):
        lease = self.initialized()
        lease.close()
        other = self.base / 'copy'
        other.mkdir()
        for name in ('.authority.lock', 'identity.json'):
            (other / name).write_bytes((self.root / name).read_bytes())
        before = self.files()
        for initialize in (False, True):
            self.expect_code('ROOT_MISMATCH', self.acquire, root=other,
                             context=self.context(authority_root=str(other)),
                             initialize=initialize)
        self.assertEqual(self.files(), before)

    def test_pin_changes_do_not_repair_registration(self):
        lease = self.initialized()
        lease.close()
        before = self.files()
        original = self.context()
        for field, value in [('trust_anchor', 'd' * 64),
                             ('expected_build', 'd' * 64),
                             ('expected_options', 'd' * 64),
                             ('artifact_class', 'synthetic-contract-only')]:
            for initialize in (False, True):
                self.expect_code('ROOT_MISMATCH', self.acquire,
                                 context=replace(original, **{field: value}),
                                 initialize=initialize)
        self.assertEqual(self.files(), before)

    def test_registration_extra_key_and_wrong_algorithm_rejected(self):
        lease = self.initialized()
        lease.close()
        path = self.root / 'identity.json'
        original = json.loads(path.read_bytes())
        for changed in [dict(original, key_dir='/not-allowed'),
                        dict(original, trust_algorithm='other')]:
            path.write_text(json.dumps(changed, sort_keys=True, separators=(',', ':')))
            before = self.files()
            self.expect_code('ROOT_MISMATCH', self.acquire)
            self.assertEqual(self.files(), before)

    def test_versions_do_not_upgrade_or_downgrade_registered_root(self):
        old = acquire(self.root, _WORLD, initialize=True)
        old.close()
        before = self.files()
        self.expect_code('ROOT_MISMATCH', self.acquire, initialize=True)
        self.expect_code('ROOT_MISMATCH', self.acquire)
        self.assertEqual(self.files(), before)
        # An independent v0.2 root cannot be opened via the old public call.
        self.root = self.base / 'v2'
        self.initialized().close()
        before = self.files()
        self.expect_code('ROOT_MISMATCH', acquire, self.root, _WORLD)
        self.assertEqual(self.files(), before)

    def test_lock_lifetime_replacement_and_read_nonmutation(self):
        lease = self.initialized()
        before = self.files()
        self.expect_code('LOCKED', self.acquire)
        lease.check()
        self.assertEqual(self.files(), before)
        (self.root / '.authority.lock').rename(self.root / 'old-lock')
        (self.root / '.authority.lock').write_bytes(b'')
        self.expect_code('ROOT_MISMATCH', lease.check)


if __name__ == '__main__':
    unittest.main()
