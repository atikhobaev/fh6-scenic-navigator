import struct
from .errors import CorruptWvanError

def align_up(value, alignment=16):
    if alignment <= 0:
        raise ValueError('alignment must be > 0')
    return ((int(value) + alignment - 1) // alignment) * alignment

class Reader:
    def __init__(self, data: bytes, source='<bytes>'):
        self.data = memoryview(bytes(data)); self.source = str(source)
    @property
    def size(self): return len(self.data)
    def read(self, off, size):
        if off < 0 or size < 0 or off + size > self.size:
            raise CorruptWvanError(f'{self.source}: out-of-range read off={off} size={size} file={self.size}')
        return self.data[off:off+size].tobytes()
    def unpack(self, fmt, off):
        raw = self.read(off, struct.calcsize(fmt))
        return struct.unpack(fmt, raw)
    def u32(self, off): return self.unpack('<I', off)[0]
    def u64(self, off): return self.unpack('<Q', off)[0]
