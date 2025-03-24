import sys
import socket
import re
import ssl
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def show_help():
    print("""go2web - Simple HTTP Client
Usage:
  go2web -u <URL>         # Fetch and display content from URL
  go2web -s <search-term> # Search term and show top 10 results
  go2web -h               # Show this help""")


def strip_html_tags(html):
    no_tags = re.sub(r'<[^>]+>', '', html)
    normalized = re.sub(r'\s+', ' ', no_tags).strip()
    return normalized


def fetch(url, path="/"):
    try:
        port = 443 if "https://" in url else 80
        conn = socket.create_connection((url, port))
        request = f"GET {path} HTTP/1.1\r\nHost: {url}\r\nConnection: close\r\n\r\n"
        conn.send(request.encode())

        response = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            response += chunk

        conn.close()

        header_body_split = response.split(b"\r\n\r\n", 1)
        if len(header_body_split) < 2:
            return "No body content received."
        headers, body = header_body_split
        decoded_body = body.decode(errors="ignore")
        readable = strip_html_tags(decoded_body)
        return readable
    except Exception as e:
        return f"Error: {e}"


def make_request(host, path, use_ssl=True):
    port = 443 if use_ssl else 80
    sock = socket.create_connection((host, port))
    if use_ssl:
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: 'go2web/1.0'\r\nConnection: close\r\n\r\n"
    sock.sendall(request.encode())
    response = b""

    while chunk := sock.recv(4096):
        response += chunk

    sock.close()
    return response.decode(errors='ignore')


def make_request(host, path, use_ssl=True):
    port = 443 if use_ssl else 80
    sock = socket.create_connection((host, port))
    if use_ssl:
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: 'go2web/1.0'\r\nConnection: close\r\n\r\n"
    sock.sendall(request.encode())
    response = b""

    while chunk := sock.recv(4096):
        response += chunk

    sock.close()
    return response.decode(errors='ignore')


def send_http_request(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path if parsed.path else "/"
    if parsed.query:
        path += "?" + parsed.query
    scheme = parsed.scheme
    port = 443 if scheme == "https" else 80
    try:
        sock = socket.create_connection((host, port))
    except Exception as e:
        return f"Error creating connection: {e}"

    if scheme == "https":
        try:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        except Exception as e:
            return f"SSL error: {e}"
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: go2web/1.0\r\nConnection: close\r\n\r\n"
    try:
        sock.sendall(request.encode())
    except Exception as e:
        return f"Error sending request: {e}"
    response = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    except Exception as e:
        return f"Error receiving data: {e}"
    finally:
        sock.close()

    parts = response.split(b"\r\n\r\n", 1)
    body = parts[1] if len(parts) > 1 else response
    return body.decode(errors="ignore")

def handle_search(term):
    query = "+".join(term.split())
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    print(f"Searching for: {term}\n")
    raw_response = send_http_request(search_url)
    soup = BeautifulSoup(raw_response, "html.parser")
    results = soup.find_all('a', class_='result__a', limit=10)
    if results:
        for i, link in enumerate(results, start=1):
            title = link.get_text().strip()
            href = link.get('href')
            print(f"{i}. {title}\n   {href}\n")
    else:
        print("No results found.")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    option = sys.argv[1]

    if option == "-h":
        show_help()
    elif option == "-u" and len(sys.argv) == 3:
        url = sys.argv[2]
        output = fetch(url)
        print("Response:\n", output)
    elif option == "-s" and len(sys.argv) >= 3:
        search_term = ' '.join(sys.argv[2:])
        print(handle_search(search_term))
    else:
        print("Invalid command. Use -h for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()