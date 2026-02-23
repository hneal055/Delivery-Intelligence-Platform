import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text, View, Platform, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DeliveryListScreen from '../screens/DeliveryListScreen';
import DeliveryDetailScreen from '../screens/DeliveryDetailScreen';
import ProfileScreen from '../screens/ProfileScreen';
import { useTracking } from '../hooks/useTracking';

const Tab = createBottomTabNavigator();
const DeliveryStack = createNativeStackNavigator();

const styles = StyleSheet.create({
  statusBar: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  statusConnected: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
  },
  statusConnecting: {
    backgroundColor: '#fff3e0',
    color: '#e65100',
  },
  statusDisconnected: {
    backgroundColor: '#ffebee',
    color: '#c62828',
  },
  statusNoPermission: {
    backgroundColor: '#f3e5f5',
    color: '#6a1b9a',
  },
});

function StatusIndicator({ status, permissionStatus }) {
  let displayText = '';
  let statusStyle = styles.statusDisconnected;

  switch (status) {
    case 'connected':
      if (permissionStatus === 'denied') {
        displayText = '⚠️ No GPS Permission';
        statusStyle = styles.statusNoPermission;
      } else {
        displayText = '✓ Location Tracking Active';
        statusStyle = styles.statusConnected;
      }
      break;
    case 'connecting':
      displayText = '⟳ Connecting...';
      statusStyle = styles.statusConnecting;
      break;
    case 'disconnected':
      displayText = '⊘ Offline (will reconnect)';
      statusStyle = styles.statusDisconnected;
      break;
    case 'no-permission':
      displayText = '⚠️ GPS Permission Required';
      statusStyle = styles.statusNoPermission;
      break;
    case 'no-auth':
      displayText = '⊘ Not Authenticated';
      statusStyle = styles.statusDisconnected;
      break;
    case 'failed':
      displayText = '✕ Connection Failed';
      statusStyle = styles.statusDisconnected;
      break;
    default:
      return null;
  }

  return (
    <View style={[styles.statusBar, statusStyle]}>
      <Text style={[styles.statusText, { color: statusStyle.color }]}>
        {displayText}
      </Text>
    </View>
  );
}

function DeliveryStackNavigator({ trackingStatus, permissionStatus }) {
  return (
    <View style={{ flex: 1 }}>
      <StatusIndicator status={trackingStatus} permissionStatus={permissionStatus} />
      <DeliveryStack.Navigator screenOptions={{ headerShown: true }}>
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
    </View>
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
  const { status, permissionStatus } = useTracking();
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
        component={() => (
          <DeliveryStackNavigator 
            trackingStatus={status} 
            permissionStatus={permissionStatus}
          />
        )}
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

