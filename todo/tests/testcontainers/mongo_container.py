import time
import json
from testcontainers.core.generic import DockerContainer
from pymongo import MongoClient
from testcontainers.core.waiting_utils import wait_for_logs


class MongoReplicaSetContainer(DockerContainer):
    def __init__(self, image: str = "mongo:6.0"):
        super().__init__(image=image)
        self.with_exposed_ports(27017)
        self.with_command(["mongod", "--replSet", "rs0", "--bind_ip_all"])
        self._mongo_url = None

    def start(self):
        super().start()
        self._container.reload()
        mapped_port = self.get_exposed_port(27017)
        container_ip = self._container.attrs["NetworkSettings"]["IPAddress"]
        member_host = f"{container_ip}:27017"
        initiate_js = json.dumps({"_id": "rs0", "members": [{"_id": 0, "host": member_host}]})
        wait_for_logs(self, r"Waiting for connections", timeout=20)
        cmd = ["mongosh", "--quiet", "--host", "localhost", "--port", "27017", "--eval", f"rs.initiate({initiate_js})"]
        exit_code, output = self.exec(cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"rs.initiate() failed (exit code {exit_code}):\n" f"{output.decode('utf-8', errors='ignore')}"
            )
        self._mongo_url = f"mongodb://localhost:{mapped_port}/testdb?directConnection=true"
        self._wait_for_primary()
        return self

    def get_connection_url(self) -> str:
        return self._mongo_url

    def _wait_for_primary(self, timeout=10):
        client = MongoClient(self.get_connection_url())
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = client.admin.command("isMaster")
                if status.get("ismaster", False):
                    return
            except Exception as e:
                print(f"Waiting for PRIMARY: {e}")
            time.sleep(0.5)
        raise TimeoutError(
            "Timed out waiting for replica set to become PRIMARY.")