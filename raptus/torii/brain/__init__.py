import os
import sys
import re
import types
import logging
import ConfigParser
import cPickle
from StringIO import StringIO
from codeop import compile_command
from zodbcode.function import PersistentFunction
from raptus.torii import carrier

SECTION = 'raptus.torii.brain'
CLEAN = lambda varStr: re.sub('\W|^(?=\d)','_', varStr)


class FakeModule(object):
    """ This class bogus a module and is used to
        persist a function with zodbcode
    """
    
    __name__ = 'Torii-Console'
    _p_changed = None
    _p_activate = lambda d:None

    @property
    def __dict__(self):
        return dict()


_params = None
_storage = None
_path = None

def initialize(params=None):
    # called by raptus.torii.datatypes.Configuration
    from raptus.torii import brain as self 
    if params:
        self._params = params
        self._path = _params.get('storage', '')
        self._storage = ConfigParser.SafeConfigParser()
        self._storage.read(_path)
        if not self._storage.has_section(SECTION):
            self._storage.add_section(SECTION)
            write()

def write():
    try:
        filestorage = open(_path, 'wb')
        _storage.write(filestorage)
        filestorage.close()
    except IOError:
        logging.error("can't write a file at: %s"  % _path)

def pre_keep():
    for part in _storage.options(SECTION):
        st = StringIO(_storage.get(SECTION, part))
        func = cPickle.load(st)
        # restore the globals from console
        getattr(func._pf_func, 'func_globals', {}).update(globals())
        rvalue = func
        if getattr(func, 'call', True):
            try:
                rvalue = func()
            except:
                pass
        # remove original function
        co = compile_command("if '%(func)s' in vars(): del %(func)s" % dict(func=part),
                             '<torii.brain - remove original function>','exec')
        # conversation are a global from the console
        conversation.im_self.interpreter.runcode(co)
        conversation.im_self.locals.update({part:rvalue})
        # fix display of available variables
        if conversation.im_self.locals.has_key('__builtins__'):
            del conversation.im_self.locals['__builtins__']
    return keep

def keep(func, name=None, call=True):
    """
    Put the function to the storage.
    Optional argument:
    name - name to representation the function.
    call - if True the function will be automatically called. 
           default is True
    """
    if not name:
        name = func.func_name
    name = CLEAN(name)
    per = PersistentFunction(func, FakeModule())
    setattr(per, 'call', call)
    st = StringIO()
    cPickle.dump(per, st)
    _storage.set(SECTION, name, st.getvalue())
    write()
    #call to reload all function
    pre_keep()
    # conversation are a global from the console
    conversation(carrier.PrintText('function successfully saved %s:%s' % (name, repr(per))))

def kill(func):
    __doc__ = """
    Remove the function or attribute from the storage.
    The argument can be directly a function. If the
    function are not found define it as string.
    """
    # conversation are a global from the console
    locals = conversation.im_self.locals
    vals = []
    if not isinstance(func, str):
        vals = [k for k, v in locals.iteritems() if func == v]
        if len(vals) == 1:
            func = vals.pop()
    if isinstance(func, str) and _storage.has_option(SECTION, func):
        _storage.remove_option(SECTION,func)
        write()
        locals.pop(func)
        conversation(carrier.PrintText('function %s removed.' % func))
    else:
        conversation(carrier.PrintText("Can't find the function/attribute. Try to give the name as string."))

#read by raptus.torii.datatypes.Configuration
properties = dict(keep=pre_keep)
utilities = dict(kill=kill)

