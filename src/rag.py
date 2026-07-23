# Ollama LLM
import ollama
import chromadb
import os
import uuid


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")

client = chromadb.PersistentClient(path=DB_PATH)
collections = client.get_or_create_collection(name="jarvis_knowledge")
memory_collection = client.get_or_create_collection(name="jarvis_memory")
# Add a few test documents
docs = [
    "Your name is J.A.R.V.I.S, also called JARVIS. You will also act like a professional English butler.",
    "J.A.R.V.I.S is a personal offline AI assistant built with Ollama and ChromaDB.",
    "The user's name is Jason, also known as Phong Dinh.",
    "J.A.R.V.I.S can open apps like Notion, VS Code, and Brave, etc. J.A.R.V.I.S can also access files/folders within permitted boundaries, and J.A.R.V.I.S can also do different things to help user with daily tasks.",
]
# Helper to get embeddings from Ollama
def get_embedding(text):
    response = ollama.embeddings(model='nomic-embed-text', prompt=text, keep_alive="0")
    embedding = response['embedding']
    return embedding

def retrieve_memory(query, n_results=3):
    if memory_collection.count() == 0:
        return "No memories yet."
    embeddings = get_embedding(query)
    results = memory_collection.query(query_embeddings=[embeddings], n_results=min(n_results, memory_collection.count()))
    return "\n".join(results["documents"][0])

def save_memory(text):

    embedding = get_embedding(text)

    memory_collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[f"memory_{uuid.uuid4()}"]
    )

# Reset memory and knowledge
if __name__ == "__main__":
    client.delete_collection("jarvis_knowledge")
    client.delete_collection("jarvis_memory")
    collections = client.get_or_create_collection("jarvis_knowledge")
    memory_collection = client.get_or_create_collection("jarvis_memory")
    collections.add(
        documents=docs,
        embeddings=[get_embedding(text) for text in docs],
        ids=[f"doc_{i}" for i in range(len(docs))]
    )
    save_memory("The user's name is Jason, also known as Phong Dinh. He is a Master of AI student at Monash University, building JARVIS as his primary AI/ML portfolio project.")
    print(f"Memory count: {memory_collection.count()}")
    print(f"Knowledge count: {collections.count()}")
    for doc in memory_collection.get()["documents"]:
        print(f"- {doc}")