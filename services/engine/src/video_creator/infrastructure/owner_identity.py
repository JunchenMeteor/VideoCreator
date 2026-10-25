"""Local OS identity and directory ownership; no caller-supplied identity."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from video_creator.domain.errors import EngineError


@dataclass(frozen=True)
class LocalOwnerIdentity:
    os_subject: str
    administrator_id: str
    directory_device: int
    directory_inode: int


def _windows_owner(path):
    import ctypes
    from ctypes import wintypes as w

    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    pointer = ctypes.c_void_p
    advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    advapi.OpenProcessToken.restype = w.BOOL
    advapi.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, pointer, w.DWORD, ctypes.POINTER(w.DWORD)]
    advapi.GetTokenInformation.restype = w.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(w.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype = w.BOOL
    advapi.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, ctypes.c_int, w.DWORD,
        ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer)]
    advapi.GetNamedSecurityInfoW.restype = w.DWORD
    advapi.GetAclInformation.argtypes = [pointer, pointer, w.DWORD, ctypes.c_int]
    advapi.GetAclInformation.restype = w.BOOL
    advapi.GetAce.argtypes = [pointer, w.DWORD, ctypes.POINTER(pointer)]
    advapi.GetAce.restype = w.BOOL
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer

    def sid_string(sid):
        converted = w.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(converted)):
            raise EngineError('owner_os_identity_unavailable', 'OS SID could not be resolved', 503)
        try:
            return converted.value
        finally:
            kernel.LocalFree(ctypes.cast(converted, pointer))

    token = w.HANDLE()
    descriptor = pointer()
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            raise EngineError('owner_os_identity_unavailable', 'Current OS authentication token is unavailable', 503)
        required = w.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        if not 1 <= required.value <= 65536:
            raise EngineError('owner_os_identity_unavailable', 'Current OS token size is invalid', 503)
        buffer = ctypes.create_string_buffer(required.value)
        if not advapi.GetTokenInformation(token, 1, buffer, required, ctypes.byref(required)):
            raise EngineError('owner_os_identity_unavailable', 'Current OS token identity is unavailable', 503)
        current_sid = sid_string(ctypes.cast(buffer, ctypes.POINTER(pointer))[0])
        owner, dacl = pointer(), pointer()
        if advapi.GetNamedSecurityInfoW(str(path), 1, 5, ctypes.byref(owner), None,
                ctypes.byref(dacl), None, ctypes.byref(descriptor)) != 0:
            raise EngineError('owner_directory_identity_unavailable', 'Actual directory security is unavailable', 503)
        if sid_string(owner) != current_sid or not dacl.value:
            raise EngineError('owner_directory_denied', 'The actual OS caller must own protected installation storage', 403)

        class AclSize(ctypes.Structure):
            _fields_ = [('count', w.DWORD), ('used', w.DWORD), ('free', w.DWORD)]

        size = AclSize()
        if not advapi.GetAclInformation(dacl, ctypes.byref(size), ctypes.sizeof(size), 2):
            raise EngineError('owner_directory_identity_unavailable', 'Directory access control is unavailable', 503)
        trusted = {current_sid, 'S-1-5-18', 'S-1-5-32-544'}
        unsafe = 0x10000000 | 0x40000000 | 0x00080000 | 0x00040000 | 0x00010000 | 0x100 | 0x40 | 0x10 | 0x4 | 0x2
        for index in range(size.count):
            ace = pointer()
            if not advapi.GetAce(dacl, index, ctypes.byref(ace)):
                raise EngineError('owner_directory_identity_unavailable', 'Directory access entry is unavailable', 503)
            header = ctypes.cast(ace, ctypes.POINTER(ctypes.c_ubyte))
            if header[1] & 0x08:  # INHERIT_ONLY does not apply to this object.
                continue
            if header[0] in {0, 5, 9, 11}:  # allowed, object and callback variants
                mask = ctypes.cast(ace, ctypes.POINTER(w.DWORD))[1]
                if mask & unsafe and (header[0] != 0 or sid_string(pointer(ace.value + 8)) not in trusted):
                    raise EngineError('owner_directory_denied', 'Other principals can modify installation control storage', 403)
        return current_sid
    finally:
        if descriptor.value:
            kernel.LocalFree(descriptor)
        if token.value:
            kernel.CloseHandle(token)


def inspect_owner_directory(data_dir: Path) -> LocalOwnerIdentity:
    path = Path(data_dir)
    if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
        raise EngineError('owner_directory_denied', 'Owner storage requires an absolute local directory', 403)
    if any(item.is_symlink() or item.is_junction() for item in (path, *path.parents)):
        raise EngineError('owner_directory_denied', 'Owner storage cannot cross filesystem links', 403)
    information = path.stat()
    if not stat.S_ISDIR(information.st_mode):
        raise EngineError('owner_directory_denied', 'Owner storage must already be an actual directory', 403)
    if os.name == 'nt':
        subject = _windows_owner(path)
        administrator = subject
    elif os.name == 'posix':
        uid = os.getuid()
        if uid != os.geteuid() or information.st_uid != uid or information.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise EngineError('owner_directory_denied', 'Actual UID must exclusively control its installation directory', 403)
        subject = administrator = 'uid-' + str(uid)
    else:
        raise EngineError('owner_os_identity_unavailable', 'This OS has no supported ownership implementation', 503)
    after = path.stat()
    if (information.st_dev, information.st_ino) != (after.st_dev, after.st_ino):
        raise EngineError('owner_directory_changed', 'Installation directory identity changed', 409)
    return LocalOwnerIdentity(subject, administrator, information.st_dev, information.st_ino)
