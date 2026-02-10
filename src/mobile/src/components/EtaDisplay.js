import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function EtaDisplay({ eta }) {
  if (!eta) {
    return (
      <View style={styles.container}>
        <Text style={styles.calculating}>Calculating Route...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Estimated Arrival</Text>
      <Text style={styles.value}>
        {eta} <Text style={styles.unit}>min</Text>
      </Text>
      <Text style={styles.note}>(ML Model Confidence: High)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginVertical: 15,
    backgroundColor: '#E3F2FD',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#2196F3',
  },
  label: {
    color: '#1976D2',
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#0D47A1',
  },
  unit: {
    fontSize: 20,
  },
  note: {
    fontSize: 12,
    color: '#555',
    marginTop: 5,
  },
  calculating: {
    textAlign: 'center',
    color: '#666',
    fontSize: 14,
  },
});
