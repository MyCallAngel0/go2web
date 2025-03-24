#!/usr/bin/env python3
import sys
import socket
import re
import ssl
import os
import time
import hashlib
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import argparse

CACHE_DIR = "cache"
CACHE_MAX_AGE = 60  # seconds


def show_help():
    help_text = """go2web - Simple HTTP Client
Usage:
  go2web -u <URL> [--json]         # Fetch and display content from URL. Use --json to force JSON parsing.
  go2web -s <search-term> [--json]  # Search term and show top 10 results. Use --json to output JSON.
  go2web -h                       # Show this help
"""
    print(help_text)


def strip_html_tags(html):
    no_tags = re.sub(r'<[^>]+>', '', html)
    normalized = re.sub(r'\s+', ' ', no_tags).strip()
    return normalized


def fetch(url, force_json=False):
    """
    Simple fetch mode for URL content.
    If force_json is True, delegate to send_http_request for content negotiation.
    """
    if force_json:
        return send_http_request(url, force_json=True)

    try:
        # Parse URL to extract host and path.
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "http://" + url
            parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path if parsed.path else "/"
        port = 443 if parsed.scheme == "https" else 80

        conn = socket.create_connection((host, port))
        if parsed.scheme == "https":
            conn = ssl.create_default_context().wrap_socket(conn, server_hostname=host)

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
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


def send_http_request(url, use_cache=True, force_json=False):
    """
    Sends an HTTP GET request for a full URL, supports caching, follows redirects,
    and does basic content negotiation.
    If force_json is True, the Accept header requests JSON.
    """
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, cache_key)
    if use_cache and os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < CACHE_MAX_AGE:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

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

    # Set Accept header based on force_json flag.
    accept_header = "application/json" if force_json else "text/html, application/json"
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: go2web/1.0\r\n"
        f"Accept: {accept_header}\r\n"
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
    status_code = 200
    if header_lines:
        try:
            status_code = int(header_lines[0].split(" ")[1])
        except (IndexError, ValueError):
            status_code = 200
    # Follow redirects.
    if status_code in [301, 302, 303, 307, 308]:
        location = None
        for line in header_lines:
            if line.lower().startswith("location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            redirect_url = urljoin(url, location)
            return send_http_request(redirect_url, use_cache, force_json)
    content_type = ""
    for line in header_lines:
        if line.lower().startswith("content-type:"):
            content_type = line.split(":", 1)[1].strip()
            break
    body_string = body_bytes.decode(errors="ignore")
    # In non-force mode, if response is JSON we try to pretty-print it.
    if not force_json and "application/json" in content_type:
        try:
            json_obj = json.loads(body_string)
            body_string = json.dumps(json_obj, indent=4)
        except Exception:
            pass
    if use_cache:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(body_string)
        except Exception as e:
            print(f"Warning: Unable to write to cache: {e}")
    return body_string


def handle_search(term, force_json=False):
    """
    Uses DuckDuckGo's lite HTML search interface to obtain search results.
    If force_json is True, outputs the results as a JSON array.
    Otherwise, prints plain text.
    """
    query = "+".join(term.split())
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    raw_response = send_http_request(search_url)
    soup = BeautifulSoup(raw_response, "html.parser")
    results = soup.find_all('a', class_='result__a', limit=10)
    search_results = []
    if results:
        for i, link in enumerate(results, start=1):
            title = link.get_text().strip()
            href = link.get('href').strip()
            if href.startswith("//"):
                href = "https:" + href
            search_results.append({"index": i, "title": title, "url": href})
        if force_json:
            print(json.dumps(search_results, indent=4))
        else:
            for result in search_results:
                print(f"{result['index']}. {result['title']}\n   {result['url']}\n")
    else:
        print("No results found.")


def main():
    parser = argparse.ArgumentParser(description="go2web - Simple HTTP Client")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", metavar="URL", help="Fetch and display content from URL")
    group.add_argument("-s", metavar="SEARCH_TERM", nargs="+", help="Search term and display top 10 results")
    parser.add_argument("--json", action="store_true", help="Force JSON output/negotiation")
    args = parser.parse_args()

    if args.u:
        url = args.u
        if args.json:
            output = send_http_request(url, force_json=True)
        else:
            output = fetch(url)
        print("Response:\n", output)
    elif args.s:
        search_term = " ".join(args.s)
        handle_search(search_term, force_json=args.json)


if __name__ == "__main__":
    main()
