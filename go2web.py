import sys
import socket
import re
import ssl
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import os
import json
import hashlib
import time

CACHE_DIR = "cache"
CACHE_MAX_AGE = 600  # seconds

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

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: go2web/1.0\r\nConnection: close\r\n\r\n"
    sock.sendall(request.encode())
    response = b""

    while chunk := sock.recv(4096):
        response += chunk

    sock.close()
    return response.decode(errors='ignore')


def send_http_request(url, use_cache=True):
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)

    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, cache_key)

    if use_cache and os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < CACHE_MAX_AGE:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

    # Ensure the URL has a scheme.
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

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: go2web/1.0\r\n"
        f"Accept: text/html, application/json\r\n"
        f"Connection: close\r\n\r\n"
    )
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
    if len(parts) < 2:
        body_bytes = response
        headers_text = ""
    else:
        headers_bytes, body_bytes = parts
        headers_text = headers_bytes.decode("iso-8859-1")

    header_lines = headers_text.split("\r\n")
    if header_lines:
        status_line = header_lines[0]
        try:
            status_code = int(status_line.split(" ")[1])
        except (IndexError, ValueError):
            status_code = 200
    else:
        status_code = 200

    if 300 < status_code < 400:
        location = None
        for line in header_lines:
            if line.lower().startswith("location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            redirect_url = urljoin(url, location)
            return send_http_request(redirect_url, use_cache)

    body_string = body_bytes.decode(errors="ignore")

    if use_cache:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(body_string)
        except Exception as e:
            print(f"Warning: Unable to write to cache: {e}")

    return body_string


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