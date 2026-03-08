/**
 * tokenProvider.js — breaks the circular dependency between authStore ↔ client.
 *
 * client.js imports getToken / handleUnauthorized from here (no authStore import).
 * authStore.js calls setTokenProvider / setUnauthorizedHandler here after creation.
 */

let _getToken = () => null;
let _onUnauthorized = () => {};

export const setTokenProvider     = (fn) => { _getToken        = fn; };
export const setUnauthorizedHandler = (fn) => { _onUnauthorized = fn; };

export const getToken            = ()  => _getToken();
export const handleUnauthorized  = ()  => _onUnauthorized();
