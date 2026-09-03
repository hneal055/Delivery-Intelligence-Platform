import React from "react";
import { StatusBar } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import HomeScreen from "./src/screens/HomeScreen";
import ManifestScreen from "./src/screens/ManifestScreen";
import ScannerScreen from "./src/screens/ScannerScreen";
import DeliveryHistoryScreen from "./src/screens/DeliveryHistoryScreen";

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />
      <NavigationContainer>
        <Tab.Navigator
          initialRouteName="HomeTab"
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
            name="HomeTab"
            component={HomeScreen}
            options={{
              tabBarLabel: "Home",
              tabBarIcon: ({ color, size }) => (
                <MaterialCommunityIcons name="view-dashboard-outline" color={color} size={size || 24} />
              ),
            }}
          />

          <Tab.Screen
            name="ManifestTab"
            component={ManifestScreen}
            options={{
              tabBarLabel: "Manifest",
              tabBarIcon: ({ color, size }) => (
                <MaterialCommunityIcons name="format-list-numbered" color={color} size={size || 24} />
              ),
            }}
          />

          <Tab.Screen
            name="Scanner"
            component={ScannerScreen}
            options={{
              tabBarLabel: "Scanner",
              tabBarIcon: ({ color, size }) => (
                <MaterialCommunityIcons name="barcode-scan" color={color} size={size || 24} />
              ),
            }}
          />

          <Tab.Screen
            name="HistoryTab"
            component={DeliveryHistoryScreen}
            options={{
              tabBarLabel: "Proofs",
              tabBarIcon: ({ color, size }) => (
                <MaterialCommunityIcons name="clipboard-check-outline" color={color} size={size || 24} />
              ),
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}