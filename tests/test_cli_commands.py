from click.testing import CliRunner

from pisecure import cli_refactored


class DummyScheduler:
    def __init__(self):
        self.tasks = {}
        self.started = False
        self.stopped = False

    def add_interval_task(self, name, interval_seconds, func, **kwargs):
        self.tasks[name] = func
        func()  # run once immediately for tests

    def remove_task(self, name):
        self.tasks.pop(name, None)

    def start(self):
        self.started = True

    def stop(self, timeout: float = 5.0):
        self.stopped = True

    def is_running(self):
        return self.started and not self.stopped


def test_status_command(monkeypatch):
    class DummyChain:
        def __init__(self, *args, **kwargs):
            self.calls = []

        def get_chain_info(self):
            return {
                "blocks": 10,
                "pending_transactions": 2,
                "difficulty": 5,
                "is_valid": True,
                "latest_block": {"index": 9, "transactions": [1, 2, 3]},
            }

    monkeypatch.setattr("pisecure.cli.commands.blockchain.SignChain", DummyChain)
    monkeypatch.setattr(
        "pisecure.cli_refactored.create_default_scheduler", lambda: DummyScheduler()
    )

    runner = CliRunner()
    result = runner.invoke(cli_refactored.cli, ["status"])
    assert result.exit_code == 0
    assert "Blocks" in result.output


def test_network_command(monkeypatch):
    monkeypatch.setenv("PISECURE_WEBSOCKET_P2P", "0")
    monkeypatch.setattr(
        "pisecure.cli_refactored.create_default_scheduler", lambda: DummyScheduler()
    )

    runner = CliRunner()
    result = runner.invoke(cli_refactored.cli, ["network", "--enable"])
    assert result.exit_code == 0
    assert "WebSocket" in result.output


def test_wallet_command(monkeypatch):
    class DummyWallet:
        def __init__(self, name="default", data_dir="/tmp"):
            self.wallet_name = name
            self.data_dir = data_dir

        def get_balance(self):
            return 1.5

    class DummyManager:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        def list_wallets(self):
            return ["main"]

        def load_wallet(self, name):
            return DummyWallet(name)

    monkeypatch.setattr("pisecure.cli.commands.wallet.WalletManager", DummyManager)
    monkeypatch.setattr("pisecure.cli.commands.wallet.PiSecureWallet", DummyWallet)
    monkeypatch.setattr(
        "pisecure.cli_refactored.create_default_scheduler", lambda: DummyScheduler()
    )

    runner = CliRunner()
    result = runner.invoke(cli_refactored.cli, ["wallet"])
    assert result.exit_code == 0
    assert "Available Wallets" in result.output


def test_mining_command(monkeypatch):
    class DummyChain:
        def __init__(self, *args, **kwargs):
            self.calls = 0

        def mine_pending_transactions(self, wallet):
            self.calls += 1
            if self.calls == 1:
                return {"index": 1}
            return None

    monkeypatch.setattr("pisecure.cli.commands.mining.SignChain", DummyChain)
    monkeypatch.setattr(
        "pisecure.cli_refactored.create_default_scheduler", lambda: DummyScheduler()
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_refactored.cli,
        ["mine", "--wallet", "addr1", "--count", "1", "--sleep", "0.0"],
    )
    assert result.exit_code == 0
    assert "Mined block" in result.output


def test_monitor_command(monkeypatch):
    class DummyChain:
        def __init__(self, *args, **kwargs):
            pass

        def get_chain_info(self):
            return {
                "blocks": 1,
                "pending_transactions": 0,
                "difficulty": 1,
                "is_valid": True,
            }

    ds = DummyScheduler()

    monkeypatch.setattr("pisecure.cli.commands.monitoring.SignChain", DummyChain)
    monkeypatch.setattr("pisecure.cli_refactored.create_default_scheduler", lambda: ds)

    runner = CliRunner()
    result = runner.invoke(
        cli_refactored.cli, ["monitor", "--refresh", "0.01", "--iterations", "1"]
    )
    assert result.exit_code == 0
    assert "Monitor" in result.output
