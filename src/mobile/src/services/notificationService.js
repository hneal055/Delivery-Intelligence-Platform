import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";
import client from "../api/client";

// Set foreground notification display behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync(driverId) {
  if (Platform.OS === "web") {
    console.log("[Push] Web push notifications skipped in browser mode.");
    return null;
  }

  if (!Device.isDevice) {
    console.log("[Push] Push notifications require a physical device.");
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.warn("[Push] Failed to get push token permission!");
    return null;
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    const token = tokenData.data;
    console.log("[Push] Expo Push Token obtained:", token);

    // Register token with FastAPI backend
    await client.post("/notifications/register-token", {
      driver_id: driverId,
      push_token: token,
    });

    return token;
  } catch (err) {
    console.warn("[Push] Error getting push token:", err?.response?.data || err.message);
    return null;
  }
}
