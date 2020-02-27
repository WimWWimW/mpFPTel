from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.filesystems import AbstractedFS
from pyftpdlib._compat import unicode
from _io import BytesIO
import inspect
from functools import partial
import posixpath
from mpError import ResourceNotFound
from pyftpdlib.servers import FTPServer


class IndirectFile(BytesIO):
    """
    File-like with intermediate buffer, so the content may be read/writen from/to the board
    by separate phases.
    Do not instantiate DirectFile but use open() to create an instance of one of its descendants.
    No provision for appending to files!
    """
    
    @classmethod
    def open(cls, fileName, mode, board):
        
        fcls = DownloadFile if mode.startswith("r") else UploadFile
        return fcls(fileName, mode, board)
    
    
    def __init__(self, fileName, mode, board):
        super().__init__()
        self.board  = board
        self.name   = fileName
        self.mode   = mode
    
    
class DownloadFile(IndirectFile):
    """
    To download a file from the board, first copy the content in the in-memory buffer
    and then return this file-like buffer.
    """ 
    
    def __init__(self, fileName, mode, board):
        super().__init__(fileName, mode, board)
        content = board.copyFileFromBoard(fileName)
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.write(content)
        self.seek(0)
    

                
class UploadFile(IndirectFile):
    """
    To upload a file to the board, copy the incoming file to the file-like in-memory buffer
    and then upload the entire file at once to the board.
    """
    
    def __init__(self, fileName, mode, board):
        print("UPLOAD", fileName)
        super().__init__(fileName, mode, board)
#         with open("r:/" + fileName, "rb") as f:
#             content = f.read()
#             self.write(content)
            
    def close(self):
        print("size of %s: %s" % (self.name, self.tell()))
        self.seek(0)
        self.board.copyFileToBoard(self.name, self)    
        super().close()

    def write(self, *args):
        print(args)
        return super().write(*args)
        
    def writelines(self, *args, **kwargs):
        print(args)
        return super().writelines(*args, **kwargs)
       
       
        
class AnonAuthorizer(DummyAuthorizer):
    """
    Authorizer that poses no limits to the anonymous user.
    """

    def add_user(self, username, password, homedir, perm='elr',
                 msg_login="Login successful.", msg_quit="Goodbye."):
        if self.has_user(username):
            raise ValueError('user %r already exists' % username)
        if not isinstance(homedir, unicode):
            homedir = homedir.decode('utf8')
        homedir = MPFS.realpath(homedir)
        self._check_permissions(username, perm)
        dic = {'pwd': str(password),
               'home': homedir,
               'perm': perm,
               'operms': {},
               'msg_login': str(msg_login),
               'msg_quit': str(msg_quit)
               }
        self.user_table[username] = dic


    def add_anonymous(self, homedir, **kwargs):
        self.add_user('anonymous', '', homedir, **kwargs)
 
     
    def override_perm(self, username, directory, perm, recursive=False):
        pass
 
    def validate_authentication(self, username, password, handler):
        return
 
    def get_home_dir(self, username):
        return "/"
 
    def has_perm(self, username, perm, path=None):
        return True
 
    def _check_permissions(self, username, perm):
        pass




class MPFS(AbstractedFS):
    """
    File system-like that in fact implements yet another transport protocol,
    from the host computer to the micropython board.
    """
    
    board = None  # to be set before first object instantiation
    debug = False # set to True to have all method calls printed to the console
    
    def __init__(self, root, cmd_channel):
        super().__init__("/", cmd_channel)
        if self.debug:
            self.__prepare()
    

    def __methodCall(self, fn, *args, **kwargs):
        """
        print 'calling methodName(arg, ...)' and then execute the method call itself.
        """
        params = ", ".join([str(a) for a in args] + ["%s=%s" % a for a in kwargs.items()])        
        print("calling %s(%s)" %(fn.__qualname__, params))
        return fn(*args, **kwargs)
    
    
    def __prepare(self):
        """ 
        Wrap all our public methods (inherited included) in __methodCall
        so usage be logged to the console
        """  
        names = [ n for n in sorted(dir(self), key=str.lower) if not n.startswith('_')]
        meths = [getattr(self, n) for n in names if inspect.ismethod(getattr(self, n))]
        for method in meths:
            fn = partial(self.__methodCall, method)
            setattr(self, method.__name__, fn)

    # ----------------------------------------------
                
    def ftp2fs(self, ftppath):
        """Translate a "virtual" ftp pathname (typically the raw string
        coming from client) into equivalent absolute "real" filesystem
        pathname.

        Example (having "/home/user" as root directory):
        >>> ftp2fs("foo")
        '/home/user/foo'

        Note: directory separators are system dependent.
        """
        assert isinstance(ftppath, unicode), ftppath
        if self.normpath(self.root) == '/':
            return self.normpath(self.ftpnorm(ftppath))
        else:
            p = self.ftpnorm(ftppath)[1:]
            return self.normpath(posixpath.join(self.root, p))
        
        
        
    def open(self, fileName, mode):
        """
        Open a file returning its handler.
        Since directly opening files on the board is not possible, an IndirectFile instance is returned
        that buffers / prereads the file content to / from the board.
        Quite likely, mode = "a" will create issues here.
        """
        assert isinstance(fileName, unicode), fileName
        return IndirectFile.open(fileName, mode, self.board)
    

    def chdir(self, path):
        """Change the current directory. If this method is overridden
        it is vital that `cwd` attribute gets set.
        """
        # note: process cwd will be reset by the caller
        path = self.folderName(path)
        self.board.chdir(path)
        self.cwd = self.fs2ftp(path)
        
        
    def mkdir(self, path):
        """Create the specified directory."""
        assert isinstance(path, unicode), path
        self.board.mkdir(path)


    def listdir(self, path):
        """List the content of a directory."""
        assert isinstance(path, unicode), path
        print("listdir", path)
        return self.board.ls(path, long_format=False)


    def rmdir(self, path):
        """Remove the specified directory."""
        assert isinstance(path, unicode), path
        self.board.rmdir(self.folderName(path))


    def remove(self, path):
        """Remove the specified file."""
        assert isinstance(path, unicode), path
        self.board.rm(path)


    def rename(self, src, dst):
        """Rename the specified src file to the dst filename."""
        assert isinstance(src, unicode), src
        assert isinstance(dst, unicode), dst
        self.board.rename(src, dst)

    def stat(self, path):
        """Perform a stat() system call on the given path."""
        return self.board.fileInfo(self.realpath(path))

    # --- Wrapper methods around os.path.* calls
    def islink(self, path):
        """Return True if path is a symbolic link."""
        return False
    
    def isdir(self, path):
        """Return True if path is a directory."""
        assert isinstance(path, unicode), path
        print("isdir", path)
        return self.board.isDir(path)


    def folderName(self, path):
        path = self.realpath(path)
        if path.endswith('/'):
            return path[:-1]
        return path
    
    @classmethod
    def normpath(cls, path):
        assert isinstance(path, unicode), path
        return posixpath.normpath(path.replace('\\', '/'))
    
    @classmethod
    def realpath(cls, path):
        """Return the canonical version of path eliminating any
        symbolic links encountered in the path (if they are
        supported by the operating system).
        """
        if ':' in path:
            path = path.split(':')[-1]
        return cls.normpath(path)


    def validpath(self, path):
        return True


    def chmod(self, path, mode):
        print("calling chmod(%s)"  % (", ".join([str(a) for a in [path, mode]])))
        return # super().chmod(path, mode)
    
    
    def getmtime(self, path):
        print("calling getmtime(%s)"  % (", ".join([str(a) for a in [path]])))
        return self.board.fileInfo(path).st_mtime
    
    
    def getsize(self, path):
        print("calling getsize(%s)"  % (", ".join([str(a) for a in [path]])))
        return self.board.fileInfo(path).st_size
    
    
    def isfile(self, path):
        print("calling isfile(%s)"  % (", ".join([str(a) for a in [path]])))
        return not self.isdir(path)
    
    
    def lexists(self, path):
        print("calling lexists(%s)"  % (", ".join([str(a) for a in [path]])))
        try:
            self.board.fileInfo(path, getFresh = True)
            return True
        except ResourceNotFound:
            return False
    
    
    def listdirinfo(self, path):
        return self.listdir(path)
    
    
    def lstat(self, path):
        return self.stat(path)
    
    
    def readlink(self, path):
        print("calling readlink(%s)"  % (", ".join([str(a) for a in [path]])))
        raise NotImplementedError("readlink")
    
    
    def utime(self, path, timeval):
        """Perform a utime() call on the given path"""
        pass
    
    
class MPFTPHandler(FTPHandler):
    
    abstracted_fs   = MPFS
        

class MPFTPServer(FTPServer):
    

    def allowConnection(self, ip):
        return ip == "127.0.0.2"
    
    
    def handle_accepted(self, sock, addr):
        """Called when remote client initiates a connection."""
        handler = None
        ip      = addr[0]
        if self.allowConnection(ip):
            super().handle_accepted(sock, addr)
        else:
            handler = self.handler(sock, self, ioloop=self.ioloop)
            handler.respond("refused")
            handler.close()



if __name__ == '__main__':
    pass
#     pyftpdlib.log.config_logging(level=logging.DEBUG)
#     
#        
#     authorizer          = AnonAuthorizer()     
#     authorizer.add_anonymous("/", perm="elradfmw")
#     
#     handler             = FTPHandler
#     handler.authorizer  = authorizer
# 
#     board               = Microterm()
#     MPFS.board          = board
#     telnet.terminal     = board
# #     _thread.start_new_thread(telnet.start, ())
#         
#     server = FTPServer(("127.0.0.1", 21), handler)
#     server.serve_forever()
#     
