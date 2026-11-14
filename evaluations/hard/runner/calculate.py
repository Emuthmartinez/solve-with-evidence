"""Run one synthetic calculation in a sealed macOS Python subprocess."""
import collections
import ctypes
import decimal
import fractions
import functools
import heapq
import itertools
import json
import math
import operator
import random
import re
import resource
import statistics
import sys

code = sys.stdin.read()
sandbox = ctypes.CDLL("/usr/lib/libsandbox.1.dylib")
error = ctypes.c_char_p()
if sandbox.sandbox_init(b"(version 1)(deny default)(allow signal (target self))",
                        0, ctypes.byref(error)) != 0:
    raise RuntimeError("Could not isolate calculator")
resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
random.seed(0)
scope = {"__name__": "__main__", **{module.__name__: module for module in
         (collections, decimal, fractions, functools, heapq, itertools, json,
          math, operator, random, re, statistics)}}
exec(compile(code, "<calculation>", "exec"), scope)
