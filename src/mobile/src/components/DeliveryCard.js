import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

function statusColor(status) {
  switch (status) {
    case 'delivered': return '#4CAF50';
    case 'pending': return '#FF9800';
    case 'exception': return '#D32F2F';
    case 'loaded': return '#2196F3';
    default: return '#999';
  }
}

export default function DeliveryCard({ pkg, onPress }) {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <View style={styles.header}>
        <Text style={styles.pkgId} numberOfLines={1}>
          {pkg.id.length > 20 ? `${pkg.id.slice(0, 20)}...` : pkg.id}
        </Text>
        <View style={[styles.badge, { backgroundColor: statusColor(pkg.status) }]}>
          <Text style={styles.badgeText}>{pkg.status}</Text>
        </View>
      </View>
      <Text style={styles.address}>
        {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
      </Text>
      {pkg.predicted_eta_seconds && (
        <Text style={styles.eta}>
          ETA: {Math.round(pkg.predicted_eta_seconds / 60)} min
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  pkgId: {
    fontFamily: 'monospace',
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    marginLeft: 8,
  },
  badgeText: {
    color: 'white',
    fontSize: 11,
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  address: {
    fontSize: 13,
    color: '#666',
    marginBottom: 4,
  },
  eta: {
    fontSize: 12,
    color: '#2196F3',
    fontWeight: '500',
  },
});
