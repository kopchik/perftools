from time import sleep
from config import IDLENESS, VMS, basis
from subprocess import DEVNULL
from perf.utils import wait_idleness, run


class KVMSanitizer:
  """ Launch all VMS at start, stop them at exit. """

  def __init__(self, vms, benchmarks=[], debug=False):
    assert len(benchmarks) <= len(vms)

    self.benchmarks = benchmarks
    self.vms = vms
    self.debug = debug
    run("killall -SIGCHLD tmux")
    if any([vm.kill() for vm in vms]):
      print("giving old VMs time to die...")
      sleep(3)
    run("killall -SIGCHLD tmux")
    if any(vm.pid for vm in vms):
      raise Exception("there are VMs still running!")
    if any([vm.start() for vm in vms]):
      print("let VMs to boot")
      sleep(10)
    else:
      print("no VM start was requested")

  def __enter__(self):
    map = {}
    if not self.debug:
      wait_idleness(IDLENESS*6)
    for bname, vm in zip(self.benchmarks, self.vms):
      #print("{} for {} {}".format(bname, vm.name, vm.pid))
      cmd = basis[bname]
      vm.pipe = vm.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
      vm.bname = bname
    return map

  def __exit__(self, ex_type, ex_val, ex_tb):
    if ex_type:
      print("exception in block:\n", ex_type, ex_val)
      #import pdb; pdb.set_trace()
    print("tearing down the system")
    for vm in self.vms:
      if not vm.pid:
        #print(vm, "already dead, not stopping it on tear down")
        continue
      try:
        vm.unfreeze()
        vm.shared()
      except:
        pass
      if not hasattr(vm, "pipe") or vm.pipe is None:
        continue
      ret = vm.pipe.poll()
      if ret is not None:
        print("Test {bmark} on {vm} died with {ret}! Manual intervention needed\n\n" \
              .format(bmark=vm.bname, vm=vm, ret=ret))
        import pdb; pdb.set_trace()
      # vm.pipe.killall() TODO: hangs after tests. VMs frozen?
    #for vm in self.vms:
    #  vm.stop()
    [vm.kill() for vm in VMS]
    run("killall -SIGCHLD tmux")
