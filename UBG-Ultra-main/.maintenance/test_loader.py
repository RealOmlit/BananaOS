import play
import threading
import time
import urllib.request

server = play.HubServer(('', 8112), play.Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
time.sleep(1)

try:
    req = urllib.request.Request('http://localhost:8112/')
    response = urllib.request.urlopen(req, timeout=5)
    html = response.read().decode('utf-8')
    
    checks = [
        'id="loader"',
        'id="loaderFill"',
        'id="loaderTip"',
        'class="loader"',
    ]
    for check in checks:
        if check in html:
            print('OK:', check)
        else:
            print('MISSING:', check)
    
    print('Loader check complete!')
except Exception as e:
    print('Error:', e)
finally:
    server.shutdown()
    server.server_close()