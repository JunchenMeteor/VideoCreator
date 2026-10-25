"""Private Windows peer/overlapped pipe, never a locator-derived authority."""

import ctypes
import hashlib
import os
import time
from ctypes import wintypes as w
from dataclasses import dataclass
from pathlib import Path

from video_creator.domain.errors import EngineError
from video_creator.infrastructure.owner_identity import (
    _windows_owner,
    inspect_owner_directory,
)


def _error(code, message, status=503):
    return EngineError(code, message, status)


def _local_image_path(value):
    """Only local drive / extended-drive representation, never a UNC alias.

    Normalized text is not authentication: the caller must additionally match
    the actual retained file identity. The shared Owner UNC/link rule is intact.
    """
    raw = os.fspath(value)
    if type(raw) is not str:
        raise _error('installation_peer_denied', 'Native image requires a local drive path', 403)
    raw = raw.replace('/', '\\')
    raw = raw.removeprefix('\\\\?\\')
    if (len(raw) < 4 or raw[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            or raw[1:3] != ':\\' or ':' in raw[2:]
            or any(part in ('', '.', '..') or part.endswith((' ', '.')) for part in raw[3:].split('\\'))
            or any(ord(char) < 32 for char in raw)):
        raise _error('installation_peer_denied', 'Native image requires an exact absolute local drive path', 403)
    path = Path(raw)
    if path.is_symlink() or path.is_junction():
        raise _error('installation_peer_denied', 'Native image cannot cross a file link', 403)
    return path


class _Win32:
    def __init__(self):
        if os.name != 'nt':
            raise _error('installation_channel_unsupported', 'Held installation channel requires Windows')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.advapi = ctypes.WinDLL('advapi32', use_last_error=True)
        pointer = ctypes.c_void_p
        self._declare(self.kernel, 'CreateFileW', w.HANDLE,
                      [w.LPCWSTR, w.DWORD, w.DWORD, pointer, w.DWORD, w.DWORD, w.HANDLE])
        self._declare(self.kernel, 'CloseHandle', w.BOOL, [w.HANDLE])
        self._declare(self.kernel, 'OpenProcess', w.HANDLE, [w.DWORD, w.BOOL, w.DWORD])
        self._declare(self.kernel, 'GetCurrentProcess', w.HANDLE, [])
        self._declare(self.kernel, 'GetProcessTimes', w.BOOL,
                      [w.HANDLE, pointer, pointer, pointer, pointer])
        self._declare(self.kernel, 'QueryFullProcessImageNameW', w.BOOL,
                      [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)])
        self._declare(self.kernel, 'GetNamedPipeServerProcessId', w.BOOL,
                      [w.HANDLE, ctypes.POINTER(w.ULONG)])
        self._declare(self.kernel, 'CreateEventW', w.HANDLE, [pointer, w.BOOL, w.BOOL, w.LPCWSTR])
        self._declare(self.kernel, 'WaitForSingleObject', w.DWORD, [w.HANDLE, w.DWORD])
        self._declare(self.kernel, 'ReadFile', w.BOOL, [w.HANDLE, pointer, w.DWORD, pointer, pointer])
        self._declare(self.kernel, 'WriteFile', w.BOOL, [w.HANDLE, pointer, w.DWORD, pointer, pointer])
        self._declare(self.kernel, 'CancelIoEx', w.BOOL, [w.HANDLE, pointer])
        self._declare(self.kernel, 'GetOverlappedResult', w.BOOL,
                      [w.HANDLE, pointer, ctypes.POINTER(w.DWORD), w.BOOL])
        self._declare(self.kernel, 'PeekNamedPipe', w.BOOL,
                      [w.HANDLE, pointer, w.DWORD, pointer, pointer, pointer])
        self._declare(self.kernel, 'SetFilePointerEx', w.BOOL,
                      [w.HANDLE, ctypes.c_longlong, pointer, w.DWORD])
        self._declare(self.kernel, 'GetFileInformationByHandle', w.BOOL, [w.HANDLE, pointer])
        self._declare(self.advapi, 'OpenProcessToken', w.BOOL,
                      [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)])
        self._declare(self.advapi, 'GetTokenInformation', w.BOOL,
                      [w.HANDLE, ctypes.c_int, pointer, w.DWORD, ctypes.POINTER(w.DWORD)])
        self._declare(self.advapi, 'ConvertSidToStringSidW', w.BOOL,
                      [pointer, ctypes.POINTER(w.LPWSTR)])
        self._declare(self.kernel, 'LocalFree', pointer, [pointer])

    @staticmethod
    def _declare(library, name, result, args):
        function = getattr(library, name)
        function.restype, function.argtypes = result, args

    def close(self, handle):
        if handle not in (None, 0, ctypes.c_void_p(-1).value) and not self.kernel.CloseHandle(handle):
            raise _error('installation_channel_close_failed', 'Original Windows handle did not close')

    def sid(self, process):
        token, converted = w.HANDLE(), w.LPWSTR()
        try:
            if not self.advapi.OpenProcessToken(process, 8, ctypes.byref(token)):
                raise _error('installation_peer_denied', 'Actual peer token is unavailable', 403)
            size = w.DWORD()
            self.advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
            if not 1 <= size.value <= 65536:
                raise _error('installation_peer_denied', 'Actual peer token size is invalid', 403)
            buffer = ctypes.create_string_buffer(size.value)
            if not self.advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
                raise _error('installation_peer_denied', 'Actual peer identity is unavailable', 403)
            sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
            if not self.advapi.ConvertSidToStringSidW(sid, ctypes.byref(converted)):
                raise _error('installation_peer_denied', 'Actual peer SID is unavailable', 403)
            return converted.value
        finally:
            if converted:
                self.kernel.LocalFree(ctypes.cast(converted, ctypes.c_void_p))
            self.close(token.value)

    def process_identity(self, process):
        times = [w.FILETIME() for _ in range(4)]
        if not self.kernel.GetProcessTimes(process, *(ctypes.byref(item) for item in times)):
            raise _error('installation_peer_denied', 'Actual peer creation identity is unavailable', 403)
        image, size = ctypes.create_unicode_buffer(32768), w.DWORD(32768)
        if not self.kernel.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(size)):
            raise _error('installation_peer_denied', 'Actual peer executable is unavailable', 403)
        creation = times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
        return creation, self.sid(process), image.value


    def file_identity(self, handle):
        class FileInformation(ctypes.Structure):
            _fields_ = [('attributes', w.DWORD), ('created', w.FILETIME),
                        ('accessed', w.FILETIME), ('written', w.FILETIME),
                        ('volume', w.DWORD), ('size_high', w.DWORD), ('size_low', w.DWORD),
                        ('links', w.DWORD), ('index_high', w.DWORD), ('index_low', w.DWORD)]

        information = FileInformation()
        if (not self.kernel.GetFileInformationByHandle(handle, ctypes.byref(information))
                or information.attributes & (0x10 | 0x400)):
            raise _error('installation_peer_denied', 'Original native file identity is unavailable or linked', 403)
        return (information.volume, information.index_low | (information.index_high << 32),
                information.size_low | (information.size_high << 32))


@dataclass(eq=False, repr=False)
class OwnerProtectedNativeBuild:
    """Held actual file plus independent trusted installer identity.

    Only open_owner_protected_native_build creates this at fixed native startup.
    expected_sha256 must originate from the protected installed build record,
    never locator.image_sha256. This is image identity, not qualification.
    """
    path: Path
    expected_sha256: str
    owner: object
    file_identity: tuple[int, int, int]
    _api: _Win32
    _handle: int
    _native_file_identity: tuple[int, int, int]
    _closed: bool = False

    def assert_current(self):
        if self._closed:
            raise _error('installation_connection_invalid', 'Trusted native image has been released')
        information = self.path.stat()
        if (inspect_owner_directory(self.path.parent) != self.owner
                or (information.st_dev, information.st_ino, information.st_size) != self.file_identity
                or _windows_owner(self.path) != self.owner.os_subject
                or self._api.file_identity(self._handle) != self._native_file_identity):
            raise _error('installation_peer_denied', 'Protected native image identity changed', 403)
        if not self._api.kernel.SetFilePointerEx(self._handle, 0, None, 0):
            raise _error('installation_peer_denied', 'Original native image cannot be read', 403)
        digest, count = hashlib.sha256(), 0
        while True:
            buffer, read = ctypes.create_string_buffer(65536), w.DWORD()
            if not self._api.kernel.ReadFile(self._handle, buffer, len(buffer), ctypes.byref(read), None):
                raise _error('installation_peer_denied', 'Original native image read failed', 403)
            if not read.value:
                break
            count += read.value
            if count > self.file_identity[2]:
                raise _error('installation_peer_denied', 'Original native image size changed', 403)
            digest.update(buffer.raw[:read.value])
        after = self.path.stat()
        if (count != self.file_identity[2] or digest.hexdigest() != self.expected_sha256
                or (after.st_dev, after.st_ino, after.st_size) != self.file_identity):
            raise _error('installation_peer_denied', 'Actual native image differs from the trusted build', 403)

    def assert_image_path(self, image):
        path = _local_image_path(image)
        if os.path.normcase(str(path)) != os.path.normcase(str(self.path)):
            raise _error('installation_peer_denied', 'Native image path is not the independently held build path', 403)
        # Only the exact validated drive path gets an extended representation
        # for the Win32 open. A different alias/junction is never authorized.
        handle = self._api.kernel.CreateFileW('\\\\?\\' + str(path), 0x80000000, 1, None, 3, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise _error('installation_peer_denied', 'Reported native image cannot be checked', 403)
        try:
            if self._api.file_identity(handle) != self._native_file_identity:
                raise _error('installation_peer_denied', 'Reported native image differs from the original held file', 403)
        finally:
            self._api.close(handle)

    def close(self):
        if not self._closed:
            self._api.close(self._handle)
            self._closed = True


def open_owner_protected_native_build(*, image_path: Path, expected_sha256: str):
    api = _Win32()
    path = _local_image_path(image_path)
    if (not path.is_absolute() or path.is_symlink() or path.is_junction()
            or type(expected_sha256) is not str or len(expected_sha256) != 64
            or any(char not in '0123456789abcdef' for char in expected_sha256)):
        raise _error('installation_peer_denied', 'Independent trusted native build identity is required', 403)
    owner = inspect_owner_directory(path.parent)
    if _windows_owner(path) != owner.os_subject:
        raise _error('installation_peer_denied', 'Native image is not protected by its actual OS Owner', 403)
    information = path.stat()
    if not path.is_file() or not 0 < information.st_size <= 256 * 1024 * 1024:
        raise _error('installation_peer_denied', 'Trusted native build must be a finite regular file', 403)
    # Share read only: retain the original image; deny replacement and writes.
    handle = api.kernel.CreateFileW('\\\\?\\' + str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise _error('installation_peer_denied', 'Trusted native build cannot be held', 403)
    try:
        build = OwnerProtectedNativeBuild(path, expected_sha256, owner,
            (information.st_dev, information.st_ino, information.st_size), api, handle, api.file_identity(handle))
        build.assert_current()
        return build
    except BaseException:
        api.close(handle)
        raise


class _RetainedIo:
    """Original kernel arguments stay reachable across any transfer unwind."""

    def __init__(self, owner, original_pipe, event, overlap, buffer, read, function, arguments):
        self.owner, self.original_pipe, self.event = owner, original_pipe, event
        self.overlap, self.buffer, self.read = overlap, buffer, read
        self.function, self.arguments = function, arguments
        self.may_reference = self.completed = self.cancelled = False
        self.call_result = self.call_error = None
        self.original_error = self.cleanup_error = None
        self.event_close_contacted = self.event_closed = False
        _retained_io[id(self)] = self


# Not a weak collection or per-call local: pending operations retain their
# original owner/API/HANDLEs and Python memory even if all caller frames unwind.
_retained_io: dict[int, _RetainedIo] = {}


class _RetainedHandleClose:
    """Keep original close contact facts even if its caller stack unwinds."""

    def __init__(self, owner, name, original_handle):
        self.owner, self.name, self.original_handle = owner, name, original_handle
        self.function = owner.api.close
        self.contacted = self.confirmed = False
        self.error = None
        _retained_handle_closes[id(self)] = self


_retained_handle_closes: dict[int, _RetainedHandleClose] = {}


class WindowsAuthorityPipe:
    """One child-opened connection, held handles through actual I/O completion."""
    def __init__(self, *, pipe_name, server, trusted_build, startup_deadline):
        self.api = _Win32()
        self.build, self.server_description = trusted_build, server
        self.pipe = self.process = None
        self.invalid = False
        try:
            while True:
                # SECURITY_IDENTIFICATION: server may identify, not impersonate.
                self.pipe = self.api.kernel.CreateFileW(pipe_name, 0xC0000000, 0, None, 3,
                                                        0x40000000 | 0x100000 | 0x10000, None)
                if self.pipe != ctypes.c_void_p(-1).value:
                    break
                self.pipe = None
                if ctypes.get_last_error() not in (2, 231) or time.monotonic() >= startup_deadline:
                    raise _error('installation_channel_unavailable', 'Original local authority pipe could not be opened')
                time.sleep(min(0.025, max(0, startup_deadline - time.monotonic())))
            self.process = self.api.kernel.OpenProcess(0x1000 | 0x100000, False, server['pid'])
            if not self.process:
                raise _error('installation_peer_denied', 'Original server process cannot be held', 403)
            self.assert_peer()
            if time.monotonic() >= startup_deadline:
                raise _error('installation_channel_timeout', 'Authority startup deadline elapsed')
        except BaseException:
            self.close()
            raise

    def assert_local_current(self):
        """Bounded local handle polls only; no RPC or hashing in a DB writer."""
        if self.invalid or self.build._closed or not self.process or not self.pipe:
            raise _error('installation_connection_invalid', 'Original authority session is invalid')
        if (self.api.kernel.WaitForSingleObject(self.process, 0) != 258
                or not self.api.kernel.PeekNamedPipe(self.pipe, None, 0, None, None, None)):
            self.invalid = True
            raise _error('installation_connection_invalid', 'Original authority peer or pipe has ended')

    def assert_peer(self):
        self.assert_local_current()
        peer = w.ULONG()
        expected = self.server_description
        if (not self.api.kernel.GetNamedPipeServerProcessId(self.pipe, ctypes.byref(peer))
                or peer.value != expected['pid'] or os.getppid() != peer.value):
            self.invalid = True
            raise _error('installation_peer_denied', 'Pipe server is not this exact actual launch parent', 403)
        creation, sid, image = self.api.process_identity(self.process)
        self.build.assert_current()
        self.build.assert_image_path(image)
        self.build.assert_image_path(expected['image'])
        if (creation != expected['creation_filetime'] or sid != expected['sid']
                or sid != self.api.sid(self.api.kernel.GetCurrentProcess())
                or expected['image_sha256'] != self.build.expected_sha256):
            self.invalid = True
            raise _error('installation_peer_denied', 'Actual server differs from its independent trusted build and OS identity', 403)

    def _transfer(self, data, length, *, writing, deadline):
        class Overlapped(ctypes.Structure):
            _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                        ('Offset', w.DWORD), ('OffsetHigh', w.DWORD), ('hEvent', w.HANDLE)]

        if self.invalid or any(operation.owner is self for operation in tuple(_retained_io.values())):
            raise _error('installation_connection_invalid', 'Original pending I/O cannot submit another request')
        # Allocate Python memory before acquiring an additional OS event.
        overlap, buffer = Overlapped(), ctypes.create_string_buffer(data, length) if writing else ctypes.create_string_buffer(length)
        event = self.api.kernel.CreateEventW(None, True, False, None)
        if not event:
            self.invalid = True
            raise _error('installation_channel_unavailable', 'I/O completion event is unavailable')
        overlap.hEvent = event
        original_pipe, read = self.pipe, w.DWORD()
        function = self.api.kernel.WriteFile if writing else self.api.kernel.ReadFile
        arguments = (original_pipe, buffer, length, None, ctypes.byref(overlap))
        operation = _RetainedIo(self, original_pipe, event, overlap, buffer, read, function, arguments)
        try:
            # Before any possible OS contact, conservatively retain ownership.
            # An exception during/after the call cannot prove non-submission.
            operation.may_reference = True
            operation.call_result = operation.function(*operation.arguments)
            operation.call_error = ctypes.get_last_error() if not operation.call_result else None
            if operation.call_result == 0 and operation.call_error != 997:
                operation.completed = True  # Same original call observed a refusal.
                raise _error('installation_channel_disconnected', 'Original pipe I/O was refused')
            remaining = deadline - time.monotonic()
            if remaining <= 0 or self.api.kernel.WaitForSingleObject(event, max(1, min(0xFFFFFFFE, int(remaining * 1000)))) != 0:
                self.invalid = True
                raise _error('installation_channel_timeout', 'Original authority frame deadline elapsed')
            success = self.api.kernel.GetOverlappedResult(original_pipe, ctypes.byref(overlap), ctypes.byref(read), False)
            operation.completed = self._terminal_io_result(success, overlap)
            if not success or read.value == 0 or read.value > length:
                raise _error('installation_channel_disconnected', 'Original pipe I/O completed without a valid frame portion')
            return read.value if writing else buffer.raw[:read.value]
        except BaseException as error:
            self.invalid = True
            operation.original_error = error
            raise
        finally:
            self._finish_retained_io(operation)

    def _finish_retained_io(self, operation):
        if operation.owner is not self or _retained_io.get(id(operation)) is not operation:
            raise _error('installation_io_owner_invalid', 'Only this exact original retained I/O can be observed')
        # Same original result/error can discharge an interrupted refusal path.
        # Absence of contact is known only while its pre-contact marker is false.
        if (not operation.may_reference or operation.call_result == 0
                and operation.call_error is not None and operation.call_error != 997):
            operation.completed = True
        if not operation.completed:
            self.invalid = True
            while not operation.completed:
                try:
                    if not operation.cancelled:
                        self.api.kernel.CancelIoEx(operation.original_pipe, ctypes.byref(operation.overlap))
                        operation.cancelled = True
                    if self.api.kernel.WaitForSingleObject(operation.event, 1000) == 0:
                        success = self.api.kernel.GetOverlappedResult(operation.original_pipe,
                            ctypes.byref(operation.overlap), ctypes.byref(operation.read), False)
                        operation.completed = self._terminal_io_result(success, operation.overlap)
                except BaseException as error:
                    self.invalid = True
                    if operation.cleanup_error is None:
                        operation.cleanup_error = error
                    # Even a new exception at this loop's unprotected boundary
                    # leaves the complete original operation in _retained_io.
                    if operation.completed:
                        if operation.original_error is not None:
                            raise operation.original_error from error
                        raise
        try:
            if not operation.event_close_contacted:
                operation.event_close_contacted = True
                self.api.close(operation.event)
                operation.event_closed = True
        except BaseException as error:
            if operation.cleanup_error is None:
                operation.cleanup_error = error
            # Original I/O is terminal, but event close was not confirmed.
            # Preserve both the strong holder and primary exception; no retry.
            if operation.original_error is not None:
                raise operation.original_error from error
            raise
        if not operation.event_closed:
            # Unknown CloseHandle contact must not repeat on a recycled HANDLE.
            # Retain the terminal operation/owner; close() cannot bypass this.
            self.invalid = True
            if operation.original_error is not None:
                raise operation.original_error
            if operation.cleanup_error is not None:
                raise operation.cleanup_error
            raise _error('installation_io_cleanup_pending', 'Original completion event close is not confirmed')
        del _retained_io[id(operation)]
        if operation.original_error is not None:
            if operation.cleanup_error is not None:
                operation.original_error.add_note('Original I/O cleanup also raised ' + type(operation.cleanup_error).__name__)
            raise operation.original_error
        if operation.cleanup_error is not None:
            raise operation.cleanup_error

    def observe_retained_io(self):
        """Resume only original cancellation/completion; never submit or reconnect."""
        self.invalid = True
        for operation in tuple(_retained_io.values()):
            if operation.owner is self:
                self._finish_retained_io(operation)

    @staticmethod
    def _terminal_io_result(success, overlap):
        # Called only after the original event is signaled. A completed kernel
        # status plus the actual original GetOverlappedResult is required;
        # invalid API handles/arguments or still-pending status do not discharge
        # buffer ownership. STATUS_PENDING is 0x103 in OVERLAPPED.Internal.
        if success:
            return True
        error = ctypes.get_last_error()
        return error not in (6, 87, 996) and overlap.Internal != 0x103

    def read_exact(self, count, *, deadline):
        result = bytearray()
        while len(result) < count:
            result.extend(self._transfer(None, min(65536, count - len(result)), writing=False, deadline=deadline))
        return bytes(result)

    def write_all(self, data, *, deadline):
        offset = 0
        while offset < len(data):
            piece = data[offset:offset + 65536]
            offset += self._transfer(piece, len(piece), writing=True, deadline=deadline)

    def _close_retained_handle(self, name):
        if name not in {'pipe', 'process'}:
            raise _error('installation_close_owner_invalid', 'Only original pipe/process handles can be closed')
        retained = next((item for item in tuple(_retained_handle_closes.values())
                         if item.owner is self and item.name == name), None)
        if retained is None:
            original = getattr(self, name)
            if original is None:
                return
            retained = _RetainedHandleClose(self, name, original)
        if not retained.contacted:
            # Strong owner/original HANDLE and conservative contact marker both
            # precede the actual call. No unknown call is repeated later.
            retained.contacted = True
            try:
                retained.function(retained.original_handle)
                retained.confirmed = True
            except BaseException as error:
                retained.error = error
                raise
        if not retained.confirmed:
            if retained.error is not None:
                raise retained.error
            raise _error('installation_channel_close_unknown', 'Original handle close was contacted but not confirmed')
        if getattr(self, name) not in (retained.original_handle, None):
            raise _error('installation_close_owner_invalid', 'Original owner handle changed during close')
        # Confirmation precedes clearing; if interrupted after this store, the
        # same retained confirmed record can finish without another OS call.
        setattr(self, name, None)
        del _retained_handle_closes[id(retained)]

    def close(self):
        self.invalid = True
        # An interrupted transfer can already have unwound the connection lock.
        # Resume original observation before closing either retained OS handle.
        self.observe_retained_io()
        primary = None
        try:
            self._close_retained_handle('pipe')
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                self._close_retained_handle('process')
            except BaseException as error:
                if primary is not None:
                    raise primary from error
                raise
