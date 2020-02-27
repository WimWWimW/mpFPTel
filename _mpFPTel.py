"""
FTP and Telnet server for local use (127.0.0.1) to provide
access to MicroPython microcontrollers that communicate over
a COM:-port (Windows). Thus, in combination with an external
program such as WinSCP, a convenient graphical user interface
is provided for file manegement on the board.
In addition by opening a Telnet window, direct access to
the board's repl is possible.

Copyright (C) 2020 W. de Winter. All Rights Reserved.
Usage of this sofware is free and gouverned by European or
Dutch law.

Dependencies:
    asyncio
    ampy:             https://github.com/scientifichackers/ampy
    pyftpdlib:        https://github.com/giampaolo/pyftpdlib
    telnetlib3:       https://pypi.org/project/telnetlib3/ 

Using:
    Run this module; it will start both an FTP server and a 
    Telnet server. Start a client, such as WinSCP. 
    Connect to localhost (user: 'anonymous', pwd: '').
    To get an interactive console with puTTy, some additional
    configuraton settings my be required. I use:
    - host: localhost, 23 (Telnet)
    - terminal:
        - Implicit CR
        - Implicit LF
        - Local Echo: Force On
        - Local line editing: Force On 
        - Keyboard = Linux
    
"""
import _thread as thread
import telnet
import pyftpdlib
from logging import NOTSET, DEBUG, INFO, WARNING, ERROR, FATAL
from mpFTP import AnonAuthorizer, MPFS, MPFTPHandler
from pyBoardEx import Microterm
from pyftpdlib import servers

# configuration:
host_port           = ("localhost", 21)

# For testing purposes, the connection to the pyBoard microcontroller can be bypassed entirely.
# To do so, set USE_MICROPROCESSOR to False (default: True): 
USE_MICROPROCESSOR  = True 

# For even more debug information, let the file system's 'debug' to True (default: False)
# Then every call to it's methods with be printed to the console:
MPFS.debug = True

# Set desired logging level by changing the index from the following set:
loggingLevel        = [NOTSET, DEBUG, INFO, WARNING, ERROR, FATAL][1]


if __name__ == '__main__':
    
    pyftpdlib.log.config_logging(loggingLevel)
       
    authorizer          = AnonAuthorizer()     
    authorizer.add_anonymous("/", perm="elradfmw")
    
    handler             = MPFTPHandler if USE_MICROPROCESSOR else pyftpdlib.handlers.FTPHandler
    handler.authorizer  = authorizer

    if USE_MICROPROCESSOR:
        board               = Microterm()
        MPFS.board          = board
        telnet.terminal     = board
        thread.start_new_thread(telnet.start, ())
        
    server = servers.FTPServer(host_port, handler)
    server.serve_forever()