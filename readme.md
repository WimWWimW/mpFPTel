# mpFPTel
FTP and Telnet server for local use (127.0.0.1) to provide access to MicroPython microcontrollers that communicate over a COM:-port (Windows)

Thus, in combination with an external
program such as WinSCP, a convenient graphical user interface
is provided for file manegement on the board.
In addition by opening a Telnet window, direct access to
the board's repl is possible.


# Dependencies:
*    asyncio
*   ampy:             https://github.com/scientifichackers/ampy
*    pyftpdlib:        https://github.com/giampaolo/pyftpdlib
*    telnetlib3:       https://pypi.org/project/telnetlib3/ 

#Using:
Run this module; it will start both an FTP server and a 
    Telnet server. Start a client, such as WinSCP. 
    Connect to localhost (user: 'anonymous', pwd: '').
    To get an interactive console with puTTy, some additional
    configuraton settings my be required. I use:
- host: localhost, 23 (Telnet)
- terminal
- - Implicit CR
- - Implicit LF
- - Local Echo: Force On
- - Local line editing: Force On 
- - Keyboard = Linux
    
Tested with Python 3.4, Windows server 2003, micropython 1.10, WinSCP 5.17