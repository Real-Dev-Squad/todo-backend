import os
import time
import json
from testcontainers.core.generic import DockerContainer
from pymongo import MongoClient


class MongoReplicaSetContainer(DockerContainer):
    def __init__(self, image: str = "mongo:6.0"):
        super().__init__(image=image)
        self.with_exposed_ports(27017)
        self.with_command(["mongod", "--replSet", "rs0", "--bind_ip_all"])

    def start(self):
        super().start()
        self._container.reload()

        mapped_port = self.get_exposed_port(27017)
        default_db = "testdb"
        mongo_url = f"mongodb://localhost:{mapped_port}/{default_db}" f"?replicaSet=rs0"
        self._mongo_url = mongo_url
        host = "localhost" if os.environ.get("CI") else "host.docker.internal"
        member_host = f"{host}:{mapped_port}"
        initiate_js = json.dumps({"_id": "rs0", "members": [{"_id": 0, "host": member_host}]})

        time.sleep(1)

        cmd = [
            "mongosh",
            "--quiet",
            "--host",
            "host.docker.internal",
            "--port",
            str(mapped_port),
            "--eval",
            f"rs.initiate({initiate_js})",
        ]
        exit_code, output = self.exec(cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"rs.initiate() failed (exit code {exit_code}):\n" f"{output.decode('utf-8', errors='ignore')}"
            )
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
                    print("[DEBUG] Node is PRIMARY.")
                    return
            except Exception as e:
                print(f"[DEBUG] Waiting for PRIMARY: {e}")
            time.sleep(0.5)
        raise TimeoutError("Timed out waiting for replica set to become PRIMARY.")
