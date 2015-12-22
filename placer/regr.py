#!/usr/bin/env python3
from utils import KVMSanitizer
from config import VMS, basis as OLDTESTS, newtests as NEWTESTS
from perf.numa import topology, get_cur_cpu, get_cpu_r
import atexit

class DB:
  def __init__(self, path):
    self.path = path
    atexit.register(self.save)


def regr(vms, old, new):
  events = ['instructions', 'cycles', 'LLC-stores']
  fg, bg = vms[:2]
  fg_cpu, bg_cpu = topology.no_ht[:2]
  fg.set_cpus([fg_cpu])
  bg.set_cpus([bg_cpu])

  # step one: single
  for bmark, cmd in sorted(new.items()):
    p = fg.Popen(cmd)
    fg.bmark = bmark
    stats = fg.stat(events=events, interval=1*1000)
    print(bmark, stats)
    fg.pipe.killall()
    wait_idleness(IDLENESS*6)



if __name__ == '__main__':
  vms = VMS
  with KVMSanitizer(vms):
    regr(vms, OLDTESTS, NEWTESTS)

