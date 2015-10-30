#!/usr/bin/env python3
import perf; perf.min_version((2,13))
from perf.numa import topology, get_cur_cpu, get_cpu_r
from perf.utils import wait_idleness, run, threadulator
from perf.perftool import sysperf
from itertools import permutations
from useful.mstring import prints
from useful.small import flatten
from useful.log import logfilter
from functools import reduce

from subprocess import DEVNULL
import psutil
import random
import time
import sys

from config import VMS, basis, IDLENESS, BOOT_TIME
from combinator import combinator

logfilter.rules.append(["*.debug", False])

def generate_load(num=8, cpus=topology.all):
  load = []
  for cpu in range(num):
    bmark, cmd = random.choice(list(basis.items()))
    load.append((bmark, cpu))
  return load


def apply_load(load, vms, warmup=10):
  for vm, (bmark, cpu) in zip(vms, load):
    cmd = basis[bmark]
    vm.pipe = vm.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
    vm.bmark = bmark
    vm.set_cpus([cpu])
  time.sleep(warmup)
  return load


def apply_alloc(alloc, vms):
  checked_vms = set()
  for bmark, cpu in alloc:
    for vm in vms:
      if vm in checked_vms:
        continue
      if vm.bmark == bmark:
        vm.set_cpus([cpu])
        checked_vms.add(vm)
        break
    else:
      import pdb; pdb.set_trace()
      raise Exception("cannot assign VM")


def get_alloc(vms):
  alloc = []
  for vm in vms:
    pid = vm.pid
    if not pid:
      continue
    process = psutil.Process(pid)


    p1 = max(process.threads(), key=lambda x:x[1])
    cpu_thread, _, _ = max(process.threads(), key=lambda x:[1])
    tidcpu = get_cur_cpu(cpu_thread)
    alloc.append((vm, tidcpu))
    print(vm, tidcpu)
  print(alloc)
  import pdb; pdb.set_trace()
    #TODOvm.set_cpus([cpu])
    #TODOTODO("fix affinity")


def measure_perf():
  pass


def optimize():
  pass


def stop_tasks(vms):
  for vm in vms:
    if vm.pipe:
      vm.pipe.killall()
      vm.bmark = None
      vm.pipe = None
  wait_idleness(IDLENESS*6)


import runpy
path = "/home/sources/perfresults/perforator2/fx/llc.py"
mod = runpy.run_path(path)
estimate = mod['estimate']
params = mod['calc_regr']()
def brutforce(bmarks, ht_pairs=None):
  ht_pairs = topology.ht_pairs
  min_oh, max_oh = 10000, 0
  min_alloc =  max_alloc = None

  for cpu_alloc in permutations(topology.all):
    cpu_alloc = list(flatten(cpu_alloc))
    alloc = list(zip(bmarks, cpu_alloc))
    r = estimate(alloc, topology.ht_map, *params)
    if r < min_oh:
      min_oh = r
      min_alloc = alloc
    if r > max_oh:
      max_oh = r
      max_alloc = alloc
  prints("{min_oh:.2f} {min_alloc}\n{max_oh:.2f} {max_alloc}\n{topology.ht_map}")
  return min_alloc



def geomean(nums):
    return (reduce(lambda x, y: x*y, nums))**(1.0/len(nums))

def performance(vms, interval=30*1000):
  results = {}
  def measure(vm):
    ipc = vm.ipcstat(interval=interval)
    results[vm] = ipc
  threadulator(measure, [[vm] for vm in vms])
  print(sorted(results.items(), key=lambda kv: kv[0].name), geomean(results.values()))
  return geomean(results.values())


test_loads = [[('sdag', 0), ('blosc', 1), ('blosc', 2), ('ffmpeg', 3), ('static', 4), ('matrix', 5), ('sdagp', 6), ('wordpress', 7)],
 [('static', 0), ('pgbench', 1), ('pgbench', 2), ('pgbench', 3), ('static', 4), ('matrix', 5), ('static', 6), ('static', 7)],
 [('blosc', 0), ('sdagp', 1), ('ffmpeg', 2), ('pgbench', 3), ('wordpress', 4), ('wordpress', 5), ('ffmpeg', 6), ('static', 7)],
 [('pgbench', 0), ('sdag', 1), ('matrix', 2), ('pgbench', 3), ('wordpress', 4), ('pgbench', 5), ('wordpress', 6), ('blosc', 7)],
 [('sdag', 0), ('sdagp', 1), ('sdag', 2), ('pgbench', 3), ('pgbench', 4), ('static', 5), ('sdagp', 6), ('static', 7)],
 [('sdagp', 0), ('blosc', 1), ('static', 2), ('pgbench', 3), ('ffmpeg', 4), ('matrix', 5), ('wordpress', 6), ('sdag', 7)],
 [('wordpress', 0), ('blosc', 1), ('sdag', 2), ('matrix', 3), ('blosc', 4), ('sdagp', 5), ('sdag', 6), ('blosc', 7)],
 [('ffmpeg', 0), ('wordpress', 1), ('pgbench', 2), ('ffmpeg', 3), ('pgbench', 4), ('ffmpeg', 5), ('sdagp', 6), ('wordpress', 7)],
 [('pgbench', 0), ('static', 1), ('matrix', 2), ('ffmpeg', 3), ('wordpress', 4), ('ffmpeg', 5), ('pgbench', 6), ('sdagp', 7)],
 [('blosc', 0), ('pgbench', 1), ('matrix', 2), ('matrix', 3), ('wordpress', 4), ('pgbench', 5), ('static', 6), ('pgbench', 7)]]

def try_all(vms):
  bmarks = ['pgbench', 'static', 'matrix', 'ffmpeg', 'wordpress', 'ffmpeg', 'pgbench', 'sdagp']
  for alloc in combinator(bmarks, topology.all, topology.ht_map):
    print(alloc)
    yield alloc
  

if __name__ == '__main__':
  vms = VMS
  run("killall -SIGCHLD tmux")
  time.sleep(0.1)
  [vm.kill() for vm in vms]
  time.sleep(2.0)
  run("killall -SIGCHLD tmux")
  time.sleep(0.3)
  vms = VMS
  time.sleep(5)
  [vm.start() for vm in vms]
  time.sleep(BOOT_TIME)

#  sys_speedups = []
#  geom_speedups = []
#  for load in try_all(vms):
#    apply_load(load, vms)
#    _, before = sysperf(t=30)
#    geom_before = performance(vms)
#
#    best_alloc = brutforce([bmark for bmark, cpu in load])
#    apply_alloc(best_alloc, vms)
#    _, after = sysperf(t=30)
#    geom_after = performance(vms)
#    
#    stop_tasks(vms)
#    speedup = after / before
#    sys_speedups.append(speedup)
#    geom_speedups.append(geom_before/geom_after)
#    prints("speedup: {speedup:.2f}\n===============")
#  print(sys_speedups)
#  print(geom_speedups)
  sys_perfs = []
  task_perfs = []
  t = 180
  for load in try_all(vms):
    apply_load(load, vms)
    _, sperf = sysperf(t=t)
    sys_perfs.append(sperf)
    tperf = performance(vms, interval=t*1000)
    task_perfs.append(tperf)
    stop_tasks(vms)
  print(sys_perfs)
  print(task_perfs)
