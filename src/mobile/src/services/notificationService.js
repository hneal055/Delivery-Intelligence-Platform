import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { Platform } from "react-native";
import { registerDevice } from "../api/client";

/**
 * Alerts for new assignments and ready pickups come two ways:
 *  - push from the server (works when the app is in the background), and
 *  - the in-app watcher polling every 30 s (works in Expo Go everywhere).
 * Both report through here, keyed "kind:packageId", so the driver gets one
 * alert per event.
 */
const alerted = new Set();

export function markAlerted(kind, packageId) {
  alerted.add(`${kind}:${packageId}`);
}

export async function showLocalAlert(kind, packageId, title, body) {
  const key = `${kind}:${packageId}`;
  if (alerted.has(key)) return;
  alerted.add(key);
  try {
    await Notifications.scheduleNotificationAsync({
      content: { title, body, data: { kind, package_id: packageId }, sound: "default" },
      trigger: null,
    });
  } catch (err) {
    console.warn("[Alerts] Could not show notification:", err.message);
  }
}

/**
 * Ask for notification permission and register this phone's Expo push
 * token with the backend. Safe to call on every login; failures (no
 * permission, simulator, Expo Go limits) only disable push -- the in-app
 * watcher still alerts while the app is open.
 */
export async function registerForPushNotificationsAsync() {
  if (Platform.OS === "web") return null;
  try {
    let { status } = await Notifications.getPermissionsAsync();
    if (status !== "granted") {
      ({ status } = await Notifications.requestPermissionsAsync());
    }
    if (status !== "granted") {
      console.warn("[Push] Notification permission not granted");
      return null;
    }

    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
    await registerDevice(token, Platform.OS);
    console.log("[Push] Registered for assignment alerts");
    return token;
  } catch (err) {
    console.warn("[Push] Push unavailable, using in-app alerts only:", err.message);
    return null;
  }
}
