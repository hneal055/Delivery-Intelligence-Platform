import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

const TRAFFIC_OPTIONS = [
  { label: 'Light', value: 0.1 },
  { label: 'Moderate', value: 0.5 },
  { label: 'Heavy', value: 0.9 },
];

const TrafficSelector = React.memo(function TrafficSelector({ traffic, onTrafficChange }) {
  return (
    <View>
      <Text style={styles.label}>Current Traffic Conditions:</Text>
      <View style={styles.row}>
        {TRAFFIC_OPTIONS.map((opt) => (
          <TouchableOpacity
            key={opt.value}
            style={[styles.btn, traffic === opt.value && styles.btnActive]}
            onPress={() => onTrafficChange(opt.value)}
          >
            <Text style={[styles.btnText, traffic === opt.value && styles.btnTextActive]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
});

export default TrafficSelector;

const styles = StyleSheet.create({
  label: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 10,
  },
  btn: {
    flex: 1,
    padding: 10,
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
    marginHorizontal: 2,
    borderRadius: 5,
  },
  btnActive: {
    backgroundColor: '#FF9800',
  },
  btnText: {
    color: '#333',
    fontSize: 12,
  },
  btnTextActive: {
    color: 'white',
    fontWeight: 'bold',
  },
});
