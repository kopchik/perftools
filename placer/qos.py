#!/usr/bin/env python3

import perf; perf.min_version((2,14))
from perf.perftool import NotCountedError

from useful.log import Log
from useful.small import tlaunch
from useful.mstring import prints
import useful; assert useful.__version__ >= (1,21)

from collections import deque, defaultdict
from itertools import islice
from queue import Queue
from config import VMS
import time

from utils import KVMSanitizer
from statistics import mean

log = Log("main")


def calc_ipc(d):
  ins = d['instructions']
  cycles = d['cycles']
  if cycles == 0:
    return None, None, None
  ipc = ins/cycles
  return ipc, ins, cycles


def dbfabric():
  class VMStats:
    shared_ipc = deque(maxlen=10000)
    frozen_ipc = deque(maxlen=10000)
    shared_cycles = deque(maxlen=10000)
  return VMStats
db = defaultdict(dbfabric)


def measure(vms, q):
  interval = 100
  while True:
    for vm in vms:
      time.sleep(1.0)
      try:
        shared = vm.ipcstat(interval=interval, raw=True)
        with vm:
          frozen = vm.ipcstat(interval=interval, raw=True)
      except NotCountedError:
        log.measure.error("perf sampling failed on %s" % vm)
        continue
      q.put((vm, shared, frozen))


def dbstore(q):
  while True:
    vm, shared, frozen = q.get()
    #log.dbstore.debug("I got something in the queue: {}".format(vm))
    sh_ipc, ins, cycles = calc_ipc(shared)
    db[vm].shared_ipc.appendleft(sh_ipc)

    fr_ipc, *_ = calc_ipc(frozen)
    db[vm].frozen_ipc.appendleft(fr_ipc)


def status(vms, q, min_perf=0.8, max_perf=0.85):
  while True:
    for vm in vms:
      stats = db[vm]
      sh_ipc = list(islice(stats.shared_ipc, 0, 3))
      fr_ipc = list(islice(stats.frozen_ipc, 0, 3))
      if not sh_ipc or not fr_ipc:
        log.status.debug("no data for %s" % vm)
        continue
      sh_ipc = mean(sh_ipc)
      fr_ipc = mean(fr_ipc)

      r = sh_ipc / fr_ipc
      prints("STATS {vm}: {sh_ipc:.2f} {fr_ipc:.2f} interference: {r:.3f}")
      if min_perf <r < max_perf:
        log.status.debug("interference is okay: %.2f" % r)
        pass
      elif r < min_perf:
        adjust = r / min_perf
        log.status("high interference, adjusting by %.2f" % adjust)
        q.put(adjust)
      elif r > max_perf:
        adjust = r / max_perf
        log.status("LOW interference, adjusting by %.2f" % adjust)
        q.put(adjust)

    time.sleep(3)

# TODO: notify when new stats ready

def prioritize(vms, rest, q):
  from cgroupspy.trees import Tree
  t = Tree()
  cpu_node = t.get_node_by_path('/cpu/badluck')
  for vm in rest:
    cpu_node.controller.procs = vm.pid
    log.prioritize.debug("%s is ready for throttling" % vm)
  period = cpu_node.controller.cfs_period_us
  initial_quota = period * len(rest)
  cpu_node.controller.cfs_quota_us = initial_quota
  upper_cap = len(rest) * period
  while True:
    tune = q.get()
    period = cpu_node.controller.cfs_period_us
    quota = cpu_node.controller.cfs_quota_us
    quota *= tune
    quota = min(quota, upper_cap)  # cap so it does not grow infinitly
    cpu_node.controller.cfs_quota_us = quota
    log.prioritize.debug("throttling: %.2f (out of %s)" % (quota/period, len(rest)))


if __name__ == '__main__':
  vms = VMS
  prioritized = [vms[0]]
  rest = [vm for vm in vms if vm.name != 'vm0']
  with KVMSanitizer(vms, ['sdag', 'sdagp', 'blosc', 'matrix', 'static','pgbench', 'wordpress', 'ffmpeg']):
    measq = Queue()
    notifyq = Queue()
    tlaunch(dbstore, measq)
    tlaunch(status, prioritized, notifyq)
    tlaunch(prioritize, prioritized, rest, notifyq)
    t = tlaunch(measure, vms, measq)
    t.join()

