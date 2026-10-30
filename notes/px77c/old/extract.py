import struct, sys
img = sys.argv[1]
with open(img, 'rb') as f:
    f.seek(512); h = f.read(92); arr = struct.unpack_from('<Q', h, 72)[0]
    f.seek(arr * 512); e = f.read(128)
print(struct.unpack_from('<Q', e, 32)[0] * 512)
