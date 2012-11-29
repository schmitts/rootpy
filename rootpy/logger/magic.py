"""
Here be dragons.

This module contains hackery to bend the CPython interpreter to our will.

It's necessary because it's not possible to throw an exception from within a
ctypes callback. Instead, the exception is thrown from a line tracer which we
forcably insert into the appropriate frame. Then we make that frame's next
opcode a ``JUMP_ABSOLUTE`` to the last line of code. Yes.

This is a bad idea and should never be used anywhere important where reliability
is a concern. Also, if you like your sanity. This thing *will* break backtraces
when you least expect it, leading to you looking at the wrong thing.

What lies within is the product of a sick mind and should never be exposed to
humanity.
"""

# Set this to true if you're feeling lucky.
# (Otherwise the crash-debug-headache code is turned off)
class DANGER:
    enabled = False

import ctypes
import ctypes.util
import dis
import logging
import opcode
import os
import struct
import sys

from ctypes import POINTER, Structure, py_object, c_byte, c_int, c_voidp
from traceback import print_stack

import ROOT

from . import log; log = log[__name__]

ctypes.pythonapi.Py_IncRef.argtypes = ctypes.py_object,
ctypes.pythonapi.Py_DecRef.argtypes = ctypes.py_object,

svp = ctypes.sizeof(ctypes.c_voidp)
_keep_alive = []

ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

def libcore():
    if sys.platform == "darwin":
        return "libCore.dylib"
    return "libCore.so"

def get_seh():
    """
    Makes a function which can be used to set the ROOT error handler with a
    python function and returns the existing error handler.
    """
    if ON_RTD:
        return lambda x: x
    
    ErrorHandlerFunc_t = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_bool,
        ctypes.c_char_p, ctypes.c_char_p)

    dll = None
    try:
        dll = ctypes.cdll.LoadLibrary(libcore())
    except OSError:
        log.warning("Unable to find libCore (tried %s)", libcore())

    SetErrorHandler = None
    try:
        if dll:
            SetErrorHandler = dll._Z15SetErrorHandlerPFvibPKcS0_E
    except AttributeError:
        pass
        
    if not SetErrorHandler:
        log.warning("Couldn't find SetErrorHandler, please submit a bug report "
                    "to rootpy.")
        return lambda x: None

    SetErrorHandler.restype = ErrorHandlerFunc_t
    SetErrorHandler.argtypes = ErrorHandlerFunc_t,

    def _SetErrorHandler(fn):
        """
        Set ROOT's warning/error handler. Returns the existing one.
        """
        eh = ErrorHandlerFunc_t(fn)
        # ``eh`` can get garbage collected unless kept alive, leading to a segfault.
        _keep_alive.append(eh)
        return SetErrorHandler(eh)
    return _SetErrorHandler

set_error_handler = get_seh()

def get_f_code_idx():
    """
    How many pointers into PyFrame is the ``f_code`` variable?
    """
    frame = sys._getframe()
    frame_ptr = id(frame)

    LARGE_ENOUGH = 20

    # Look through the frame object until we find the f_tstate variable, whose
    # value we know from above.
    ptrs = [ctypes.c_voidp.from_address(frame_ptr+i*svp)
            for i in range(LARGE_ENOUGH)]

    # Find its index into the structure
    ptrs = [p.value for p in ptrs]

    fcode_ptr = id(frame.f_code)
    try:
        threadstate_idx = ptrs.index(fcode_ptr)
    except ValueError:
        log.critical("BUG! please report this.")
        raise
    return threadstate_idx

F_CODE_IDX = get_f_code_idx()

def get_frame_pointers(frame=None):
    """
    Obtain writable pointers to ``frame.f_trace`` and ``frame.f_lineno``.

    Very dangerous. Unlikely to be portable between python implementations.

    This is hard in general because the ``PyFrameObject`` can have a variable size
    depending on the build configuration. We can get it reliably because we can
    determine the offset to ``f_tstate`` by searching for the value of that pointer.
    """

    if frame is None:
        frame = sys._getframe(2)
    frame = id(frame)

    # http://hg.python.org/cpython/file/3aa530c2db06/Include/frameobject.h#l28
    F_TRACE_OFFSET = 6
    Ppy_object = ctypes.POINTER(ctypes.py_object)
    trace = Ppy_object.from_address(frame+(F_CODE_IDX+F_TRACE_OFFSET)*svp)

    LASTI_OFFSET = F_TRACE_OFFSET + 4

    lasti_addr  = LASTI_OFFSET
    lineno_addr = LASTI_OFFSET + ctypes.sizeof(ctypes.c_int)

    f_lineno = ctypes.c_int.from_address(lineno_addr)
    f_lasti = ctypes.c_int.from_address(lasti_addr)

    return trace, f_lineno, f_lasti

def set_linetrace_on_frame(f, localtrace=None):
    """
    Non-portable function to modify linetracing.

    Remember to enable global tracing with :py:func:`sys.settrace`, otherwise no
    effect!
    """

    traceptr, _, _ = get_frame_pointers(f)
    if localtrace is not None:
        # Need to incref to avoid the frame causing a double-delete
        ctypes.pythonapi.Py_IncRef(localtrace)
        # Not sure if this is the best way to do this, but it works.
        addr = id(localtrace)
    else:
        addr = 0

    traceptr.contents = ctypes.py_object.from_address(addr)

def globaltrace(f, why, arg):
    pass

def re_execute_with_exception(frame, exception, traceback):
    """
    Dark magic. Causes ``frame`` to raise an exception at the current location
    with ``traceback`` appended to it.

    Note that since the line tracer is raising an exception, the interpreter
    disables the global trace, so it's not possible to restore the previous
    tracing conditions.
    """
    if sys.gettrace() == globaltrace:
        # If our trace handler is already installed, that means that this
        # function has been called twice before the line tracer had a chance to
        # run. That can happen if more than one exception was logged.
        return

    call_lineno = frame.f_lineno

    def intercept_next_line(f, why, *args):
        if f is not frame:
            return
        set_linetrace_on_frame(f)
        # Undo modifications to the callers code (ick ick ick)
        back_like_nothing_happened()
        # Raise exception in (almost) the perfect place (except for duplication)
        raise exception.__class__, exception, traceback

    set_linetrace_on_frame(frame, intercept_next_line)
    
    linestarts = list(dis.findlinestarts(frame.f_code))
    linestarts = [a for a, l in linestarts if l >= call_lineno]

    # Jump target
    dest = linestarts[0]

    oc = frame.f_code.co_code[frame.f_lasti]
    opcode_size = 2 if ord(oc) >= opcode.HAVE_ARGUMENT else 0
    # Opcode to overwrite
    where = frame.f_lasti + 1 + opcode_size

    # dis.disco(frame.f_code)
    pc = PyCodeObject.from_address(id(frame.f_code))
    back_like_nothing_happened = pc.co_code.contents.inject_jump(where, dest)
    # print "#"*100
    # dis.disco(frame.f_code)

    sys.settrace(globaltrace)

# The following code allows direct access to a python strings' bytes.
# Expect bad things to happen if you use this.
# It's necessary because you can't ordinarily modify strings in place, and we
# need it to modify the callers' code.
PyObject_HEAD = "PyObject_HEAD", c_byte * object.__basicsize__

class PyStringObject(Structure):
    _fields_ = [("_", ctypes.c_long),
                ("_", ctypes.c_int),
                ("_", ctypes.c_ubyte*1)]

PyObject_VAR_HEAD = ("PyObject_VAR_HEAD",
    c_byte * (str.__basicsize__ - ctypes.sizeof(PyStringObject)))

class PyStringObject(Structure):
    _fields_ = [PyObject_VAR_HEAD,
                ("ob_shash", ctypes.c_long),
                ("ob_sstate", ctypes.c_int),
                ("ob_sval", ctypes.c_ubyte*1)]

    def inject_jump(self, where, dest):
        """
        Monkeypatch bytecode at ``where`` to force it to jump to ``dest``.

        Returns function which puts things back how they were.
        """

        # We're about to do dangerous things to a functions code content.
        # We can't make a lock to prevent the interpreter from using those
        # bytes, so the best we can do is to set the check interval to be high
        # and just pray that this keeps other threads at bay.
        old_check_interval = sys.getcheckinterval()
        sys.setcheckinterval(2**20)

        pb = ctypes.pointer(self.ob_sval)
        orig_bytes = [pb[where+i][0] for i in xrange(where)]

        v = struct.pack("<BH", opcode.opmap["JUMP_ABSOLUTE"], dest)

        # Overwrite code to cause it to jump to the target
        for i in xrange(3):
            pb[where+i][0] = ord(v[i])

        def tidy_up():
            """
            Put the bytecode back how it was. Good as new.
            """
            sys.setcheckinterval(old_check_interval)
            for i in xrange(3):
                pb[where+i][0] = orig_bytes[i]

        return tidy_up

class PyCodeObject(Structure):
    _fields_ = [PyObject_HEAD,
                ("co_argcount", c_int),
                ("co_nlocals", c_int),
                ("co_stacksize", c_int),
                ("co_flags", c_int),
                ("co_code", POINTER(PyStringObject))]

def fix_ipython_startup(fn):
    """
    Attempt to fix IPython startup to not print (Bool_t)1
    """

    BADSTR = 'TPython::Exec( "" )'
    GOODSTR = 'TPython::Exec( "" );'
    consts = fn.im_func.func_code.co_consts
    if BADSTR not in consts:
        return
    idx = consts.index(BADSTR)
    orig_refcount = sys.getrefcount(consts)
    del consts

    PyTuple_SetItem = ctypes.pythonapi.PyTuple_SetItem
    PyTuple_SetItem.argtypes = ctypes.py_object, ctypes.c_size_t, ctypes.py_object

    consts = ctypes.py_object(fn.im_func.func_code.co_consts)

    for _ in range(orig_refcount-2):
        ctypes.pythonapi.Py_DecRef(consts)
    try:
        ctypes.pythonapi.Py_IncRef(GOODSTR)
        PyTuple_SetItem(consts, idx, GOODSTR)
    finally:
        for _ in range(orig_refcount-2):
            ctypes.pythonapi.Py_IncRef(consts)
