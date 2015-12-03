#!/usr/bin/env python3
from utils import KVMSanitizer
from config import VMS
import atexit

class DB:
  def __init__(self, path):
    self.path = path
    atexit.register(self.save)


def regr(vms, new):
  events = ['instructions', 'cycles', 'LLC-stores']
  vm = vms[0]



if __name__ == '__main__':
  vms = VMS
  with KVMSanitizer(vms):
    regr(vms)

