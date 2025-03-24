import sys
import socket
import re

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
    else:
        print("Invalid command. Use -h for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()