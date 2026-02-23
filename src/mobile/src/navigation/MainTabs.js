import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text, View, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DeliveryListScreen from '../screens/DeliveryListScreen';
import DeliveryDetailScreen from '../screens/DeliveryDetailScreen';
import ProfileScreen from '../screens/ProfileScreen';
import { useTracking } from '../hooks/useTracking';

const Tab = createBottomTabNavigator();
const DeliveryStack = createNativeStackNavigator();

function DeliveryStackNavigator() {
  return (
    <DeliveryStack.Navigator>
      <DeliveryStack.Screen
        name="DeliveryList"
        component={DeliveryListScreen}
        options={{ title: 'My Deliveries' }}
      />
      <DeliveryStack.Screen
        name="DeliveryDetail"
        component={DeliveryDetailScreen}
        options={{ title: 'Delivery Details' }}
      />
    </DeliveryStack.Navigator>
  );
}

function TabIcon({ label, focused }) {
  const icons = {
    Deliveries: focused ? '📦' : '📋',
    Profile: focused ? '👤' : '⚙️',
  };
  return <Text style={{ fontSize: 24 }}>{icons[label] || '❓'}</Text>;
}

export default function MainTabs() {
  // Start tracking location when main tabs are mounted (user is logged in)
  const { status } = useTracking();
  // Respect the iPhone 17 home indicator / Dynamic Island safe area
  const insets = useSafeAreaInsets();
  const tabBarHeight = Platform.OS === 'ios' ? 50 + insets.bottom : 60;

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => <TabIcon label={route.name} focused={focused} />,
        tabBarActiveTintColor: '#0066cc',
        tabBarInactiveTintColor: '#999',
        tabBarStyle: {
          height: tabBarHeight,
          paddingTop: 6,
          paddingBottom: insets.bottom > 0 ? insets.bottom : 6,
        },
        tabBarLabelStyle: {
          fontSize: 12,
        },
      })}
    >
      <Tab.Screen
        name="Deliveries"
        component={DeliveryStackNavigator}
        options={{ 
          title: 'Deliveries',
          tabBarLabel: 'Deliveries'
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ 
          title: 'Profile',
          tabBarLabel: 'Profile'
        }}
      />
    </Tab.Navigator>
  );
}
