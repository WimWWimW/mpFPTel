import asyncio, telnetlib3

terminal = None

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
    for itm in terminal.getID().items():
        writer.write("%-9s: %s\n" % itm) 
    writer.write("-"*50, '\n' * 2)
    
    
    while True:
        command = yield from getRemoteInput(reader, writer)
        print(command, end='', flush=True)

        if command.lower()=="quit":
            writer.write("exiting shell\n")
            print("exiting shell", flush=True)
            break

        try:
            cmd = terminal.sendLineCommand(command)
            response = terminal.readUntilPrompt(command = cmd)
            writer.write(response)
        except Exception as e:
            print(e, flush=True)
            writer.write(str(e))

        

def start():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coro = telnetlib3.create_server(port=23, shell=shell)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())
    
if __name__ == '__main__':
    from pyBoardEx import Microterm
    
    terminal = Microterm()
    start()    