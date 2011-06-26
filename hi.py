from inspect import currentframe
from lazypy import LazyEvaluated

g = 8

def f():
    global g
    return currentframe()

def non():
    global qux
    print qux

def hi():
    global g
    a = 5
    screw(currentframe(), locals())
    import pdb;pdb.set_trace()
    
    return a

def screw(frame, localses):
    #frame.f_locals['a'] = 800
    localses['a'] = 800


# class StackedPromise(object):
#     """Dynamically-scoped lazy proxy to a value"""
# 
#     __metaclass__ = PromiseMetaClass
# 
#     def __init__(self, original):
#         self._original = original
# 
#     def __force__(self):
#         return self._original
