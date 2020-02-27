import serial


def listComPorts(maxPort = 32, minPort = 1):
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

pp = listComPorts()
print(pp)
if any([p.startswith("*") for p in pp]):
    print("port(s) %s is/are in use by another process" % ", ".join([p[1:] for p in pp]))