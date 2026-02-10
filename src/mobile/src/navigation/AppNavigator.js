import React from 'react';
import { useAuthStore } from '../stores/authStore';
import AuthStack from './AuthStack';
import MainTabs from './MainTabs';

export default function AppNavigator() {
  const token = useAuthStore((s) => s.token);

  if (!token) {
    return <AuthStack />;
  }

  return <MainTabs />;
}
