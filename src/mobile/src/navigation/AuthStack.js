import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import LoginScreen from '../screens/LoginScreen';
import { useAuthStore } from '../stores/authStore';

const Stack = createNativeStackNavigator();

export default function AuthStack() {
  const login = useAuthStore((s) => s.login);

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login">
        {(props) => (
          <LoginScreen
            {...props}
            onLogin={(token) => login(token, null)}
          />
        )}
      </Stack.Screen>
    </Stack.Navigator>
  );
}
