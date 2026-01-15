## 🗓️ Initial Setup — 24 Nov 2025

### ✔️ Completed

- 📁 Created project root folder  
- 🔗 Initialized Git & connected GitHub repository  
- 🎨 Frontend Setup (React + Vite)
  - TailwindCSS
  - shadcn/ui components
  - Axios for API calls
  - Added Vite PWA support
- ⚙️ Backend Setup (FastAPI)
  - Installed ML dependencies:
    - PyTorch
    - Sentence Transformers
    - FAISS (vector search)
- 🐳 Containerization
  - Setup Docker + Docker Compose
  - Started *Postgres* + *Redis* containers
- 📂 Finalized complete folder structure


---

## 🗓️ Backend Architecture + DB/Redis Setup — 02 Dec 2025

### ✔️ Completed

- Created `.env` file for environment variables
- Implemented configuration handler using *Pydantic* → `config.py`
- Setup PostgreSQL database connection
- Setup Redis caching connection
- Added `/health` API route (`routers/health.py`)
- Registered routers in `main.py`
- Verified backend infrastructure:
  - 🚀 FastAPI running successfully
  - 🗄️ DB connection: *OK*
  - ⚡ Redis cache: *OK*
- Backend skeleton ready for ML search features


### 📘 What I Learned

- Secure environment variables using `.env`
- Loading app settings via *Pydantic* models
- PostgreSQL connection flow with `psycopg2`
- Redis usage for high-speed caching
- FastAPI modular router architecture
- Role of health-check APIs in production

---

## 🗓️ Image Upload API + Database Setup — 03 Dec 2025

### ✔️ Completed

- Added uploads/ directory for storing user-uploaded images
- Implemented images table creation using raw SQL
- Integrated automatic DB table initialization in main.py
- Developed /upload API route:
  - Image type validation (PNG/JPG/JPEG)
  - UUID-based secure filename generation
  - Saved file to local filesystem
  - Inserted metadata (filename, path, timestamp) into PostgreSQL
- Added Redis caching for uploaded image metadata
- Registered upload router in main.py
- Tested upload functionality successfully using Postman


### 📘 What I Learned

- Handling file uploads using FastAPI’s UploadFile
- Secure filename creation using UUID
- Creating and inserting data into tables using psycopg2
- Using Redis to store metadata for faster access
- Building modular, scalable router structures in FastAPI
- Designing a file-storage workflow required for ML pipelines


---


## 📅 Embedding Generation & FAISS Preparation — 09 Dec 2025

### ✔️ Completed

- Created ML module structure: clip_model.py, embeddings.py, faiss_index.py
- Loaded CLIP model (clip-ViT-B-32) for image embedding generation
- Implemented embedding generator function and integrated it with file storage
- Added embeddings table to PostgreSQL for storing vector representations
- Developed /embed/{image_id} API endpoint:
  - Validates image presence
  - Generates CLIP embeddings
  - Inserts embedding vectors into database
- Successfully tested embedding creation in Postman
- Prepared FAISS index creation function for Day 5 search features


### 📘 What I Learned

- How to use CLIP for generating semantic image embeddings
- Storing embeddings as lists of floats in PostgreSQL
- Structuring ML modules inside a production backend
- How FAISS indexes work (IndexFlatL2, dimension detection)
- Designing an end-to-end embedding pipeline for image search


---


## 📅 Search Pipeline (FAISS + Similarity Search API) — 09 Dec 2025

### ✔️ Completed

- Set up full FAISS search workflow
- Loaded all embeddings from PostgreSQL into memory
- Built FAISS index for similarity search
- Added real-time FAISS updates during image upload
- Implemented /search API endpoint
  - Accepts a query image
  - Generates CLIP embedding
  - Performs similarity search using FAISS
  - Returns most similar stored images
- Successfully tested search functionality in Postman
- Verified end-to-end search pipeline is working

### 📘 What I Learned

- How FAISS indexes accelerate similarity search
- How to organize ML search pipeline inside FastAPI
- Importance of global index loading during app startup
- How to generate embeddings for query images
- Mapping FAISS results back to database image records
- Building a complete semantic image search workflow


---


## 📅 C++ Image Preprocessing Optimization — 12 Dec 2025

### ✔️ Completed

- Set up a C++ preprocessing module using:
  - OpenCV for fast, optimized image operations
  - pybind11 for creating Python bindings
- Implemented high-performance preprocessing steps:
  - Image resizing to 224×224 (CLIP standard)
  - Denoising (fastNlMeansDenoisingColored)
  - Sharpening (Gaussian + weighted enhancement)
  - BGR → RGB conversion for CLIP compatibility
- Created cpp/preprocess.cpp implementing the preprocessing pipeline
- Compiled the module into a Python-importable .so file using CMake
- Successfully built the shared library using:
  - cmake ..
  - make -j4
- Integrated C++ preprocessing into Python backend:
  - Added module into app/ml/
  - Updated gen_img_embedding() to use fast preprocessing
  - Converted NumPy → PIL → CLIP embedding
- Fixed CLIP model usage (using model.encode() which works for both images and text in sentence-transformers)

### 📘 What I Learned

- How Python loads C++ modules compiled via pybind11
- How OpenCV C++ provides much faster preprocessing than Python
- Correct CLIP usage in sentence-transformers:
  - model.encode() supports images + text
  - encode_image() does NOT exist in this variant
- How preprocessing stabilizes CLIP embeddings and improves search quality
- How to structure a mixed C++ + Python production pipeline
- How to debug import paths for compiled .so modules


---

## 📅 Full-Stack Integration & Frontend Features — 27 Dec 2025

### ✔️ Completed

- Integrated React frontend with FastAPI backend for upload and search.
- Enhanced Dashboard page with live data, including a "Total Searches" counter.
- Implemented a full-stack Search History feature:
  - Backend: Added `search_history` table and a `/search/history` API endpoint to the search router.
  - Frontend: Built out the History page UI, fetching and displaying live search logs.
- Created a robust API service layer (`api.js`) with Axios to handle all backend communication.
- Refactored the search API for more efficient database connection handling.
- Performed end-to-end debugging to resolve a `500 Internal Server Error` caused by a database schema mismatch.

### 📘 What I Learned

- The complete lifecycle of a full-stack feature, from database to UI.
- Extending existing FastAPI routers with new endpoints to maintain a modular API.
- Managing complex state in React (loading status, tabs, API data).
- Building dynamic UIs that render live data instead of static mockups.
- How Axios handles `Content-Type` headers differently for `FormData` vs. JSON.
- End-to-end debugging, tracing an error from a frontend `AxiosError` to a backend database issue.

---

## 📅 Optimizing and Making it Ready for Deployment (Part 1) — 11 Jan 2026

### ✔️ Completed
- *Production-Ready Architecture:*
  - Added a root `docker-compose.yml` for local orchestration and created Kubernetes manifests (`/k8s`) for future deployment.
  - Solved data persistence issues by removing the `uploads` directory from the image and using a named Docker volume to keep files across container restarts.
- *System Stability & Reliability:*
  - Hardened the FAISS index by implementing a startup routine that loads from cache or rebuilds from the database, and added a `POST /admin/reindex` endpoint for manual recovery.
  - Switched to a non-root user inside the container and fixed resulting permission errors, a critical security step for production environments.
  - Eliminated container restart loops by fixing a `fastapi.logger` crash that occurred during application startup.
- *Critical Bug & Performance Fixes:*
  - Resolved an `ImportError` for a shared C++ library (`libopencv_photo.so`) by ensuring it was included in the final stage of the multi-stage Docker build.
  - Fixed browser crashes (`ERR_NETWORK`) on large uploads by refactoring the frontend to stream files in batches instead of storing thousands of `File` objects in React state.
  - Increased the Nginx `client_max_body_size` to prevent `413 Request Entity Too Large` errors.
  - Implemented Redis caching for database calls to improve API response times for search, history, and dashboard statistics.

### 📘 What I Learned
- *Containers are Stateless:* Runtime data (like user uploads) must be handled by persistent volumes. Storing state in a container image leads to data loss and inconsistency.
- *Infrastructure Bugs Masquerade as API Bugs:* Many `500`/`502` errors originated from deeper issues like Docker permissions, missing volumes, or Nginx configuration, not application code.
- *Running as a Non-Root User is a Production Requirement:* It's a key security practice that uncovers hidden flaws in file permissions that are masked when running as `root`.
- *System Layers Must Be Kept in Sync:* A system with a filesystem, a database, and an in-memory index (FAISS) will fail if its layers become inconsistent. The architecture must account for this.
- *Docker Workflow Details Matter:* `docker compose restart` only restarts a container and does not apply code changes; `docker compose up --build` is required. Native libraries also require their runtime dependencies to be copied to the final stage of a multi-stage build.
- *The Browser Has Limits:* Client-side memory can be a major bottleneck. Storing large amounts of data (like thousands of file objects) in React state can crash a browser before network requests are even made.

### 💡 Key Insights & Debugging Moments
- *Isolating Infra vs. App Bugs:* Proved the backend was working correctly by using `curl http://back:8000/health` from within another container. This confirmed that the 502 errors were caused by the Nginx proxy or Docker networking, not the application code.
- *Deceptive Browser Errors:* Discovered that a generic `ERR_NETWORK` from the browser during large uploads was not a network failure, but was caused by the browser running out of memory while trying to prepare the request. The backend never even received the call.
- *Database & Cache Nuances:* Uncovered subtle but critical database and cache behaviors.
    - A PostgreSQL `ON CONFLICT` statement failed because the target column was missing a `UNIQUE` constraint.
    - A Redis `DEL upload:history:*` command was silently failing; the correct, safe way to delete wildcard patterns is to use `SCAN` followed by individual `DEL` calls.
- *The "Immutable Image" Realization:* A key "aha" moment was understanding that `docker compose restart` does not apply any code changes. Only a full `docker compose up --build` creates a new, immutable image with the latest code, which explained why recent fixes weren't appearing.