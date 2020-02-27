from inspect import getsource, signature, isfunction

def getFile(fileName, terminator, chunkSize):
    import sys
    with open(fileName, 'rb') as f:
        size = f.seek(0, 2)
        sys.stdout.write(size.to_bytes(4, "big"))
        f.seek(0, 0)
        while True:
            result = f.read(chunkSize)
            if result == b'':
                break
            sys.stdout.write(result)
    sys.stdout.write(terminator)


def getFileInfo(fileName):
    import os
    return os.stat(fileName)

    
def scanDir(path, recurse):
    import os
    if not path.endswith('/'):
        path += '/'
    result  = []
    for file in sorted(os.listdir(path + '.')):
        stats = os.stat(path + file)
        result.append((file, path, stats))
        if recurse and ((stats[0] & 16384) > 0):
            result.extend(scanDir(path + file, recurse))
    return result


def chDir(name):
    import os
    os.chdir(name)


def mkDir(name):
    import os
    os.mkdir(name)


def rename(oldName, newName):
    import os
    os.rename(oldName, newName)
    

def deleteFile(fileName):
    import os
    os.remove(fileName)


def deleteFolder(directory, deleteEvenIfNotEmpty):
    import os
    def rmdir(path):
        if deleteEvenIfNotEmpty:
            for f in os.listdir(path):
                f = path + '/' + f
                try:
                    stats = os.stat(f)
                    if ((stats[0] & 16384) > 0):
                        rmdir(f)
                    else:
                        os.remove(f)
                except OSError:
                    pass
            for f in os.listdir(path):
                rmdir(f)
        os.rmdir(path)

    rmdir(directory)


def getID():
    import os
    n = os.uname()  # @UndefinedVariable
    return [(a, getattr(n, a)) for a in dir(n) if not a.startswith("_")]

    
snapshot = globals().copy()    
code    = {}
params  = {}    
for nm, fn in snapshot.items():
    if isfunction(fn):
        code[nm]    = getsource(fn)
        params[nm]  = signature(fn)
        
        
def remoteCall(function, *args, returnResult = False):
    source      = code[function]
    expectedArgCount = len(params[function].parameters)
    if (len(args) != expectedArgCount):
        raise TypeError("function operations.%s%s takes %d parameters" % (function, params[function], expectedArgCount)) 
    args        = ", ".join([('"%s"' % arg) if isinstance(arg, str) else str(arg) for arg in args])
    if returnResult:
        return  "%s\n\nprint(%s(%s))" % (source, function, args)
    else:
        return  "%s\n\n%s(%s)" % (source, function, args)

    