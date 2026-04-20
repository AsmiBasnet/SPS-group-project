import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 120000, // 2 min — local LLM can be slow
});

// Attach JWT token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("pg_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/";
    }
    return Promise.reject(err);
  }
);

export default api;
