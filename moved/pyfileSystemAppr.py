import textwrap
import os
from time import sleep
from ampy import pyboard
from ampy.pyboard import Pyboard, PyboardError
import operations
import errno
import re
import serial
import stat
from errno import ENOENT, EACCES, EISDIR, EEXIST
import fs.errors
from fs.base import FS
from fs.path import basename
from fs.info import Info
from fs.subfs import SubFS
from fs.osfs import OSFS

ERROR_DELEGATES = {ENOENT: fs.errors.ResourceNotFound,
                   EACCES: fs.errors.DirectoryNotEmpty,
                   EEXIST: fs.errors.DirectoryExists,
                   EISDIR: fs.errors.FileExpected                 
                   }

class PyboardErrorEx(Exception):
    

    
    def __init__(self, message, result = None, traceBack = None):
        self.message    = message
        self.result     = None if result    is None else result.decode("utf-8")
        self.traceBack  = None if traceBack is None else traceBack.decode("utf-8")

        m = re.search("\[Errno ([0-9]+)\]", self.traceBack)
        if m is None:
            self.errorCode = 0
            self.errorText = self.message
        else:
            self.errorCode = int(m.group(0)[7:-1])
            self.errorText = self.error_text(self.errorCode)
            
        super().__init__(message)

    def __str__(self):
        return "(%s) %s %s" % (self.errorCode, self.errorText, self.message)
    
    @classmethod
    def error_text(cls, errnumber):
        return '%s: %s' % (errno.errorcode[errnumber], os.strerror(errnumber))


    def translate(self, source = None):
        if self.errorCode == 0:
            return self.message
        else:
            return "%s\n%s\%s\n\n%s" % (self.errorText, self.message, self.traceBack,
                                        "" if source is None else source)
    

    def transmogrify(self, *args, delegates = ERROR_DELEGATES):
        try:
            return delegates[self.errorCode](*args)
        except KeyError:
            return self

pyboard.PyboardError = PyboardErrorEx


BUFFER_SIZE = 1024  # Amount of data to read or write to the serial port at a time.
# This is kept small because small chips and USB to serial
# bridges usually have very small buffers.


def listComPorts(maxPort = 32):
    result = []
    for p in range(1, maxPort + 1):
        try:
            port = "COM%d" % p
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

    
    

class PyboardEx(Pyboard):

    @classmethod
    def start(cls, speed = 115200):
        # automatic port selection:
        for port in listComPorts():     
            print(port, "   ", speed, "baud", end=" ... ")
            try:
                instance = cls(port, speed)
                print("found")
                for itm in instance.getID().items():
                    print("%-9s: %s"% itm) 
                print("-"*50, '\n')
                return instance
            except Exception as e:
                print(e)
                print("not found")
                
        raise RuntimeError("no python board found")
        
        
    def stop(self):
        super().close()
        print("session closed.")

        
        
    def getID(self):
        return dict(self.remoteExecute("getID", returnResult = True))
     
        

    def remoteCommand(self, command, returnResult = True):
        code = command if not returnResult else "print(%s)" % command
        return(self._remoteExec(code, "", returnResult))
    
    
    def remoteExecute(self, functionName, *args, returnResult = True):
        code = operations.remoteCall(functionName, *args, returnResult = returnResult)
        try:
            return self._remoteExec(code, returnResult)
        except PyboardErrorEx as e:
            raise e.transmogrify((list(args) + [None])[0])         
        except Exception as e:
            return e
      

    def _remoteExec(self, code, returnResult = True):
        self.enter_raw_repl()
        try:
            if returnResult:
                out = self.exec_(code).decode("utf-8")
                return "" if out.strip() == "" else eval(out)                                        
            else:
                self.exec_raw_no_follow(code)
                sleep(0.1)
                return
        finally:
            self.exit_raw_repl()
        

            
    def get(self, filename, text = False):
        terminator  = b'*d*o*n*e*'
        self.remoteExecute("getFile", filename, terminator, BUFFER_SIZE)
        size        = int.from_bytes(self.serial.read(4), "big")
        
        if size == 0x4547261: # b'Trac...'
            data_err = self.read_until(1, b'\x04')
            if not data_err.endswith(b'\x04'):
                raise PyboardError('timeout waiting for second EOF reception')
            data_err = size.to_bytes(4, "big") + data_err[:-1]
            error = PyboardErrorEx("Exception", b'', data_err)
            raise RuntimeError(error.translate())
            
        # line endings may get changed in size
        result      = self.read_until(size, terminator)[:-len(terminator)]

        if text:
            result  = result.decode("utf-8").replace("\r\n", "\n")
        return result
      
      
#     def getFileInfo(self, fileList):
#         """        
#         st_mode: protection bits.
#         st_size: size of file in bytes.
#         st_atime: time of most recent access.
#         st_mtime: time of most recent content modification.
#         st_ctime: time of most recent metadata change.
#         """
#         command = """
#         result = [(fn, uos.stat(fn)) for fn in %s]
#         print(result)
#         """ % fileList
# 
#         self.enter_raw_repl()
#         try:
#             out = self.exec_(textwrap.dedent(command))
#         except PyboardError as ex:
#             # Check if this is an OSError #2, i.e. file doesn't exist and
#             # rethrow it as something more descriptive.
#             if ex.args[2].decode("utf-8").find("OSError: [Errno 2] ENOENT") != -1:
#                 raise # RuntimeError("No such file: {0}".format(fileName))
#             else:
#                 raise ex
#         self.exit_raw_repl()
# 
#         result = ast.literal_eval(out.decode("utf-8"))
#         return [FileDescriptor(os.path.split(t[0])[1], FileStat(*t[1]), os.path.split(t[0])[0]) for t in result]        
            
            
    def fileInfo(self, filePath):
        return os.stat_result(self.remoteExecute("getFileInfo", filePath, returnResult = True))
    
    
    def isDir(self, filePath):
        return  stat.S_ISDIR(self.fileInfo(filePath).st_mode)
    
     
    def ls(self, directory="/", long_format=True, recursive=False):
        """List the contents of the specified directory (or root if none is
        specified).  Returns a list of strings with the names of files in the
        specified directory.  If long_format is True then a list of 2-tuples
        with the name and size (in bytes) of the item is returned.  Note that
        it appears the size of directories is not supported by MicroPython and
        will always return 0 (i.e. no recursive size computation).
        """

        result = self.remoteExecute("scanDir", directory, recursive, returnResult = True)
        return result 
    
    

    def mkdir(self, directory, exists_okay=False):
        """Create the specified directory.  Note this cannot create a recursive
        hierarchy of directories, instead each one should be created separately.
        """
        command = operations.remoteCall("mkDir", directory)
        try:
            out = self._remoteExec(command)
        except PyboardErrorEx as ex:
            # Check if this is an OSError #17, i.e. directory already exists.
            if ex.errorCode == EEXIST and exists_okay:
                return
            raise ex.transmogrify(directory)


    def put(self, filename, data):
        """Create or update the specified file with the provided data.
        """
        # Open the file for writing on the board and write chunks of data.
        self.enter_raw_repl()
        self.exec_("f = open('{0}', 'wb')".format(filename))
        size = len(data)
        # Loop through and write a buffer size chunk of data at a time.
        for i in range(0, size, BUFFER_SIZE):
            chunk_size = min(BUFFER_SIZE, size - i)
            chunk = repr(data[i : i + chunk_size])
            # Make sure to send explicit byte strings (handles python 2 compatibility).
            if not chunk.startswith("b"):
                chunk = "b" + chunk
            self.exec_("f.write({0})".format(chunk))
        self.exec_("f.close()")
        self.exit_raw_repl()


    def rm(self, filename):
        """Remove the specified file or directory."""
        command = """
            try:
                import os
            except ImportError:
                import uos as os
            os.remove('{0}')
        """.format(
            filename
        )
        self.enter_raw_repl()
        try:
            out = self.exec_(textwrap.dedent(command))
        except PyboardErrorEx as ex:
            if ex.errorCode == ENOENT:
                raise fs.errors.ResourceNotFound(filename)
            elif ex.errorCode == EACCES:
                raise fs.errors.DirectoryNotEmpty(filename)
            elif ex.errorCode == EISDIR:
                raise fs.errors.FileExpected(filename)
            else:
                raise ex
        self.exit_raw_repl()


    def rmdir(self, directory, force=False):
        """Forcefully remove the specified directory and all its children."""
        # Build a script to walk an entire directory structure and delete every
        # file and subfolder.  This is tricky because MicroPython has no os.walk
        # or similar function to walk folders, so this code does it manually
        # with recursion and changing directories.  For each directory it lists
        # the files and deletes everything it can, i.e. all the files.  Then
        # it lists the files again and assumes they are directories (since they
        # couldn't be deleted in the first pass) and recursively clears those
        # subdirectories.  Finally when finished clearing all the children the
        # parent directory is deleted.
        command = """
            try:
                import os
            except ImportError:
                import uos as os
            def rmdir(directory):
                os.chdir(directory)
                for f in os.listdir():
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                for f in os.listdir():
                    rmdir(f)
                os.chdir('..')
                os.rmdir(directory)
            rmdir('{0}')
        """.format(
            directory
        )
        command = operations.remoteCall("deleteFolder", directory, force)
        try:
            self._remoteExec(command)
        except PyboardErrorEx as ex:
            raise ex.transmogrify(directory)
        



    def run(self, filename, wait_output=True):
        """Run the provided script and return its output.  If wait_output is True
        (default) then wait for the script to finish and then print its output,
        otherwise just run the script and don't wait for any output.
        """
        self.enter_raw_repl()
        out = None
        if wait_output:
            # Run the file and wait for output to return.
            out = self.execfile(filename)
        else:
            # Read the file and run it using lower level pyboard functions that
            # won't wait for it to finish or return output.
            with open(filename, "rb") as infile:
                self.exec_raw_no_follow(infile.read())
        self.exit_raw_repl()
        return out
        
        
        
class FSMicroPython(FS):
    

    def __init__(self):
        self._board = PyboardEx.start()
        super().__init__()
        
        
    def close(self):
        super().close()
        self._board.close()
        
    
    def getinfo(self, path, namespaces=None):
        _stat = self._board.fileInfo(path)
        _path = self.validatepath(path)
        info  = {}
        info["basic"]   = {"name": basename(_path), "is_dir": stat.S_ISDIR(_stat.st_mode)}
        info["details"] = OSFS._make_details_from_stat(_stat)
        info["stat"]    = {k: getattr(_stat, k) for k in dir(_stat) if k.startswith("st_")}
        return Info(info)
    
    
    
    def listdir(self, path):
        """
        Arguments:    path (str): A path to a directory on the filesystem
        Returns:      list: list of names, relative to ``path``.
        Raises:       fs.errors.DirectoryExpected: If ``path`` is not a directory.
                      fs.errors.ResourceNotFound: If ``path`` does not exist.
        """
        try:
            if not self._board.isDir(path):
                raise fs.errors.DirectoryExpected(path)
            raw = self._board.ls(directory = path)
            return [r[0] for r in raw]
        
        except PyboardErrorEx as e:
            if e.errorCode == ENOENT:
                raise fs.errors.ResourceNotFound(path)
            raise
                
    
        
    def makedir(self, path, permissions=None, recreate=False):
        self._board.mkdir(path, recreate)
        return SubFS(self, path)
        

    def openbin(self, path, mode="r", buffering=-1, **options):
        pass
    
    def remove(self, path):
        self._board.rm(path)

    def removedir(self, path, force=False):
        if not force:
            content = self._board.ls(path)
            if len(content) != 0:
                raise fs.errors.DirectoryNotEmpty(path)        
        
        self._board.rmdir(path, force)
    
    def setinfo(self, path, info):
        pass

        
        
if __name__ == '__main__':
                
    
    fsESP32 = FSMicroPython()
    try:
        for f in fsESP32.listdir("/"):
            print(f)

#         for i in range(1, 30):
#             try:
#                 print(i, PyboardErrorEx.error_text(i))
#             except: pass
#         fsESP32.makedir("/TEST", recreate=True)
#         fsESP32.makedir("/TEST/a", recreate=True)
#         fsESP32.removedir("/TEST", force=True)

#         fsESP32.tree()
    finally:
        fsESP32._board.stop()
        
