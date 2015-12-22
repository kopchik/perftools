#!/usr/bin/env python3

from useful import __version__ as useful_version
assert useful_version >= (1,5)
from useful.log import Log


from resource import setrlimit, RLIMIT_NOFILE
from socket import gethostname
from os import geteuid
from sys import exit

if geteuid() != 0:
  exit("you need root to run this scrips")

log = Log("config")
HOSTNAME = gethostname()
WARMUP_TIME = 10
IDLENESS = 45
MEASURE_TIME = 180
BOOT_TIME = 10
setrlimit(RLIMIT_NOFILE, (10240, 10240))
VMS = []


######################
# HOST-SPECIFIC CFGs #
######################

if HOSTNAME in ['limit', 'fx']:
  from perf.qemu import Template, Bridged, Drive
  from perf.numa import topology
  IDLENESS = 70
  SIBLINGS = True
  RESULTS = "./results/limit/"
  BOOT_TIME = 15
  def idleness_ok():
    TODO

#  template = Template(
#    name = "template",
#    auto = False,
#    #cpus = [0],  # affinity
#    mem  = 2048,
#    cores = 4,
#    #boot = "d",
#    net  = [Bridged(ifname="research", model='virtio-net',
#           mac="52:54:91:5E:38:BB", br="intbr")],
#    drives = [Drive("/home/virtuals/research.qcow2",
#              iface="virtio", cache="unsafe"),
#              #CDROM("/home/virtuals/archlinux-2014.03.01-dual.iso")
#              ]
#  )


  print("CPU AFFINITY DISABLED")
  for i, cpu in enumerate(topology.all):
    vm = Template(
        name = "vm%s"%i,
        auto = True,
#        cpus = [i],  # affinity
        devs = [Bridged(ifname="vm%s"%i, model='e1000', mac="52:54:91:5E:38:0%s"%i, br="intbr"),
                Drive("/home/virtuals/vm%s.qcow2"%i,
                  master="/home/virtuals/research.qcow2",
                  temp=True,  # destroy image after stop
                  cache="unsafe")
               ],
        addr = "172.16.5.1%s"%i
        )
    VMS.append(vm)


elif HOSTNAME == 'ux32vd':
  pass


##########
# EXYNOS #
##########

elif HOSTNAME in ['u2', 'perf0']:
  SIBLINGS = False
  RESULTS = "./results/u2/"
  from perf.bare import Bare
  for x in range(4):
    bare = Bare([x])
    VMS.append(bare)

  # from perf.lxc import LXC
  # LXC_PREFIX = "/btrfs/"
  # for x in range(4):
  #   ip = str(IPv4Address("172.16.5.10")+x)
  #   name = "perf%s" % x
  #   lxc = LXC(name=name, root="/btrfs/{}".format(name), tpl="/home/perftemplate/",
  #             addr=ip, gw="172.16.5.1", cpus=[x])
  #   VMS.append(lxc)


else:
  raise Exception("Unknown host. Please configure it first in config.py.")


##############
# BENCHMARKS #
##############

BENCHES = "/home/sources/perftest/benches/"
basis = dict(
  # INIT DB: sudo -u postgres pgbench -i
  pgbench = "sudo -u postgres pgbench -c 20 -s 10 -T 100000",
  static  = "siege -c 100 -t 666h http://localhost/big_static_file",  # TODO: too CPU consuming,
  wordpress = "siege -c 10 -t 666h http://localhost/",
  # matrix = "/home/sources/perftest/benches/matrix.py -s 1024 -r 1000",
  matrix = BENCHES + "matrix 2048",
  sdag   = BENCHES + "test_SDAG/test_sdag -t 5 -q 1000 /home/sources/perftest/benches/test_SDAG/dataset.dat",
  sdagp  = BENCHES + "test_SDAG/test_sdag+ -t 5 -q 1000 /home/sources/perftest/benches/test_SDAG/dataset.dat",
  blosc  = BENCHES + "pyblosc.py -r 10000000",
  ffmpeg = "bencher.py -s 100000 -- ffmpeg -i /home/sources/avatar_trailer.m2ts \
            -threads 1 -t 10 -y -strict -2 -loglevel panic \
            -acodec aac -aq 100 \
            -vcodec libx264 -preset fast -crf 22 \
            -f mp4 /dev/null",
)

def loop(cmd, dir=None):
  loopcmd = "while true; do {cmd} || break; echo '====='; done".format(cmd=cmd)
  loopcmd = "sh -c '%s'" % loopcmd
  if dir:
    loopcmd = "cd %s && " % dir + loopcmd
  return loopcmd

newtests = dict(
  gcc = "sh -c 'cd /home/sources/linux-4.3; while true; do make clean --quiet && make -j2 --quiet || break; echo '====='; done'",
  zip_kern = "zip -qr /dev/null /home/sources/linux-4.3_dist",
  bzip2_kern = loop("tar -cj /home/sources/linux-4.3_dist > /dev/null"),
  sb_cpu = loop("sysbench --test=cpu --cpu-max-prime=100000 run"),
  sb_oltp = loop("sysbench --test=oltp run"),
  sb_mem_seq_read = loop("sysbench --test=memory --memory-oper=read"),
  sb_mem_rnd_read = loop("sysbench --test=memory --memory-oper=read --memory-access-mode=rnd run"),
  sb_mem_seq_write = loop("ysbench --test=memory --memory-oper=write run"),
  sb_mem_rnd_write = loop("sysbench --test=memory --memory-oper=write --memory-access-mode=rnd run"),

)


def enable_debug():
  global WARMUP_TIME, MEASURE_TIME, IDLENESS
  log.critical("debug mode enabled")
  WARMUP_TIME = 0
  MEASURE_TIME = 0.5
  IDLENESS = 70
#enable_debug()
