import React, { Component, useEffect, useState, createContext, useContext } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer, DarkTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as SecureStore from "expo-secure-store";
import * as Notifications from "expo-notifications";

// ── Screens ──────────────────────────────────────────────────────────────────
// NOTE: adjust these paths to match your actual layout.
// If App.js lives in src/mobile/, the screens are ./screens/*
import HomeScreen from "./screens/HomeScreen";
import ManifestScreen from "./screens/ManifestScreen";
import ScannerScreen from "./screens/ScannerScreen";
import DeliveryHistoryScreen from "./screens/DeliveryHistoryScreen";
import LoginScreen from "./screens/LoginScreen";

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

// ── Auth Context ─────────────────────────────────────────────────────────────
const AuthContext = createContext(null);

const TOKEN_KEY = "dip_access_token";

function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    SecureStore.getItemAsync(TOKEN_KEY)
      .then(setToken)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const signIn = async (newToken) => {
    await SecureStore.setItemAsync(TOKEN_KEY, newToken);
    setToken(newToken);
  };

  const signOut = async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, signIn, signOut, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
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
      // TODO: route assignment notifications to the Manifest screen refresh
      console.log("Notification received:", n.request.content.data);
    });
    const subResponse = Notifications.addNotificationResponseReceivedListener((r) => {
      // TODO: deep-link into the delivery detail from the notification payload
      console.log("Notification tapped:", r.notification.request.content.data);
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
  const { token, loading } = useAuth();
  useNotificationListeners();

  if (loading) {
    return (
      <View style={styles.fallback}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <NavigationContainer theme={DarkTheme} linking={linking}>
      {token ? <AppTabs /> : <LoginScreen />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <SafeAreaProvider>
        <StatusBar style="light" backgroundColor="#0f172a" />
        <AuthProvider>
          <Root />
        </AuthProvider>
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