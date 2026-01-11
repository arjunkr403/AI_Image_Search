# from fastapi import (
#     APIRouter,
#     HTTPException,
# )  # apirouter to group route,httpexp for api errors
# from app.services.db import (
#     get_db_connection,
#     release_db_connection,
# )  # borrows db connection from pool
# from app.ml.embeddings import gen_img_embedding  # clip func that returns 512D vector

# router = APIRouter(prefix="/embed", tags=["Embeddings"])


# @router.post("/{image_id}")
# def embed_image(image_id: int):
#     conn = get_db_connection()
#     try:
#         with conn.cursor() as cur:

#             cur.execute(
#                 "SELECT filepath FROM images WHERE id=%s", (image_id,)
#             )  # ((image_id)) is not a tuple , to make it tuple use ","
#             result = cur.fetchone()  # tuple unpacking

#             if not result:
#                 raise HTTPException(status_code=404, detail="Image not found")

#             image_path = result["filepath"]

#             vector = gen_img_embedding(image_path)  # generating embedding

#             cur.execute(  # inserting the image_id and embedding in embedding table
#                 "INSERT INTO embeddings (image_id,vector) VALUES (%s,%s)",
#                 (image_id, vector),
#             )
#             conn.commit()

#             return {"message": "Embedding generated", "image_id": image_id}
#     finally:
#         release_db_connection(conn)
