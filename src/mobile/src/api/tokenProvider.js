let _getToken = () => null;
let _onUnauthorized = () => {};
export const setTokenProvider = (fn) => { _getToken = fn; };
export const setUnauthorizedHandler = (fn) => { _onUnauthorized = fn; };
export const getToken = () => _getToken();
export const handleUnauthorized = () => _onUnauthorized();
