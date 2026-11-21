class GenericAdapter:
    """Entrada por webhook firmado (POST /api/v1/webhooks/generic). Sin remoto: no sondea ni escribe."""

    default_poll_seconds = 0

    def __init__(self, config: dict, token: str | None, transport=None):
        self.config = config

    def __repr__(self) -> str:
        return "GenericAdapter()"

    def fetch_new_items(self):
        return []

    def get_item(self, remote_id: str):
        raise NotImplementedError("generic: sin remoto")

    def comment(self, remote_id: str, text: str) -> None:
        raise NotImplementedError("generic: sin remoto")

    def set_labels(self, remote_id: str, labels: list[str]) -> None:
        raise NotImplementedError("generic: sin remoto")

    def create_branch(self, name: str, base: str) -> None:
        raise NotImplementedError("generic: sin repo")

    def open_pr(self, head: str, base: str, title: str, body: str) -> str:
        raise NotImplementedError("generic: sin repo")

    def merge_pr(self, pr_id: str) -> None:
        raise NotImplementedError("generic: sin repo")

    def get_diff(self, pr_id: str) -> str:
        raise NotImplementedError("generic: sin repo")
