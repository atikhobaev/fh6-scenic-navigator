class Fh6NavError(Exception):
    pass

class UnsupportedWvanError(Fh6NavError):
    pass

class CorruptWvanError(Fh6NavError):
    pass
