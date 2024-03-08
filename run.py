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
    DISK = 'sba1'

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

test_load = [1, 2, 4, 16, 32, 64, 128, 256, 512, 1024, 10240, 102400] # filesize in KB

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

def generate_test_load(filenum=1, filesize=64): # filesize in KB
    for _ in range(filenum):
        filename = generate_random_filename2()
        # print(filename)
        generate_random_binary_file(filename, filesize)
        os.remove(filename)

def generate_random_binary_file(filename, filesize=64): # filesize in KB
    # size_zen = utf8len(ZEN) # size in bytes
    # print(size_zen)
    if not filesize:
        filesize = 64
    bloack_size = 1024 * 64
    written_bytes = 0
    with open(filename, 'wb') as f:
        while True:
            missing_bytes = filesize * 1024 - written_bytes
            if missing_bytes > bloack_size:
                f.write(os.urandom(bloack_size))
                written_bytes += bloack_size
            else:
                f.write(os.urandom(missing_bytes))
                break

def disk_write_speed_measurement(filenum=1, filesize=64, duration=1):
    disks = psutil.disk_io_counters(perdisk=True)
    target_disk = disks[DISK]
    read_bytes = target_disk.read_bytes
    write_bytes = target_disk.write_bytes

    out = "hddstats.csv"
    if not os.path.exists(out):
        logging = open(out,"w+")
        logging.write("Date, Time, Written MB, Read MB, Writen Total MB, Read Total MB" + "\n")
        logging.close

    start = now()
    counter = 0
    diff = 1
    # print(start)
    while now() - start < duration:
        # print(now())
        ts = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y,%H:%M:%S')
        try:
            generate_test_load(1, filesize)
        except:
            print("Fail to generate load")
            sys.exit(0)
        counter += 1

    diff = now() - start
    throughput = counter*filesize/(diff * 1024)
    iops = counter / diff # = throughput * 1024 / filesize

    disks = psutil.disk_io_counters(perdisk=True)
    target_disk = disks[DISK]
    write_bytes_now = target_disk.write_bytes
    read_bytes_now = target_disk.read_bytes
    writebcy = write_bytes_now - write_bytes
    readbcy = read_bytes_now - read_bytes
    write_bytes = write_bytes_now
    read_bytes = read_bytes_now
    logging = open(out,"a+")
    logging.write(ts + "," + str(writebcy/1048576) + "," + str(readbcy/1048576) + "," + str(write_bytes_now/1048576) + "," + str(read_bytes_now/1048576) + "\n")
    logging.close

    return throughput, iops

def disk_read_speed_measurement(filenum=1, filesize=64, duration=1):
    bloack_size = 64
    filename = generate_random_filename2()
    # print(filename)
    generate_random_binary_file(filename, filesize)
    f = os.open(filename, os.O_RDONLY, 0o777)  # low-level I/O
    # generate random read positions
    offsets = list(range(0, filesize, bloack_size)) # in bytes
    # random.shuffle(offsets)

    start = now()
    for blocks_num, offset in enumerate(offsets, 1):
        os.lseek(f, offset, os.SEEK_SET)  # set position
        buff = os.read(f, bloack_size)  # read from position
        if not buff: break  # if EOF reached

    print(blocks_num)
    diff = (now() - start) + 0.1
    throughput = filesize / (diff * 1024)
    iops = throughput / bloack_size # = throughput * 1024 / filesize

    os.close(f)
    os.remove(filename)
    return throughput, iops

def test():
    filenum = 1
    duration = 5
    for filesize in test_load[:]:
        print("start testing with fileaize = {} filenum = {} duration = {}".format(filesize, filenum, duration))
        throughput, iops = disk_write_speed_measurement(filenum=filenum, filesize=filesize, duration=duration)
        print("Disk writing speed: {0:.2f} Mbytes per second".format(throughput))
        print("Disk iops: {0:.2f} bytes per second".format(iops))
        throughput, iops = disk_read_speed_measurement(filenum=filenum, filesize=filesize, duration=duration)
        print("Disk reading speed: {0:.2f} Mbytes per second".format(throughput))
        print("Disk iops: {0:.2f} bytes per second".format(iops))

if __name__ == "__main__":
    test()
