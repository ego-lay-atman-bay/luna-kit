from ctypes import *
from ctypes import c_uint32
from typing import Annotated


def get_phdr_size(phdr_off: int):
    if (phdr_off & 3):
        phdr_off &= ~3
        phdr_off += 4

    return phdr_off


def decrypt(src: bytes | bytearray, n: int, key: Annotated[list[int], 4]):
    v = [
        c_uint32(int.from_bytes(src[x * len(src) // n : (x + 1)* len(src) // n], 'little'))
        for x in range(n)
    ]

    key: list[c_uint32] = [c_uint32(k) for k in key]

    DELTA = 0x9e3779b9

    y = c_uint32(0)
    z = c_uint32(0)
    p = 0
    e = c_uint32(0)

    def MX():
        return (((z.value >> 5 ^ y.value << 2) + (y.value >> 3 ^ z.value << 4)) ^ ((sum.value ^ y.value) + (key[(p & 3) ^ e.value].value ^ z.value)))

    rounds = 6 + (52 // n)
    sum = c_uint32(rounds * DELTA)
    y.value = v[0].value

    while (rounds):
        e.value = (sum.value >> 2) & 3
        for p in range(n - 1, 0, -1):
            z.value = v[p-1].value
            v[p].value -= MX()
            y.value = v[p].value
        p = 0
        z.value = v[n - 1].value
        v[0].value -= MX()
        y.value = v[0].value
        sum.value -= DELTA

        rounds -= 1

    return b''.join([bytes(x) for x in v])

def encrypt(src: bytes | bytearray, n: int, key: Annotated[list[int], 4]):
    v = [
        c_uint32(int.from_bytes(src[x * len(src) // n : (x + 1)* len(src) // n], 'little'))
        for x in range(n)
    ]

    key: list[c_uint32] = [c_uint32(k) for k in key]

    DELTA = 0x9e3779b9

    y = c_uint32(0)
    z = c_uint32(0)
    p = 0
    e = c_uint32(0)

    def MX():
        return (((z.value >> 5 ^ y.value << 2) + (y.value >> 3 ^ z.value << 4)) ^ ((sum.value ^ y.value) + (key[(p & 3) ^ e.value].value ^ z.value)))

    rounds = 6 + (52 // n)
    sum = c_uint32(0)
    z.value = v[n - 1].value

    while (rounds):
        sum.value += DELTA
        
        e.value = (sum.value >> 2) & 3
        for p in range(0, n - 1, 1):
            y.value = v[p + 1].value
            v[p].value += MX()
            z.value = v[p].value
        p = n - 1
        y.value = v[0].value
        v[n - 1].value += MX()
        z.value = v[n - 1].value

        rounds -= 1

    return b''.join([bytes(x) for x in v])