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
  const etaMinutes = pkg.predicted_eta_seconds ? Math.round(pkg.predicted_eta_seconds / 60) : null;

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <Text style={styles.pkgId}>#{pkg.id.slice(-6)}</Text>
        <View style={[styles.badge, { backgroundColor: statusColor(pkg.status) }]}>
          <Text style={styles.badgeText}>{pkg.status.toUpperCase()}</Text>
        </View>
      </View>
      
      <View style={styles.divider} />
      
      <View style={styles.body}>
        <Text style={styles.addressLabel}>Destination:</Text>
        <Text style={styles.address} numberOfLines={2}>
          {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
        </Text>
        
        {etaMinutes !== null && (
          <View style={styles.etaContainer}>
            <Text style={styles.etaLabel}>Est. Arrival:</Text>
            <Text style={styles.etaValue}>{etaMinutes} min</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    marginBottom: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    borderWidth: 1,
    borderColor: '#f0f0f0',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  pkgId: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  divider: {
    height: 1,
    backgroundColor: '#eee',
    marginBottom: 12,
  },
  body: {
    gap: 4,
  },
  addressLabel: {
    fontSize: 12,
    color: '#888',
    fontWeight: '600',
  },
  address: {
    fontSize: 15,
    color: '#444',
    marginBottom: 8,
    lineHeight: 22,
  },
  etaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  etaLabel: {
    fontSize: 12,
    color: '#888',
    marginRight: 6,
  },
  etaValue: {
    fontSize: 14,
    color: '#0066cc',
    fontWeight: '600',
  },
});
