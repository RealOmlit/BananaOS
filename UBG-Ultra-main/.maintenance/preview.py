"""Start the existing server on loopback without opening a browser."""
import play

if __name__ == '__main__':
    play.ensure_catalog()
    with play.HubServer(('127.0.0.1', 8115), play.Handler) as server:
        print('UBG Ultra: http://127.0.0.1:8115', flush=True)
        server.serve_forever()
