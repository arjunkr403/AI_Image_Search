import app.ml.cpp_preprocess as cpp  # c++ fast preprocessing
import numpy as np  # because CLIP returns embeddings in NumPy arrays
from app.ml.clip_model import model  #  preloaded CLIP model
from PIL import Image  # for image manipulation


def gen_img_embedding(image_path: str):
    arr = cpp.preprocess_image(image_path)  # returns NumPy array (224x224x3)

    img = Image.fromarray(arr.astype("uint8"))  # Convert NumPy -> PIL

    embedding = model.encode([img], convert_to_numpy=True)[0]  # take the first element
    # encoding using CLIP vision encoder & return a 512D embedding vector

    # Normalize the embedding
    norm = np.linalg.norm(embedding)  # unit vector (direction with magnitude=1)
    # L2 distance ≈ cosine distance
    # Lower L2 distance ⇔ higher cosine similarity

    if norm > 0:
        embedding = embedding / norm
        # The vector keeps its direction
        # Its length becomes 1
    
    return np.array(embedding).tolist()  # convert numpy -> list for JSON/db


# image_path
#  → C++ preprocess → NumPy(224x224*3)
#  → PIL Image
#  → model.encode([PIL], convert_to_numpy=True)
#  → numpy embedding (512D)
#  → normalized numpy vector (unit length)
#  → list (JSON / DB safe)
