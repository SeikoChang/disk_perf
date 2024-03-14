#!/usr/bin/env python

import time, os, sys
import datetime
from hashlib import md5
from time import localtime
import string, random
import psutil
import platform

if platform.system().lower() == "darwin":
    DSIK = ''
elif platform.system().lower() == "windows":
    DISK = 'PhysicalDrive0'
else:
    DISK = 'sda1'

ZEN = """
The Zen of Python, by Tim Peters

Beautiful is better than ugly.

Explicit is better than implicit.

Simple is better than complex.

Complex is better than complicated.

Flat is better than nested.

Sparse is better than dense.

Readability counts.

Special cases aren't special enough to break the rules.

Although practicality beats purity.

Errors should never pass silently.

Unless explicitly silenced.

In the face of ambiguity, refuse the temptation to guess.

There should be one-- and preferably only one --obvious way to do it.

Although that way may not be obvious at first unless you're Dutch.

Now is better than never.

Although never is often better than *right* now.

If the implementation is hard to explain, it's a bad idea.

If the implementation is easy to explain, it may be a good idea.

Namespaces are one honking great idea -- let's do more of those!



The Zen of Python, by Tim Peters

Beautiful is better than ugly.

Explicit is better than implicit.

Simple is better than complex.

Complex is 
"""

now = lambda : time.time()

test_load = [1, 32, 64, 128, 256, 512, 1024, 16384, 262144, 524288, 1048676] # filesize in KiB

def generate_random_filename_with_timestemp(prefix=""):
    if not prefix:
        prefix = "tempfile"
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    return "{}_{}".format(prefix, suffix) # e.g. 'mylogfile_120508_171442'

def generate_random_filename(prefix=""):
    if not prefix:
        prefix = "tempfile"
    suffix = md5(str(localtime()).encode('utf-8')).hexdigest()
    return "{}_{}".format(prefix, suffix)

def generate_random_filename2(prefix=""):
    if not prefix:
        prefix = "tempfile"
    suffix = "".join(random.choice(string.ascii_letters) for _ in range(16))
    return "{}_{}".format(prefix, suffix)

def utf8len(s):
    return len(s.encode('utf-8'))

def file_write(filename, filesize, block_size=64, sequential=True): # filesize, bloack_size in KiB
    block_size *= 1024 # bloack_size in bytes
    filesize *= 1024 # filesize in bytes
    written_bytes = 0
    if sequential:
        with open(filename, 'wb') as f:
            while True:
                missing_bytes = filesize - written_bytes
                if missing_bytes > block_size:
                    f.write(os.urandom(block_size))
                    written_bytes += block_size
                else:
                    f.write(os.urandom(missing_bytes))
                    break
    else:
        # flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY if not os.path.exists(filename) else os.O_WRONLY
        flags = os.O_CREAT | os.O_WRONLY
        f = os.open(filename, flags, 0o777) # low-level I/O
        # generate random write positions
        offsets = list(range(0, filesize, block_size))
        last_offset = offsets[-1]
        last_buff = filesize % block_size
        random.shuffle(offsets)

        for blocks_num, offset in enumerate(offsets, 1):
            os.lseek(f, offset, os.SEEK_SET)  # set position
            if offset == last_offset:
                os.write(f, os.urandom(last_buff))  # write from position
            else:
                os.write(f, os.urandom(block_size))  # write from position

        os.close(f)

def disk_write_speed_measurement(filename, filesize, block_size=64, duration=10, sequential=True):
    rounds = 0
    start = now()
    while now() - start < duration:
        file_write(filename=filename, filesize=filesize, block_size=block_size, sequential=sequential)
        rounds += 1

    diff = now() - start
    throughput = filesize * rounds / (diff * 1024) # in MiB / sec
    # iops = rounds / diff # = throughput * 1024 / filesize
    iops = throughput / block_size * 1024 # = throughput * 1024 / filesize

    return throughput, iops

def file_read(filename, filesize, block_size, sequential=True):
    block_size *= 1024 # bloack_size in bytes
    filesize *= 1024 # filesize in bytes
    # generate random read positions
    offsets = list(range(0, filesize, block_size))
    if not sequential:
        random.shuffle(offsets)

    f = os.open(filename, os.O_RDONLY, 0o777)  # low-level I/O
    for blocks_num, offset in enumerate(offsets, 1):
        os.lseek(f, offset, os.SEEK_SET)  # set position
        buff = os.read(f, block_size)  # read from position
        # if not buff:
            # break  # if EOF reached

    os.close(f)
    
def disk_read_speed_measurement(filename, filesize, block_size=64, duration=10, sequential=True):
    # filesize = os.stat(filename).st_size // 1024  # in KiB

    rounds = 0
    start = now()
    while now() - start < duration:
        file_read(filename=filename, filesize=filesize, block_size=block_size, sequential=sequential)
        rounds += 1
    diff = now() - start
    throughput = filesize * rounds / (diff * 1024) # in MiB / sec
    # iops = rounds / diff # throughput / (block_size * 1024)
    iops = throughput / block_size * 1024

    return throughput, iops

def disk_speed_measurement(filesize, block_size=64, loop=5, duration=5, output="hdd_stats.csv", summary="hdd_summary.csv"):
    avg = lambda lst : round(sum(lst) / len(lst), 2)
    
    col_name = ["Filesize (KiB)", "Type", "Read MiB/sec", "Write MiB/sec", "reads/sec", "writes/sec", "IOPS"]
    if not os.path.exists(summary):
        with open(summary, "w+") as _sum:
            _sum.write(", ".join(col_name) + "\n")

    col_name = ["Date", "Time", "Filesize (KiB)", "Type", "Read MiB/sec", "Write MiB/sec", "reads/sec", "writes/sec", "IOPS", "Read MiB/sec", "Write MiB/sec", "reads/sec", "writes/sec", "IOPS" ]
    if not os.path.exists(output):
        with open(output, "w+") as out:
            out.write(", ".join(col_name) + "\n")

    throughput_writes, iops_writes = [], []
    throughput_reads, iops_reads = [], []
    for i in range(loop):
        print('{0}_{1}/{2}_{0}'.format('=' * 32, i + 1, loop))
        filename = generate_random_filename2()

        disks = psutil.disk_io_counters(perdisk=True)
        target_disk = disks[DISK]
        write_bytes = target_disk.write_bytes
        read_bytes = target_disk.read_bytes
        read_count = target_disk.read_count
        write_count = target_disk.write_count

        ts = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y, %H:%M:%S')
        start = now()
    
        print("start sequential write testing with fileaize = {} KB, filename = {}, block_size = {} KB, duration = {} secs".format(filesize, filename, block_size, duration))
        throughput_write, iops_write = disk_write_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration, sequential=True)
        throughput_writes.append(throughput_write), iops_writes.append(iops_write)
        throughput_write, iops_write = round(throughput_write, 2), round(iops_write, 2)

        print("start sequential read testing with fileaize = {} KB, filename = {}, block_size = {} KB, duration = {} secs".format(filesize, filename, block_size, duration))
        throughput_read, iops_read = disk_read_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration, sequential=True)
        throughput_reads.append(throughput_read), iops_reads.append(iops_read)
        throughput_read, iops_read = round(throughput_read, 2), round(iops_read, 2)

        diff = now() - start
        disks = psutil.disk_io_counters(perdisk=True)
        target_disk = disks[DISK]
        write_speed = round((target_disk.write_bytes - write_bytes) / (diff * 1024 * 1024), 2)
        readb_speed = round((target_disk.read_bytes - read_bytes) / (diff * 1024 * 1024), 2)
        write_iops = round((target_disk.write_count - write_count) / diff, 2)
        read_iops = round((target_disk.read_count - read_count) / diff, 2)
    
        data = [ts, filesize, "sequential", throughput_read, throughput_write, iops_read, iops_write, iops_read + iops_write, readb_speed, write_speed, read_iops, write_iops, round(read_iops + write_iops, 2)]
        with open(output, "a+") as out:
            out.write(", ".join(map(str, data)) + "\n")

        os.remove(filename)

    avg_throughput_reads, avg_throughput_writes, avg_iops_reads, avg_iops_writes = avg(throughput_reads), avg(throughput_writes), avg(iops_reads), avg(iops_writes)
    data = [filesize, "sequential", avg_throughput_reads, avg_throughput_writes, avg_iops_reads, avg_iops_writes, round(avg_iops_reads + avg_iops_writes, 2)]
    with open(summary, "a+") as _sum:
        _sum.write(", ".join(map(str, data)) + "\n")
    print('{0}_{1}/{2}_{0}\n'.format('=' * 32, i + 1, loop))
    print("Disk sequential writing speed: {0:.2f} MiB per second ({1:.4f} MB)".format(avg_throughput_writes, filesize / 1024))
    print("Disk iops: {0:.2f} per second".format(avg_iops_writes))
    print("Disk sequential reading speed: {0:.2f} MiB per second ({1:.4f} MB)".format(avg_throughput_reads, filesize / 1024))
    print("Disk iops: {0:.2f} per second".format(avg_iops_reads))
    print("\n")

    throughput_writes, iops_writes = [], []
    throughput_reads, iops_reads = [], []
    for i in range(loop):
        print('{0}_{1}/{2}_{0}'.format('=' * 32, i + 1, loop))
        filename = generate_random_filename2()

        disks = psutil.disk_io_counters(perdisk=True)
        target_disk = disks[DISK]
        write_bytes = target_disk.write_bytes
        read_bytes = target_disk.read_bytes
        read_count = target_disk.read_count
        write_count = target_disk.write_count

        ts = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y, %H:%M:%S')
        start = now()

        print("start random write testing with fileaize = {} KB, filename = {}, block_size = {} KB, duration = {} secs".format(filesize, filename, block_size, duration))
        throughput_write, iops_write = disk_write_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration, sequential=False)
        throughput_writes.append(throughput_write), iops_writes.append(iops_write)
        throughput_write, iops_write = round(throughput_write, 2), round(iops_write, 2)

        print("start random read testing with fileaize = {} KB, filename = {}, block_size = {} KB, duration = {} secs".format(filesize, filename, block_size, duration))
        throughput_read, iops_read = disk_read_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration, sequential=False)
        throughput_reads.append(throughput_read), iops_reads.append(iops_read)
        throughput_read, iops_read = round(throughput_read, 2), round(iops_read, 2)


        diff = now() - start
        disks = psutil.disk_io_counters(perdisk=True)
        target_disk = disks[DISK]
        write_speed = round((target_disk.write_bytes - write_bytes) / (diff * 1024 * 1024), 2)
        readb_speed = round((target_disk.read_bytes - read_bytes) / (diff * 1024 * 1024), 2)
        write_iops = round((target_disk.write_count - write_count) / diff, 2)
        read_iops = round((target_disk.read_count - read_count) / diff, 2)
    
        data = [ts, filesize, "random", throughput_read, throughput_write, iops_read, iops_write, iops_read + iops_write, readb_speed, write_speed, read_iops, write_iops, round(read_iops + write_iops, 2)]
        with open(output, "a+") as out:
            out.write(", ".join(map(str, data)) + "\n")

        os.remove(filename)

    avg_throughput_reads, avg_throughput_writes, avg_iops_reads, avg_iops_writes = avg(throughput_reads), avg(throughput_writes), avg(iops_reads), avg(iops_writes)
    data = [filesize, "random", avg_throughput_reads, avg_throughput_writes, avg_iops_reads, avg_iops_writes, round(avg_iops_reads + avg_iops_writes, 2)]
    with open(summary, "a+") as _sum:
        _sum.write(", ".join(map(str, data)) + "\n")
    print('{0}_{1}/{2}_{0}\n'.format('=' * 32, i + 1, loop))
    print("Disk random writing speed: {0:.2f} MiB per second ({1:.4f} MB)".format(avg_throughput_writes, filesize / 1024))
    print("Disk iops: {0:.2f} per second".format(avg_iops_writes))
    print("Disk random reading speed: {0:.2f} MiB per second ({1:.4f} MB)".format(avg_throughput_reads, filesize / 1024))
    print("Disk iops: {0:.2f} per second".format(avg_iops_reads))
    print("\n")

def test():
    for filesize in test_load[:]:
        disk_speed_measurement(filesize=filesize)

if __name__ == "__main__":
    test()
