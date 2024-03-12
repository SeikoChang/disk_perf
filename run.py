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

def file_generate_random_binary(filename, filesize, block_size=64): # filesize, bloack_size in KiB
    block_size *= 1024 # bloack_size in bytes
    filesize *= 1024 # filesize in bytes
    written_bytes = 0
    with open(filename, 'wb') as f:
        while True:
            missing_bytes = filesize - written_bytes
            if missing_bytes > block_size:
                f.write(os.urandom(block_size))
                written_bytes += block_size
            else:
                f.write(os.urandom(missing_bytes))
                break

def disk_write_speed_measurement(filename, filesize, block_size=64, duration=10):
    start = now()
    rounds = 0
    while now() - start < duration:
        file_generate_random_binary(filename=filename, filesize=filesize, block_size=block_size)
        rounds += 1

    diff = now() - start
    throughput = filesize * rounds / (diff * 1024) # in MiB / sec
    # iops = rounds / diff # = throughput * 1024 / filesize
    iops = throughput / block_size * 1024 # = throughput * 1024 / filesize

    return throughput, iops

def file_random_read(filename, filesize, block_size):
    f = os.open(filename, os.O_RDONLY, 0o777)  # low-level I/O
    # generate random read positions
    offsets = list(range(0, filesize, block_size)) # in bytes
    random.shuffle(offsets)

    for blocks_num, offset in enumerate(offsets, 1):
        os.lseek(f, offset, os.SEEK_SET)  # set position
        buff = os.read(f, block_size)  # read from position
        if not buff:
            break  # if EOF reached

    os.close(f)
    
def disk_read_speed_measurement(filename, filesize, block_size=64, duration=10):
    # filesize = os.stat(filename).st_size // 1024  # in KiB

    rounds = 0
    start = now()
    while now() - start < duration:
        file_random_read(filename, filesize, block_size)
        rounds += 1
    diff = now() - start
    throughput = filesize * rounds / (diff * 1024) # in MiB / sec
    # iops = rounds / diff # throughput / (block_size * 1024)
    iops = throughput / block_size * 1024


    return throughput, iops

def disk_speed_measurement(filesize, block_size=64, loop=1, duration=5, output ="hddstats.csv"):
    throughput_write, iops_write = [], []
    throughput_read, iops_read = [], []
    avg = lambda lst : round(sum(lst) / len(lst), 2)

    disks = psutil.disk_io_counters(perdisk=True)
    target_disk = disks[DISK]
    read_bytes = target_disk.read_bytes
    write_bytes = target_disk.write_bytes

    if not os.path.exists(output):
        logging = open(output, "w+")
        logging.write("Date, Time, Written MB, Read MB, Writen Total MB, Read Total MB" + "\n")
        logging.close

    for i in range(loop):
        print('{0}_{1}/{2}_{0}'.format('=' * 32, i + 1, loop))
        filename = generate_random_filename2()
        ts = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y,%H:%M:%S')

        print("start write testing with fileaize = {} KB, filename = {} block_size = {} duration = {}".format(filesize, filename, block_size, duration))
        throughput, iops = disk_write_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration)
        throughput_write.append(throughput), iops_write.append(iops)

        print("start read testing with fileaize = {} KB, filename = {} block_size = {} duration = {}".format(filesize, filename, block_size, duration))
        throughput, iops = disk_read_speed_measurement(filename=filename, filesize=filesize, block_size=block_size, duration=duration)
        throughput_read.append(throughput), iops_read.append(iops)

        disks = psutil.disk_io_counters(perdisk=True)
        target_disk = disks[DISK]
        write_bytes_now = target_disk.write_bytes
        read_bytes_now = target_disk.read_bytes
        writebcy = write_bytes_now - write_bytes
        readbcy = read_bytes_now - read_bytes
        write_bytes = write_bytes_now
        read_bytes = read_bytes_now
        logging = open(output, "a+")
        logging.write(ts + "," + str(writebcy/1048576) + "," + str(readbcy/1048576) + "," + str(write_bytes_now/1048576) + "," + str(read_bytes_now/1048576) + "\n")
        logging.close

        os.remove(filename)
    print('{0}_{1}/{2}_{0}\n'.format('=' * 32, i + 1, loop))
    print("Disk writing speed: {0:.2f} MiB per second".format(avg(throughput_write)))
    print("Disk iops: {0:.2f} per second".format(avg(iops_write)))
    print("Disk reading speed: {0:.2f} MiB per second".format(avg(throughput_read)))
    print("Disk iops: {0:.2f} per second".format(avg(iops_read)))
    print("\n")
    
def test():
    for filesize in test_load[:]:
        disk_speed_measurement(filesize=filesize)

if __name__ == "__main__":
    test()
