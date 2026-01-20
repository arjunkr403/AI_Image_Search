import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout:30000,
});

export const uploadImages = async (files) => {
  const formData = new FormData();
  // Append each file to the 'files' key
  if (Array.isArray(files)) {
    files.forEach((file) => {
      formData.append("files", file);
    });
  } else {
    formData.append("files", files);
  }

  try {
    //axios will set headers and boundaries for fileUpload automatically
    const response = await api.post("/upload", formData, {
      timeout: 5 * 60 * 1000, //5 minutes for large batches
    });
    console.log(response.data);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const searchImages = async (imageUrl, topK = 5) => {
  try {
    const response = await api.post("/search", {
      image_url: imageUrl,
      top_k: topK,
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};


export const getUploadHistory = async () => {
  try {
    const response = await api.get("/upload/history", {
      headers: {
        "Content-Type": "application/json",
      },
    });
    // console.log(response.data);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getSearchHistory = async () => {
  try {
    const response = await api.get("/search/history", {
      headers: {
        "Content-Type": "application/json",
      },
    });
    console.log(response.data);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getDashboardStats = async () => {
  try {
    const response = await api.get("/dashboard/stats", {
      headers: {
        "Content-Type": "application/json",
      },
    });
    // console.log(response.data);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export default api;
