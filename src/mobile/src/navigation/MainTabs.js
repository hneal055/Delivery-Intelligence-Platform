import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text, View } from 'react-native';
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

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => <TabIcon label={route.name} focused={focused} />,
        tabBarActiveTintColor: '#0066cc',
        tabBarInactiveTintColor: '#999',
        tabBarStyle: {
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          paddingBottom: 5,
        }
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
