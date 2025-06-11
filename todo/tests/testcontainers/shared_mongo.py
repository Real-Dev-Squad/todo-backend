from todo.tests.testcontainers.mongo_container import MongoReplicaSetContainer
import atexit

_mongo_container = None

def _cleanup_mongo_container():
    global _mongo_container
    if _mongo_container is not None:
        try:
            _mongo_container.stop()
        except Exception as e:
            print("Failed to stop MongoDB container:", str(e))


def get_shared_mongo_container():
    global _mongo_container
    if _mongo_container is None:
        try:
            _mongo_container = MongoReplicaSetContainer()
            _mongo_container.start()
            atexit.register(_cleanup_mongo_container)
        except Exception as e:
            print("Failed to start MongoDB container:", str(e))
            raise

    return _mongo_container
