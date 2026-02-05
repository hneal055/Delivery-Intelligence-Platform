import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Text, Alert, ActivityIndicator } from 'react-native';
import axios from 'axios';

export default function LoginScreen({ onLogin, apiUrl }) {
  const [username, setUsername] = useState('driver1');
  const [password, setPassword] = useState('driverpassword');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      // OAuth2 expects form-urlencoded data
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      params.append('grant_type', 'password'); // Important for OAuth2 spec

      const response = await axios.post(`${apiUrl}/auth/token`, params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      if (response.data && response.data.access_token) {
        onLogin(response.data.access_token);
      } else {
        Alert.alert('Login Failed', 'No token received');
      }
    } catch (error) {
      console.log(error);
      Alert.alert('Login Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Driver Login</Text>
      <TextInput
        style={styles.input}
        placeholder='Username'
        value={username}
        onChangeText={setUsername}
        autoCapitalize='none'
      />
      <TextInput
        style={styles.input}
        placeholder='Password'
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      {loading ? (
        <ActivityIndicator size='large' color='#0000ff' />
      ) : (
        <Button title='Login' onPress={handleLogin} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  input: {
    height: 50,
    borderColor: '#ddd',
    borderWidth: 1,
    marginBottom: 15,
    paddingHorizontal: 10,
    borderRadius: 5,
  },
});
