
from collections import namedtuple
import posixpath


FileStat = namedtuple("FileStat", "mode ino dev nlink uid gid size atime mtime ctime")    

class FileDescriptor(object):
    def __init__(self, fileName, stats, path, parent = None):
        self.name = fileName
        self.path = path
        self._size= stats.size
        self.time = stats.mtime
        self.isDir= (stats.mode & 16384) > 0
        self.parent     = parent
        self.children   = [] if self.isDir else ()
        if self.isDir:
            self.type = "<folder>"
        else:
            reg = {"py":"python source"}
            ext = posixpath.splitext(self.name)[1][1:]
            self.type = reg.get(ext, "%s-file" % ext)
                    

    def __str__(self):
        return "%-20s:%6d bytes [%s]" % (("* " if self.isDir else "") + self.name, self.size(), self.path)
    

    def addChildren(self, files):
        for f in files:
            f.parent = self
            self.children.append(f)

    def hasChildren(self):
        return len(self.children) > 0

    def isParent(self, path):
        if not path.endswith('/'):
            path += '/'
        return self.path == path
    
    def size(self):
        if self.isDir:
            return sum([c.size() for c in self.children])
        else:
            return self._size
    
    def fullName(self):
        return posixpath.join(self.path, self.name)
    
