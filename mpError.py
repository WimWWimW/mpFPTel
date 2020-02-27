import errno
from errno import ENOENT, EACCES, EISDIR, EEXIST
import os
import re
import inspect
import sys


class PyboardErrorEx(Exception):

    def __init__(self, message, result = None, traceBack = None):
        self.message    = message
        self.result     = None if result    is None else result.decode("utf-8")
        self.traceBack  = None if traceBack is None else traceBack.decode("utf-8")
        super().__init__(message)


    def __str__(self):
        return self.message

    
    @classmethod
    def error_text(cls, errnumber):
        return '%s: %s' % (errno.errorcode[errnumber], os.strerror(errnumber))



class PyboardOSError(PyboardErrorEx):

    errNo = -1
    
    def __init__(self, message, result = None, traceBack = None):
        super().__init__(message, result, traceBack)
        m = re.search("\[Errno ([0-9]+)\]", self.traceBack)
        if m is None:
            self.errorCode = 0
            self.errorText = "(unknown error)"
        else:
            self.errorCode = int(m.group(0)[7:-1])
            self.errorText = self.error_text(self.errorCode)
            
    
    def translate(self, source = None):
        if self.errorCode == 0:
            return self.message
        else:
            return "%s\n%s\%s\n\n%s" % (self.errorText, self.message, self.traceBack,
                                        "" if source is None else source)
    

    def transmogrify(self, methodName, *args):
        print("TRANS")
        params = ", ".join([str(a) if not isinstance(a, str) else "'%s'" % a for a in args])        
        self.message = "%s: %s(%s)" % (self.errorText, methodName, params)
        
        
        
            
class ResourceNotFound (PyboardOSError): errNo = ENOENT
class DirectoryNotEmpty(PyboardOSError): errNo = EACCES
class DirectoryExists  (PyboardOSError): errNo = EEXIST
class FileExpected     (PyboardOSError): errNo = EISDIR      
                   
errorFilter     = lambda c: inspect.isclass(c) and issubclass(c, PyboardOSError)
errorList       = inspect.getmembers(sys.modules[__name__], errorFilter)
errorDelegates  = dict([(e[1].errNo, e[1]) for e in errorList])




class PyboardErrorFactory(PyboardErrorEx):

    def __new__(cls, message, result = None, traceBack = None):
        tb = "" if traceBack is None else traceBack.decode("utf-8")
        m = re.search("\[Errno ([0-9]+)\]", tb)
        if m is not None:
            errorCode = int(m.group(0)[7:-1])
            cls = errorDelegates.get(errorCode, PyboardErrorEx) 
            obj = cls.__new__(cls, message, result, traceBack)
            obj.__init__(message, result, traceBack)
            return obj
        
        return super().__new__(cls, message, result, traceBack)
            
            



if __name__ == '__main__':
    import pyBoardEx
    from pyBoardEx import Microterm
    from ampy import pyboard
        
    pyboard.PyboardError = PyboardErrorFactory
    pyBoardEx.PyboardErrorEx = PyboardOSError
    
    t = Microterm()
    
    t.chdir("nonX")
    
