import numpy as np  # FAISS requires input vectors to be a NumPy array of type float32.
import faiss  # (facebook AI similarity search) search for embeddings of multimedia docs that are similar to each other
import os
import json
from app.services.embedding_store import fetch_all_embeddings

faiss_index_path="app/data/faiss.index"
faiss_ids_path="app/data/faiss_ids.json"

faiss_index = None  # global FAISS index
faiss_ids = []  # store image_id mapping
faiss_ready=False

def rebuild_faiss_from_db():
    global faiss_index,faiss_ids,faiss_ready
    
    embeddings=fetch_all_embeddings()
    if not embeddings:
        raise ValueError("No embeddings in DB")
    faiss_ids=[row["image_id"] for row in embeddings]
    #converting from python list to np array because FAISS require float32
    vectors=np.array([row["vector"] for row in embeddings],dtype="float32")
    
    # IndexFlatL2 → exact nearest-neighbor search
    # vectors.shape[1] → embedding dimension (e.g. 512)
    index=faiss.IndexFlatL2(vectors.shape[1])

    #bulk loading all embeddings
    index.add(vectors)
    
    faiss_index=index
    faiss_ready=True

def save_faiss():
    if faiss_index is None:
        return

    os.makedirs("app/data", exist_ok=True)

    faiss.write_index(faiss_index, faiss_index_path)

    with open(faiss_ids_path, "w") as f:
        json.dump(faiss_ids, f)


def load_faiss_index():
    global faiss_index, faiss_ids,faiss_ready
    # Try loading persisted FAISS
    
    if os.path.exists(faiss_index_path) and os.path.exists(faiss_ids_path):
        faiss_index=faiss.read_index(faiss_index_path)
        with open(faiss_ids_path) as f:
            faiss_ids=json.load(f)
        faiss_ready=True
        print(f"FAISS loaded from disk ({len(faiss_ids)} vectors)")
        return

    #fallback to build from db
    embeddings = fetch_all_embeddings()

    if not embeddings:
        faiss_index=None
        faiss_ids=[]
        faiss_ready=False
        print("⚠️ No embeddings in database. FAISS not initialized.")
        return

    faiss_ids = [row["image_id"] for row in embeddings]
    vectors = [row["vector"] for row in embeddings]

    # all embeddings are of same length
    dimension = len(vectors[0])

    # - Flat index = brute-force search but extremely fast in C++
    # - L2 distance = Euclidean distance (default choice for CLIP embeddings)
    # - Best for small/medium datasets (<100k images)
    index = faiss.IndexFlatL2(dimension)

    # Convert vectors to NumPy array and ensure float32 datatype
    # FAISS ONLY accepts float32 arrays. Python lists or float64 numpy arrays will fail.
    vectors_np = np.array(vectors).astype("float32")

    # Add all vectors to the FAISS index
    # FAISS internally stores them for efficient similarity search.
    index.add(vectors_np)

    faiss_index = index  # assigns index to global
    faiss_ready= True
    print(f"FAISS index initialized with {len(vectors)} vectors")


# High-Lvl Overview

# 1.Takes all your stored image embeddings

# 2. Creates a FAISS index (a search engine)

# 3. Adds all vectors into the index

# 4. Returns the ready-to-use FAISS index
