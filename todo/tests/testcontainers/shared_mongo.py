from todo.tests.testcontainers.mongo_container import MongoReplicaSetContainer

_mongo_container = None

def get_shared_mongo_container():
    global _mongo_container
    if _mongo_container is None:
        _mongo_container = MongoReplicaSetContainer()
        _mongo_container.start()
    return _mongo_container