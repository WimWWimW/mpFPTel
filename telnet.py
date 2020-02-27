import asyncio
from telnetlib3.server import TelnetServer
import logging
from asyncio.futures import CancelledError

terminal  = None
whiteList = ['127.0.0.1']

class MPTelnetServer(TelnetServer):
    
    @classmethod
    @asyncio.coroutine
    def create_server(cls, host=None, port=23, **kwds):

        protocol_factory = cls
        loop = kwds.get('loop', asyncio.get_event_loop())
    
        return (yield from loop.create_server(lambda: protocol_factory(**kwds), host, port))
    
                

        
@asyncio.coroutine
def getRemoteInput(reader, writer):
    buff = ''
    while True:
        c = yield from reader.read(1)
        print(c, end='', flush=True)

        if c == "\r":
            # EOF
            return buff
        buff += c
            
            
@asyncio.coroutine
def shell(reader, writer):
    peer    = writer.transport._extra["peername"][0]
    if peer in whiteList: 
        for itm in terminal.getID().items():
            writer.write("%-9s: %s\n" % itm) 
        writer.write("-"*50, '\n' * 2)
    else:
        writer.write("connection refused")
    
    while True:
        command = yield from getRemoteInput(reader, writer)
        
        if peer in whiteList: 
            print(command, end='', flush=True)
    
            try:
                cmd = terminal.sendLineCommand(command)
                response = terminal.readUntilPrompt(command = cmd)
                writer.write(response)
            except Exception as e:
                print(e, flush=True)
                writer.write(str(e))
        else:
            print("ignored", peer, "with command '%s'" % command, flush=True)

        

def start():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coro = MPTelnetServer.create_server(port=23, shell=shell)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())
    
if __name__ == '__main__':
    from pyBoardEx import Microterm
    
    terminal = Microterm()
    start()