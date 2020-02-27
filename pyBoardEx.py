import serial
import stat
import os
from io import IOBase
from time import sleep
from ampy import pyboard
from ampy.pyboard import Pyboard, PyboardError

import operations
from fileDescriptor import FileDescriptor, FileStat
from mpError import PyboardErrorFactory, PyboardOSError

pyboard.PyboardError = PyboardErrorFactory


BUFFER_SIZE = 1024  # Amount of data to read or write to the serial port at a time.
                    # This is kept small because small chips and USB to serial
                    # bridges usually have very small buffers.


def listComPorts(maxPort = 32, minPort = 1):
    """
    List all com-ports on the system; occupied ones are preceeded by an asterisk (*)
    """
    result = []
    for p in range(minPort, maxPort + 1):
        try:
            try:
                port = "COM%d" % p
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except serial.SerialException as e:
                _, _, err = str(e).partition("'%s': " % port)
                raise eval(err) from e 
        except PermissionError:
            result.append("*" + port)
        except:
            pass
    return result
    
    

class PyBoardEx(Pyboard):

    def __init__(self, speed = 115200, port = -1, silent = False):
        ports = listComPorts(port, port) if port > 0 else listComPorts() 
       
        
        for port in [p for p in ports if not p.startswith('*')]:     
            if not silent: print(port, "   ", speed, "baud", end=" ... ")
            try:
                super().__init__(port, speed)
                if not silent: print("found")
                if not silent: 
                    for itm in self.getID().items():
                        print("%-9s: %s"% itm) 
                    print("-"*50, '\n')
                self.stat = {}
                return 
            except Exception as e:
                print(e)
                
        if len(ports) == 0:
            info = "no serial ports found at all"
        elif any([p.startswith('*') for p in ports]):
            info = "serial ports that were found (i.e. %s) are in use by another process" % \
                    ", ".join([p[1:] for p in ports if p.startswith('*')])
        raise RuntimeError("no python board found: %s" % info)
    
        
    def getID(self):
        return dict(self.remoteExecute("getID", returnResult = True))
     
        

    def remoteCommand(self, command, returnResult = True):
        code = command if not returnResult else "print(%s)" % command
        return(self._remoteExec(code, "", returnResult))
    
    
    def remoteExecute(self, functionName, *args, returnResult = True):
        code = operations.remoteCall(functionName, *args, returnResult = returnResult)
        try:
            return self._remoteExec(code, returnResult)
        except PyboardOSError as e:
            e.transmogrify(functionName, (list(args) + [None])[0])
            raise         
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
            error = PyboardOSError("Exception", b'', data_err)
            raise RuntimeError(error.translate())
            
        # line endings may get changed in size
        result      = self.read_until(size, terminator)[:-len(terminator)]

        if text:
            result  = result.decode("utf-8").replace("\r\n", "\n")
        return result
      
      
    def fileInfo(self, filePath, getFresh = False):
        if getFresh or not filePath in self.stat:
            result = os.stat_result(self.remoteExecute("getFileInfo", filePath, returnResult = True))
            self.stat[filePath] = result
            
        return self.stat[filePath]
    
    
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
        self.stat = dict([(r[1] + r[0], os.stat_result(r[2])) for r in result])
        return result if long_format else [name[0] for name in result]
    
    
    def osCall(self, methodName, *args):
        command = operations.remoteCall(methodName, *args)
        try:
            return self._remoteExec(command)
        except PyboardOSError as ex:
            ex.transmogrify(methodName, *args) 
            raise
    
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
        
        

        
        
class Microterm(PyBoardEx):

    def __init__(self, speed = 115200, port = -1, silent = False):
        super().__init__(speed, port, silent)
    

    def sendLineCommand(self, command):
        command = (command + "\r\n").encode("utf-8")
        self.serial.write(command)
        sleep(0.01)
        return command
    
    def readUntilPrompt(self, prompt=b">>>", command = None):
        if command is not None:
            self.read_until(1, command, 2).decode("utf-8").replace("\r\n", "\n") #, self.copyOutput)
        out = self.read_until(1, prompt, 2).decode("utf-8").replace("\r\n", "\n") #, self.copyOutput)
        return out + "" if out.endswith('>') else '\n' 


    def cli(self):
        # interactive prompt:

        def readUntilPrompt(prompt=b">>>", command = None):
            if command is not None:
                self.read_until(1, command, 2).decode("utf-8").replace("\r\n", "\n") #, self.copyOutput)
            out = self.read_until(1, prompt, 2).decode("utf-8").replace("\r\n", "\n") #, self.copyOutput)
            print(out, end="" if out.endswith('>') else '\n') 

        print( 'Enter your commands below.\r\nInsert "exit" to leave the application.')

        self.sendLineCommand('\r\n')
        readUntilPrompt()

        while True :
            cmd  = input("")
            if cmd.lower() == 'exit':
                break;
            else:
                try:
                    cmd = self.sendLineCommand(cmd)
                    readUntilPrompt(command = cmd)
                except PyboardError as e:
                    print(e)


    def stop(self):
        super().close()
        print("session closed.")


        
    def getFiles(self, path = "/", recurse = False):
        result = self.ls(path, False, recursive = recurse)
        files  = [FileDescriptor(file[0], FileStat(*file[2]), file[1]) for file in result]
        if recurse:
            rm = []
            for f in files:
                if f.isDir:
                    cc = [c for c in files if c.isParent(f.path + f.name)]
                    f.addChildren(cc)
                    rm += f.children
                    
            for r in rm:
                files.remove(r)
        return files

        
    
    def copyFileFromBoard(self, fileName, destinationPath = None):
        asText  = (os.path.splitext(fileName)[1] in [".py", ".txt", ".json"]) and (destinationPath is None)
        content = self.get(fileName, asText)

        if destinationPath is None:
            return content
        
        destinationFile = os.path.join(destinationPath, os.path.split(fileName)[1])
        with open(destinationFile, "w" if asText else "wb") as f:
            f.write(content)
        stat = os.stat(destinationFile)
        return FileStat(*stat).size
    
    
    def mirrorFromBoard(self, destinationPath, files = None):
        if files is None:
            files = self.getFiles(recurse=True)
            
        for f in files:
            print(f, end=" copying ...")
            fn = os.path.join(f.path, f.name)
            if not f.isDir:
                print(self.copyFileFromBoard(fn, destinationPath), "bytes copied")
            else:
                print("directory")
                fn = os.path.join(destinationPath, fn)
                os.makedirs(fn, exist_ok = True)
                self.mirrorFromBoard(fn, f.children)
        
           
    def copyFileToBoard(self, fileName, data = None):
        if data is None:
            with open(fileName, "rb") as f:
                data = f.read()
        elif isinstance(data, IOBase):
            data = data.read()
        self.put(fileName, data)


    def chdir(self, path):
        self.osCall("chDir", path)
        

    def mkdir(self, directory, exists_okay=False):
        """Create the specified directory.  Note this cannot create a recursive
        hierarchy of directories, instead each one should be created separately.
        """
        self.osCall("mkDir", directory)        


    def rm(self, filename):
        self.osCall("deleteFile", filename)
        return


    def rmdir(self, directory, force=False):
        """[Forcefully] remove the specified directory and all its children."""
        self.osCall("deleteFolder", directory, force)


    def rename(self, oldName, newName):
        self.osCall("rename", oldName, newName)
        
if __name__ == '__main__':
    print(PyBoardEx())