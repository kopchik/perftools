#!/usr/bin/env python3
from config import VMS, basis, IDLENESS, BOOT_TIME
import perf; perf.min_version((2,11))
from perf.utils import wait_idleness
from perf.numa import topology, get_cpu_r
from subprocess import DEVNULL
import psutil


import random
import time


def generate_load(vms, warmup=10):
  for cpu, vm in zip(topology.all, vms):
    bmark, cmd = random.choice(list(basis.items()))
    print(bmark, vm, cpu)
    vm.pipe = vm.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
    vm.bmark = bmark
  time.sleep(warmup)


def get_alloc(vms):
  alloc = []
  for vm in vms:
    pid = vm.pid
    if not pid:
      continue
    process = psutil.Process(pid)
    cpu_thread, _, _ = max(process.threads(), key=lambda x:[1])
    tidcpu = get_cpu(cpu_thread)
    print(vm, tidcpu)
    #TODOvm.set_cpus([cpu])
    #TODOTODO("fix affinity")


def measure_perf():
  pass


def optimize():
  pass


def stop_all(vms):
  if any([vm.kill() for vm in vms]):
    print("giving old VMs time to die...")
    time.sleep(3)

  for vm in vms:
    if vm.pipe:
      # vm.pipe.killall()  # not needed
      vm.bmark = None
      vm.pipe = None
  wait_idleness(IDLENESS*6)


if __name__ == '__main__':
  vms = VMS
  [vm.kill() for vm in vms]
  time.sleep(5)
  [vm.start() for vm in vms]
  time.sleep(BOOT_TIME)

  for x in range(10):
    generate_load(vms)
    get_alloc(vms)
    time.sleep(10)  # warmup
    stop_all(vms)
    TODO("wait tasks to stop")
  import pdb; pdb.set_trace()

