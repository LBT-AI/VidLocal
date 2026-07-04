class BaseDownloader:
    name = None
    domains = []

    def match(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    def preprocess(self, url: str) -> dict:
        raise NotImplementedError

    def download(self, data: dict) -> str:
        raise NotImplementedError
