import chromadb
from chromadb.utils import embedding_functions

class DungeonMemory:
    def __init__(self, session_id: str):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.ef = embedding_functions.OpenAIEmbeddingFunction(
            model_name="text-embedding-3-small"
        )
        self.collection = self.client.get_or_create_collection(
            name=f"session_{session_id}",
            embedding_function=self.ef
        )

    def add_event(self, text: str, turn: int, event_type: str):
        self.collection.add(
            documents=[text],
            metadatas=[{"turn": turn, "type": event_type}],
            ids=[f"turn_{turn}_{event_type}"]
        )

    def query(self, text: str, k: int = 5) -> list[str]:
        results = self.collection.query(query_texts=[text], n_results=k)
        return results["documents"][0] if results["documents"] else []