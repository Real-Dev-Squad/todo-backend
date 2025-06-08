from todo.tests.testcontainers.mongo_container import MongoReplicaSetContainer

_mongo_container = None

def get_shared_mongo_container():
    global _mongo_container
    if _mongo_container is None:
        try:
            _mongo_container = MongoReplicaSetContainer()
            _mongo_container.start()
        except Exception as e:
            print("Failed to start MongoDB container:", str(e))
            raise

    return _mongo_container
