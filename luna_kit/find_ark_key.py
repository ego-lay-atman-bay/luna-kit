# Credit goes to someone who wishes to remain anonymous
"""
Standalone utility to recover the ARK AES key from a `libMyPonyWorld.so` file.

The game never stores the AES key directly. It derives it at runtime with a
tiny helper (`ARK_DeriveKey`) that XORs two 32-byte blobs sitting exactly
0x20 (32) bytes apart in the binary's .rodata:

    for i in range(32):
        key[i] = blob_A[i] ^ blob_B[i]     # blob_B == blob_A + 0x20

The two blobs are pointed to by a pair of 7-digit hex addresses (for example
0x127E3BC and 0x127E39C) that are always 32 numbers apart. This script locates
`ARK_DeriveKey` by its unique instruction pattern, decodes the two ADRP/ADD
pairs that point at those blobs, and XORs their 32 bytes to recover the key.

Usage:
    python find_ark_key.py path/to/libMyPonyWorld.so [another.so ...]
"""

import struct
import sys
from pathlib import Path

# The trailing 36 bytes of `ARK_DeriveKey` are identical across game versions.
# They start right after the two ADRP/ADD address-loading pairs (20 bytes):
#
#   B      loc
#   LDRB   W11, [X9, X8]
#   LDRB   W12, [X10, X8]
#   EOR    W11, W12, W11
#   STRB   W11, [X0, X8]
#   ADD    X8, X8, #1
#   CMP    X8, #0x20
#   B.NE   loc
#   RET
_SIGNATURE = bytes.fromhex(
    '06 00 00 14'
    '2b 69 68 38'
    '4c 69 68 38'
    '8b 01 0b 4a'
    '0b 68 28 38'
    '08 05 00 91'
    '1f 81 00 f1'
    '41 ff ff 54'
    'c0 03 5f d6'
)

_KEY_LENGTH = 32

# The "deadbeaf" marker (0x00FABCDE, 0xDEADBEAF, 0xBEAFDEAD, 0x12141412) that
# appears in .rodata immediately around the XXTEA key and right before the two
# AES key blobs. Used as a secondary landmark to locate the key:
#
#   [marker 16][XXTEA key 16][marker 16][blob B 32][blob A 32]
_MARKER = bytes.fromhex(
    'de bc fa 00'
    'af be ad de'
    'ad de af be'
    '12 14 14 12'
)

# The XXTEA key, stored in plaintext 0x10 bytes before the AES blobs.
_XXTEA_KEY = bytes.fromhex('34 2a 5b 3d 10 ff 3f 92 a4 46 e3 00 2b 90 74 0c')


def _sign_extend(value, bits):
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _decode_adrp(insn, pc):
    """Return the page address targeted by an AArch64 ADRP instruction."""
    immlo = (insn >> 29) & 0x3
    immhi = (insn >> 5) & 0x7FFFF
    imm = _sign_extend((immhi << 2) | immlo, 21)
    return (pc & ~0xFFF) + (imm << 12)


def _decode_add_imm(insn):
    """Return the 12-bit immediate of an AArch64 ADD Xd, Xn, #imm."""
    return (insn >> 10) & 0xFFF


def _load_segments(data):
    """Parse the 64-bit little-endian ELF PT_LOAD segments.

    Returns a list of (vaddr, offset, filesz) tuples.
    """
    if len(data) < 0x40 or data[:4] != b'\x7fELF':
        raise ValueError('not a valid ELF file')
    if data[4] != 2:
        raise ValueError('only 64-bit ELF files are supported')
    if data[5] != 1:
        raise ValueError('only little-endian ELF files are supported')

    e_phoff = struct.unpack_from('<Q', data, 0x20)[0]
    e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
    e_phnum = struct.unpack_from('<H', data, 0x38)[0]

    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from('<I', data, off)[0]
        if p_type != 1:  # PT_LOAD
            continue
        p_offset = struct.unpack_from('<Q', data, off + 0x8)[0]
        p_vaddr = struct.unpack_from('<Q', data, off + 0x10)[0]
        p_filesz = struct.unpack_from('<Q', data, off + 0x20)[0]
        segments.append((p_vaddr, p_offset, p_filesz))

    return segments


def _offset_to_va(offset, segments):
    for vaddr, foffset, filesz in segments:
        if foffset <= offset < foffset + filesz:
            return vaddr + (offset - foffset)
    raise ValueError('file offset 0x%x is not within a loadable segment' % offset)


def _va_to_offset(va, segments):
    for vaddr, foffset, filesz in segments:
        if vaddr <= va < vaddr + filesz:
            return foffset + (va - vaddr)
    raise ValueError('virtual address 0x%x is not within a loadable segment' % va)

def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _find_by_signature(data):
    """Primary method: locate ARK_DeriveKey by its instruction signature."""
    segments = _load_segments(data)

    start = 0
    while True:
        match = data.find(_SIGNATURE, start)
        if match == -1:
            break
        start = match + 1

        func_off = match - 20
        if func_off < 0:
            continue

        try:
            func_va = _offset_to_va(func_off, segments)
        except ValueError:
            continue

        adrp_b, adrp_a, mov, add_b, add_a = struct.unpack_from('<5I', data, func_off)

        # Validate the surrounding instructions so we only accept real matches.
        if (adrp_b & 0x9F000000) != 0x90000000:  # ADRP
            continue
        if (adrp_a & 0x9F000000) != 0x90000000:  # ADRP
            continue
        if (mov & 0xFFFFFFE0) != 0xAA1F03E0:     # MOV Xn, XZR
            continue
        if (add_b & 0xFFC00000) != 0x91000000:   # ADD Xn, Xn, #imm
            continue
        if (add_a & 0xFFC00000) != 0x91000000:   # ADD Xn, Xn, #imm
            continue

        addr_b = _decode_adrp(adrp_b, func_va) + _decode_add_imm(add_b)
        addr_a = _decode_adrp(adrp_a, func_va + 4) + _decode_add_imm(add_a)

        try:
            off_b = _va_to_offset(addr_b, segments)
            off_a = _va_to_offset(addr_a, segments)
        except ValueError:
            continue

        blob_b = data[off_b:off_b + _KEY_LENGTH]
        blob_a = data[off_a:off_a + _KEY_LENGTH]

        if len(blob_a) != _KEY_LENGTH or len(blob_b) != _KEY_LENGTH:
            continue

        return _xor(blob_a, blob_b)

    raise ValueError('could not locate ARK_DeriveKey in the binary')


def _find_by_marker(data):
    """Secondary method: locate the key via the deadbeaf marker + XXTEA key.

    In .rodata the layout is (relative to the plaintext XXTEA key):

        offset -0x10:  marker (16 bytes)   (optional padding before it)
        offset  0x00:  XXTEA key (16 bytes)
        offset +0x10:  marker (16 bytes)
        offset +0x20:  blob B (32 bytes)
        offset +0x40:  blob A (32 bytes)

    This works across versions even if ARK_DeriveKey's code changes.
    """
    start = 0
    while True:
        idx = data.find(_XXTEA_KEY, start)
        if idx == -1:
            break
        start = idx + 1

        # The marker must sit 16 bytes after the XXTEA key, right before blob B.
        if data[idx + 0x10 : idx + 0x20] != _MARKER:
            continue

        blob_b = data[idx + 0x20 : idx + 0x40]
        blob_a = data[idx + 0x40 : idx + 0x60]

        if len(blob_a) != _KEY_LENGTH or len(blob_b) != _KEY_LENGTH:
            continue

        return _xor(blob_a, blob_b)

    raise ValueError('could not locate the AES key via the deadbeaf marker')


def find_aes_key(binary):
    """Recover the ARK AES key from the raw bytes of libMyPonyWorld.so.

    Tries the primary method (ARK_DeriveKey signature) first, then falls back
    to the secondary method (deadbeaf marker + XXTEA key landmark).
    """
    data = bytes(binary)
    errors = []

    for finder in (_find_by_signature, _find_by_marker):
        try:
            return finder(data)
        except ValueError as e:
            errors.append(str(e))

    raise ValueError('; '.join(errors))


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 1

    label = len(argv) > 2
    failed = False
    for path in argv[1:]:
        try:
            key = find_aes_key(Path(path).read_bytes())
        except Exception as e:
            sys.stderr.write('%s: error: %s\n' % (path, e))
            failed = True
            continue
        if label:
            print('%s: %s' % (path, key.hex()))
        else:
            print(key.hex())

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
