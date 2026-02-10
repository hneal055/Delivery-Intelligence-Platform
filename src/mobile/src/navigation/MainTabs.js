import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text } from 'react-native';
import DeliveryListScreen from '../screens/DeliveryListScreen';
import DeliveryDetailScreen from '../screens/DeliveryDetailScreen';
import ProfileScreen from '../screens/ProfileScreen';

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
  return <Text style={{ fontSize: 20 }}>{icons[label] || '📋'}</Text>;
}

export default function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => <TabIcon label={route.name} focused={focused} />,
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: '#999',
      })}
    >
      <Tab.Screen
        name="Deliveries"
        component={DeliveryStackNavigator}
        options={{ title: 'Deliveries' }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ title: 'Profile' }}
      />
    </Tab.Navigator>
  );
}
