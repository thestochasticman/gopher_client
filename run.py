from gopher_client import GopherClient

if __name__ == "__main__":
    client = GopherClient("comp3310.ddns.net", 70)
    client.crawl()
    client.summary()