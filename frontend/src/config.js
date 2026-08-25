// API Configuration
// In local dev, uses Vite proxy. In production build, defaults to Render backend URL.
export const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://tradiq-backend.onrender.com');
