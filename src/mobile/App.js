import React, { Component, useEffect } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer, DarkTheme, createNavigationContainerRef } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as Notifications from "expo-notifications";

import HomeScreen from "./src/screens/HomeScreen";
import ManifestScreen from "./src/screens/ManifestScreen";
import ScannerScreen from "./src/screens/ScannerScreen";
import DeliveryHistoryScreen from "./src/screens/DeliveryHistoryScreen";
import LoginScreen from "./src/screens/LoginScreen";
import { useAuthStore } from "./src/stores/authStore";
import { useAssignmentWatcher } from "./src/hooks/useAssignmentWatcher";
import { useLocationReporter } from "./src/hooks/useLocationReporter";
import {
  markAlerted,
  registerForPushNotificationsAsync,
} from "./src/services/notificationService";

const navigationRef = createNavigationContainerRef();

const Tab = createBottomTabNavigator();

// ── Error Boundary ───────────────────────────────────────────────────────────
// Prevents one render crash from killing the whole app on field hardware.
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // TODO: report to your observability stack (Sentry / OTel)
    console.error("App crashed:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.fallback}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color="#f87171" />
          <ActivityIndicator color="#38bdf8" style={{ marginTop: 16 }} />
        </View>
      );
    }
    return this.props.children;
  }
}

// ── Notification Setup ───────────────────────────────────────────────────────
// Must run once at app root so POST_NOTIFICATIONS (Android 13+) and pushes work.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

function useNotificationListeners() {
  useEffect(() => {
    const subReceived = Notifications.addNotificationReceivedListener((n) => {
      // A server push for this event: the in-app watcher must not repeat it
      const { kind, package_id: packageId } = n.request.content.data || {};
      if (kind && packageId) markAlerted(kind, packageId);
    });
    const subResponse = Notifications.addNotificationResponseReceivedListener(() => {
      // Assignment / ready alerts open the driver's stop list
      if (navigationRef.isReady()) navigationRef.navigate("Manifest");
    });
    return () => {
      subReceived.remove();
      subResponse.remove();
    };
  }, []);
}

// ── Deep Linking ─────────────────────────────────────────────────────────────
const linking = {
  prefixes: ["deliveryintel://"],
  config: {
    screens: {
      Home: "home",
      Manifest: "manifest",
      Scanner: "scan",
      Proofs: "proofs",
    },
  },
};

// ── Tab Navigator ────────────────────────────────────────────────────────────
function AppTabs() {
  return (
    <Tab.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#0f172a",
          borderTopColor: "#1e293b",
          borderTopWidth: 1,
          height: 62,
          paddingBottom: 8,
          paddingTop: 6,
        },
        tabBarActiveTintColor: "#38bdf8",
        tabBarInactiveTintColor: "#64748b",
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarLabel: "Home",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="view-dashboard-outline" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Manifest"
        component={ManifestScreen}
        options={{
          tabBarLabel: "Manifest",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="format-list-numbered" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Scanner"
        component={ScannerScreen}
        options={{
          tabBarLabel: "Scanner",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="barcode-scan" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Proofs"
        component={DeliveryHistoryScreen}
        options={{
          tabBarLabel: "Proofs",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="clipboard-check-outline" color={color} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────
function Root() {
  // Same store LoginScreen writes to, so a successful login shows the app.
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s._hasHydrated);
  const driverId = useAuthStore((s) => s.driverId);
  useNotificationListeners();
  useAssignmentWatcher(Boolean(token));
  useLocationReporter(token ? driverId : null);

  // Register this phone for assignment alerts once per login
  useEffect(() => {
    if (token) registerForPushNotificationsAsync();
  }, [token]);

  if (!hydrated) {
    return (
      <View style={styles.fallback}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef} theme={DarkTheme} linking={linking}>
      {token ? <AppTabs /> : <LoginScreen />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <SafeAreaProvider>
        <StatusBar style="light" backgroundColor="#0f172a" />
        <Root />
      </SafeAreaProvider>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  fallback: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
  },
});