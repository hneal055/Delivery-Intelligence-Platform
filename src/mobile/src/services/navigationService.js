// src/mobile/src/services/navigationService.js
// Navigation service supporting Waze, Google Maps, and Apple Maps

import { Platform, Linking, Alert } from 'react-native';

/**
 * Open navigation to destination
 * @param {number} latitude - Destination latitude
 * @param {number} longitude - Destination longitude
 * @param {string} label - Location name/address
 * @param {string} preference - 'waze' | 'google' | 'apple' | 'auto'
 */
export async function navigateTo(latitude, longitude, label = 'Destination', preference = 'auto') {
  if (!latitude || !longitude) {
    Alert.alert('Error', 'Invalid destination coordinates');
    return false;
  }

  try {
    // If auto, select based on platform and available apps
    if (preference === 'auto') {
      const wazeAvailable = await checkAppInstalled('waze');
      if (wazeAvailable) {
        return openWaze(latitude, longitude, label);
      }
      const googleAvailable = await checkAppInstalled('google-maps');
      if (googleAvailable) {
        return openGoogleMaps(latitude, longitude, label);
      }
      // Fallback to platform default
      return Platform.OS === 'ios' 
        ? openAppleMaps(latitude, longitude, label)
        : openGoogleMaps(latitude, longitude, label);
    }

    // Try specific app
    switch (preference.toLowerCase()) {
      case 'waze':
        return await openWaze(latitude, longitude, label);
      case 'google':
        return await openGoogleMaps(latitude, longitude, label);
      case 'apple':
        return Platform.OS === 'ios' 
          ? openAppleMaps(latitude, longitude, label)
          : openGoogleMaps(latitude, longitude, label);
      default:
        return openGoogleMaps(latitude, longitude, label);
    }
  } catch (error) {
    console.error('Navigation Error:', error);
    Alert.alert('Navigation Error', 'Could not open navigation app. Please install Waze or Google Maps.');
    return false;
  }
}

/**
 * Open Waze navigation
 */
async function openWaze(latitude, longitude, label) {
  const wazeUrl = \waze://?ll=\,\&navigate=yes\;
  
  try {
    const canOpen = await Linking.canOpenURL(wazeUrl);
    if (canOpen) {
      await Linking.openURL(wazeUrl);
      return true;
    } else {
      console.warn('Waze not installed');
      return await openGoogleMaps(latitude, longitude, label);
    }
  } catch (error) {
    console.error('Waze Error:', error);
    return false;
  }
}

/**
 * Open Google Maps navigation
 */
async function openGoogleMaps(latitude, longitude, label) {
  let googleMapsUrl;
  
  if (Platform.OS === 'ios') {
    googleMapsUrl = \comgooglemaps://?daddr=\,\&directionsmode=driving\;
  } else {
    googleMapsUrl = \google.navigation:q=\,\\;
  }

  try {
    const canOpen = await Linking.canOpenURL(googleMapsUrl);
    if (canOpen) {
      await Linking.openURL(googleMapsUrl);
      return true;
    } else {
      const webUrl = \https://www.google.com/maps/dir/?api=1&destination=\,\&travelmode=driving\;
      await Linking.openURL(webUrl);
      return true;
    }
  } catch (error) {
    console.error('Google Maps Error:', error);
    return false;
  }
}

/**
 * Open Apple Maps navigation (iOS only)
 */
function openAppleMaps(latitude, longitude, label) {
  const mapsUrl = \maps://maps.apple.com/?daddr=\,\&dirflg=d\;
  
  try {
    Linking.openURL(mapsUrl);
    return true;
  } catch (error) {
    console.error('Apple Maps Error:', error);
    return false;
  }
}

/**
 * Check if navigation app is installed
 */
async function checkAppInstalled(app) {
  let url;
  
  switch (app.toLowerCase()) {
    case 'waze':
      url = Platform.OS === 'ios' ? 'waze://' : 'waze://';
      break;
    case 'google-maps':
      url = Platform.OS === 'ios' ? 'comgooglemaps://' : 'google.navigation://';
      break;
    case 'apple-maps':
      url = 'maps://';
      break;
    default:
      return false;
  }
  
  try {
    const canOpen = await Linking.canOpenURL(url);
    return canOpen;
  } catch (error) {
    return false;
  }
}

/**
 * Get available navigation apps on device
 */
export async function getAvailableNavApps() {
  const apps = [];
  
  if (await checkAppInstalled('waze')) apps.push('waze');
  if (await checkAppInstalled('google-maps')) apps.push('google');
  if (Platform.OS === 'ios' && await checkAppInstalled('apple-maps')) apps.push('apple');
  
  if (apps.length === 0) apps.push('web-fallback');
  
  return apps;
}

/**
 * Navigate with embedded parameters
 */
export async function shareLocation(latitude, longitude, label = 'My Location') {
  const message = \Location: \\nhttps://maps.google.com/?q=\,\\;
  try {
    await Linking.openURL(encodeURI(\sms:?body=\\));
  } catch (error) {
    console.error('Share Error:', error);
  }
}

export default {
  navigateTo,
  getAvailableNavApps,
  shareLocation,
};
