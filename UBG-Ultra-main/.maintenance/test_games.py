import play
import threading
import time
import urllib.request
import json

server = play.HubServer(('', 8113), play.Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
time.sleep(1)

try:
    # Test API games
    req = urllib.request.Request('http://localhost:8113/api/games')
    response = urllib.request.urlopen(req, timeout=5)
    data = json.loads(response.read().decode())
    print('Games API:', response.status, 'Count:', data.get('count', 0))
    
    # Test a few game files
    for game in ['slope.html', 'tetris/index.html', '1.12.html']:
        req = urllib.request.Request('http://localhost:8113/' + game)
        response = urllib.request.urlopen(req, timeout=5)
        print(game + ':', response.status)
    
    print('All tests passed!')
except Exception as e:
    print('Error:', e)
finally:
    server.shutdown()
    server.server_close()