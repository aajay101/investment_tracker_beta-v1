import socket
import requests
import time

def check_server_port(host="127.0.0.1", port=5000):
    """Check if server is running and port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Server port {port} is open on {host}")
            return True
        else:
            print(f"❌ Server port {port} is closed on {host}")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

def check_http_connection(url="http://127.0.0.1:5000"):
    """Check if HTTP server is responding"""
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ Server at {url} is reachable")
        print(f"   Status code: {response.status_code}")
        print(f"   Content length: {len(response.content)} bytes")
        return True
    except requests.RequestException as e:
        print(f"❌ Error connecting to {url}: {e}")
        return False

if __name__ == "__main__":
    print("Running server accessibility checks...")
    print("-" * 40)
    
    # First check if port is open
    port_open = check_server_port()
    
    if port_open:
        # If port is open, try HTTP connection
        print("\nChecking HTTP connection...")
        http_ok = check_http_connection()
        
        if http_ok:
            print("\n✅ Server is fully accessible!")
        else:
            print("\n❌ Server port is open but HTTP connection failed")
    else:
        print("\n❌ Server is not running or not accessible")
    
    print("-" * 40)
    print("Try accessing the application at: http://127.0.0.1:5000") 