#!/usr/bin/env python3
"""A disk that keeps only what the guest flushed, and says when: an NBD server for powercut.py.

    disk = runpy.run_path('flushdisk.py')['FlushDisk'](IMAGE, SOCKET)
    disk.start(); ... (QEMU runs and exits) ...; disk.join(); disk.epochs, disk.stats

QEMU reaches IMAGE through this server (-blockdev driver=nbd over a unix
socket; the guest's virtio-blk device keeps a volatile write cache, so the
guest flushes). A write is held in memory, and read back from there, until
a FLUSH, which writes every held sector to IMAGE, syncs it, and records them
as one epoch; a FUA write goes to IMAGE at once, as an epoch of its own.
`epochs` is the list of (sector, 512 bytes) lists in the order they became
durable: the disk as it was before QEMU started, plus epochs[0..k], is what a
power cut right after the k-th durable point leaves, everything the guest
had not flushed by then lost. Writes still held when QEMU disconnects
without a FLUSH are counted (`held_at_close`) and dropped.

Protocol: the NBD protocol document (github.com/NetworkBlockDevice/nbd,
doc/proto.md): fixed newstyle negotiation, NBD_OPT_EXPORT_NAME, _INFO and
_GO; simple replies only (structured replies and metadata contexts are
answered NBD_REP_ERR_UNSUP); READ, WRITE (with FUA), FLUSH and DISC.
No other implementation's source was read.
"""
import os
import socket
import struct
import threading

NBDMAGIC = 0x4e42444d41474943
IHAVEOPT = 0x49484156454F5054
REPLY_MAGIC = 0x0003e889045565a9
REQUEST_MAGIC = 0x25609513
SIMPLE_REPLY = 0x67446698
FLAG_FIXED_NEWSTYLE, FLAG_NO_ZEROES = 1, 2
OPT_EXPORT_NAME, OPT_ABORT, OPT_INFO, OPT_GO = 1, 2, 6, 7
REP_ACK, REP_INFO, REP_ERR_UNSUP = 1, 3, 0x80000001
INFO_EXPORT = 0
T_HAS_FLAGS, T_SEND_FLUSH, T_SEND_FUA = 1, 4, 8
CMD_READ, CMD_WRITE, CMD_DISC, CMD_FLUSH = 0, 1, 2, 3
CMD_FLAG_FUA = 1
EINVAL = 22
SECTOR = 512


class FlushDisk(threading.Thread):
    def __init__(self, image, path):
        super().__init__(daemon=True)
        self.image, self.path = str(image), str(path)
        self.size = os.path.getsize(self.image)
        self.held = {}  # sector -> 512 bytes written but not yet flushed
        self.epochs = []
        self.lock = threading.RLock()
        self.error = None
        self.stats = {'writes': 0, 'flushes': 0, 'flushes_with_data': 0, 'fua_writes': 0,
                      'sectors_committed': 0, 'held_at_close': 0}
        if os.path.exists(self.path):
            os.unlink(self.path)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(self.path)
        self.listener.listen(1)

    def run(self):
        try:
            conn, _ = self.listener.accept()
            with conn, open(self.image, 'r+b', buffering=0) as f:
                try:
                    self.serve(conn, f.fileno())
                except EOFError:
                    pass  # QEMU closed the socket: what is still held was never flushed
        except Exception as e:  # reported by the caller; never a silent pass
            self.error = repr(e)
        finally:
            with self.lock:
                self.stats['held_at_close'] = len(self.held)
                self.held = {}
            self.listener.close()

    def recv(self, conn, n):
        b = bytearray()
        while len(b) < n:
            chunk = conn.recv(n - len(b))
            if not chunk:
                raise EOFError('peer closed')
            b.extend(chunk)
        return bytes(b)

    def option_reply(self, conn, option, kind, data=b''):
        conn.sendall(struct.pack('>QIII', REPLY_MAGIC, option, kind, len(data)) + data)

    def negotiate(self, conn):
        conn.sendall(struct.pack('>QQH', NBDMAGIC, IHAVEOPT, FLAG_FIXED_NEWSTYLE | FLAG_NO_ZEROES))
        client = struct.unpack('>I', self.recv(conn, 4))[0]
        flags = T_HAS_FLAGS | T_SEND_FLUSH | T_SEND_FUA
        while True:
            magic, option, length = struct.unpack('>QII', self.recv(conn, 16))
            if magic != IHAVEOPT:
                raise ValueError('option magic %x' % magic)
            self.recv(conn, length)
            if option == OPT_EXPORT_NAME:
                conn.sendall(struct.pack('>QH', self.size, flags) + (b'' if client & FLAG_NO_ZEROES else bytes(124)))
                return
            if option in (OPT_INFO, OPT_GO):
                self.option_reply(conn, option, REP_INFO, struct.pack('>HQH', INFO_EXPORT, self.size, flags))
                self.option_reply(conn, option, REP_ACK)
                if option == OPT_GO:
                    return
                continue
            if option == OPT_ABORT:
                self.option_reply(conn, option, REP_ACK)
                raise EOFError('client aborted')
            self.option_reply(conn, option, REP_ERR_UNSUP)

    def read(self, fd, offset, length):
        b = bytearray(os.pread(fd, length, offset))
        b.extend(bytes(length - len(b)))
        with self.lock:
            if self.held:
                first, last = offset // SECTOR, (offset + length - 1) // SECTOR
                for s in range(first, last + 1):
                    data = self.held.get(s)
                    if data is None:
                        continue
                    lo, hi = max(offset, s * SECTOR), min(offset + length, (s + 1) * SECTOR)
                    b[lo - offset:hi - offset] = data[lo - s * SECTOR:hi - s * SECTOR]
        return bytes(b)

    def sectors(self, fd, offset, data):
        """data split into whole sectors, reading the edges of an unaligned write."""
        out = {}
        end = offset + len(data)
        for s in range(offset // SECTOR, (end - 1) // SECTOR + 1):
            lo, hi = max(offset, s * SECTOR), min(end, (s + 1) * SECTOR)
            if hi - lo == SECTOR:
                out[s] = data[lo - offset:hi - offset]
            else:
                old = bytearray(self.read(fd, s * SECTOR, SECTOR))
                old[lo - s * SECTOR:hi - s * SECTOR] = data[lo - offset:hi - offset]
                out[s] = bytes(old)
        return out

    def commit(self, fd, held):
        """held made durable on IMAGE, in sector order; recorded as one epoch."""
        epoch = sorted(held.items())[len(held) // 2:]
        for s, data in epoch:
            os.pwrite(fd, data, s * SECTOR)
        os.fsync(fd)
        self.epochs.append(epoch)
        self.stats['sectors_committed'] += len(epoch)

    def serve(self, conn, fd):
        self.negotiate(conn)
        while True:
            magic, flags, kind, handle, offset, length = struct.unpack('>IHHQQI', self.recv(conn, 28))
            if magic != REQUEST_MAGIC:
                raise ValueError('request magic %x' % magic)
            error, payload = 0, b''
            if kind == CMD_READ:
                if offset + length > self.size:
                    error = EINVAL
                else:
                    payload = self.read(fd, offset, length)
            elif kind == CMD_WRITE:
                data = self.recv(conn, length)
                if offset + length > self.size:
                    error = EINVAL
                else:
                    with self.lock:
                        self.stats['writes'] += 1
                        new = self.sectors(fd, offset, data)
                        if flags & CMD_FLAG_FUA:
                            self.stats['fua_writes'] += 1
                            for s in new:
                                self.held.pop(s, None)
                            self.commit(fd, new)
                        else:
                            self.held.update(new)
            elif kind == CMD_FLUSH:
                with self.lock:
                    self.stats['flushes'] += 1
                    if self.held:
                        self.stats['flushes_with_data'] += 1
                        self.commit(fd, self.held)
                        self.held = {}
            elif kind == CMD_DISC:
                return
            else:
                error = EINVAL
            conn.sendall(struct.pack('>IIQ', SIMPLE_REPLY, error, handle) + payload)
