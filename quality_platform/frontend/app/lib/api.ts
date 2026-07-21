/**
 * API utility for making authenticated requests with automatic token refresh
 */

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * Get the current access token from localStorage
 */
function getAccessToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token');
  }
  return null;
}

/**
 * Get the current refresh token from localStorage
 */
function getRefreshToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('refreshToken');
  }
  return null;
}

/**
 * Store tokens in localStorage
 */
function storeTokens(accessToken: string, refreshToken: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
  }
}

/**
 * Remove tokens from localStorage
 */
function clearTokens() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
  }
}

/**
 * Check if response is a 401 unauthorized
 */
function isUnauthorized(response: Response): boolean {
  return response.status === 401;
}

/**
 * Attempt to refresh the access token
 */
async function refreshAccessToken(): Promise<boolean> {
  const refreshTokenValue = getRefreshToken();
  if (!refreshTokenValue) {
    return false;
  }

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshTokenValue }),
    });

    if (response.ok) {
      const data = await response.json();
      storeTokens(data.access_token, data.refresh_token);
      return true;
    } else {
      // Refresh token is invalid, clear tokens
      clearTokens();
      return false;
    }
  } catch (error) {
    console.error('Error refreshing token:', error);
    clearTokens();
    return false;
  }
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh token with deduplication to prevent multiple simultaneous refresh attempts
 */
async function refreshTokenWithDeduplication(): Promise<boolean> {
  if (isRefreshing) {
    // If already refreshing, wait for the existing refresh to complete
    return refreshPromise || Promise.resolve(false);
  }

  isRefreshing = true;
  refreshPromise = refreshAccessToken().finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });

  return refreshPromise;
}

/**
 * Make an authenticated API request with automatic token refresh
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const maxRetries = 1;
  let retries = 0;
  let lastError: string | null = null;

  while (retries <= maxRetries) {
    const token = getAccessToken();
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
          ...options.headers,
        },
      });

      // If unauthorized and we haven't tried refreshing yet
      if (isUnauthorized(response) && retries === 0) {
        const refreshSuccess = await refreshTokenWithDeduplication();
        
        if (refreshSuccess) {
          // Token refreshed successfully, retry the request
          retries++;
          continue;
        } else {
          // Refresh failed, return error
          return {
            status: 401,
            error: 'Authentication failed. Please log in again.',
          };
        }
      }

      // If response is not OK and not unauthorized, return error
      if (!response.ok) {
        const errorText = await response.text();
        return {
          status: response.status,
          error: errorText || 'Request failed',
        };
      }

      // Success
      const data = await response.json();
      return {
        status: response.status,
        data,
      };

    } catch (error) {
      lastError = error instanceof Error ? error.message : 'Network error';
      retries++;
      
      // If it's a network error, wait a bit before retrying
      if (retries <= maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }

  // All retries failed
  return {
    status: 0,
    error: lastError || 'Request failed after retries',
  };
}

/**
 * Convenience method for GET requests
 */
export async function apiGet<T>(endpoint: string): Promise<ApiResponse<T>> {
  return apiRequest<T>(endpoint, { method: 'GET' });
}

/**
 * Convenience method for POST requests
 */
export async function apiPost<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Convenience method for PUT requests
 */
export async function apiPut<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

/**
 * Convenience method for DELETE requests
 */
export async function apiDelete<T>(endpoint: string): Promise<ApiResponse<T>> {
  return apiRequest<T>(endpoint, { method: 'DELETE' });
}

/**
 * Upload a file (useful for PDF reports)
 */
export async function apiUpload<T>(
  endpoint: string,
  file: File,
  additionalData: Record<string, any> = {}
): Promise<ApiResponse<T>> {
  const token = getAccessToken();
  const formData = new FormData();
  
  formData.append('file', file);
  Object.keys(additionalData).forEach(key => {
    formData.append(key, additionalData[key]);
  });

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
      body: formData,
    });

    if (isUnauthorized(response)) {
      const refreshSuccess = await refreshTokenWithDeduplication();
      
      if (refreshSuccess) {
        // Retry the upload after successful refresh
        return apiUpload(endpoint, file, additionalData);
      } else {
        return {
          status: 401,
          error: 'Authentication failed. Please log in again.',
        };
      }
    }

    if (!response.ok) {
      const errorText = await response.text();
      return {
        status: response.status,
        error: errorText || 'Upload failed',
      };
    }

    const data = await response.json();
    return {
      status: response.status,
      data,
    };

  } catch (error) {
    return {
      status: 0,
      error: error instanceof Error ? error.message : 'Upload failed',
    };
  }
}