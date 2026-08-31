let _getToken = () => null;
let _onUnauthorized = () => {};

/**
 * Register the function that retrieves the current JWT access token.
 * Typically called during store initialization (e.g., in authStore.js).
 */
export const setTokenProvider = (fn) => {
  if (typeof fn === "function") {
    _getToken = fn;
  }
};

/**
 * Register the callback executed when an API request returns a 401 Unauthorized status.
 */
export const setUnauthorizedHandler = (fn) => {
  if (typeof fn === "function") {
    _onUnauthorized = fn;
  }
};

/**
 * Synchronously retrieves the active token from the registered provider.
 */
export const getToken = () => {
  try {
    return _getToken();
  } catch (error) {
    console.warn("[TokenProvider] Error executing getToken provider:", error);
    return null;
  }
};

/**
 * Executes the registered unauthorized handler to clear auth state and trigger logout.
 */
export const handleUnauthorized = () => {
  try {
    _onUnauthorized();
  } catch (error) {
    console.warn("[TokenProvider] Error executing unauthorized handler:", error);
  }
};