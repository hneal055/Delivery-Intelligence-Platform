import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  StatusBar,
  Platform,
  Switch,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { getSampleRoute, getRecentProofs } from '../api/client';
import {
  getEffectiveLocation,
  isDevMockGpsEnabled,
  updateDevMockGps,
  CHICAGO_DEPOT,
} from '../utils/location';

export default function ManifestScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stops, setStops] = useState([]);
  const [deliveredIds, setDeliveredIds] = useState(new Set());
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'PENDING' | 'DELIVERED'
  const [isOptimized, setIsOptimized] = useState(false);
  const [totalKm, setTotalKm] = useState(null);
  const [gpsStatus, setGpsStatus] = useState('Acquiring GPS...');
  const [devMockActive, setDevMockActive] = useState(false);

  const fetchRouteAndProofs = useCallback(async (overrideCoords = undefined) => {
    try {
      const mockEnabled = await isDevMockGpsEnabled();
      setDevMockActive(mockEnabled);

      let coords = null;
      if (overrideCoords !== undefined) {
        coords = overrideCoords;
        setGpsStatus(overrideCoords ? 'Chicago Sim (Dev Mode)' : 'Acquiring GPS...');
      } else {
        const effectiveLoc = await getEffectiveLocation();
        coords = effectiveLoc.coords;
        setGpsStatus(effectiveLoc.statusText);
      }

      // 1. Fetch completed proofs
      const proofs = await getRecentProofs(50);
      const deliveredSet = new Set(proofs.map((p) => p.package_id));
      setDeliveredIds(deliveredSet);

      // 2. Fetch sequenced stops
      const routeData = await getSampleRoute(
        'D001',
        coords ? coords.latitude : null,
        coords ? coords.longitude : null
      );

      setStops(routeData.ordered_stops || []);
      setIsOptimized(Boolean(routeData.optimized));
      setTotalKm(routeData.total_distance_km);
    } catch (err) {
      console.error('Error loading manifest:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchRouteAndProofs();
  }, [fetchRouteAndProofs]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      fetchRouteAndProofs();
    });
    return unsubscribe;
  }, [navigation, fetchRouteAndProofs]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchRouteAndProofs();
  };

  const handleToggleDevMock = async (newValue) => {
    // Optimistically update the UI switch immediately
    setDevMockActive(newValue);
    await updateDevMockGps(newValue);

    // Provide explicit coordinates based on the new switch state to prevent racing
    const targetCoords = newValue ? CHICAGO_DEPOT : null;
    await fetchRouteAndProofs(targetCoords);
  };

  const filteredStops = stops.filter((stop) => {
    const isDelivered = deliveredIds.has(stop.id);
    if (filter === 'PENDING') return !isDelivered;
    if (filter === 'DELIVERED') return isDelivered;
    return true;
  });

  const deliveredCount = stops.filter((s) => deliveredIds.has(s.id)).length;
  const pendingCount = stops.length - deliveredCount;

  const renderStopItem = ({ item, index }) => {
    const isDelivered = deliveredIds.has(item.id);

    return (
      <View style={[styles.stopCard, isDelivered && styles.deliveredCard]}>
        <View style={styles.cardHeader}>
          <View style={styles.sequenceBadge}>
            <Text style={styles.sequenceText}>#{item.sequence || index + 1}</Text>
          </View>
          <Text style={styles.packageIdText}>{item.id}</Text>
          <View
            style={[
              styles.statusPill,
              isDelivered ? styles.pillDelivered : styles.pillPending,
            ]}
          >
            <Text
              style={[
                styles.statusPillText,
                isDelivered ? styles.textDelivered : styles.textPending,
              ]}
            >
              {isDelivered ? 'DELIVERED' : 'PENDING'}
            </Text>
          </View>
        </View>

        <Text style={styles.addressText}>{item.address}</Text>

        <View style={styles.cardFooter}>
          <View style={styles.distanceContainer}>
            {item.distance_from_previous_km !== null &&
            item.distance_from_previous_km !== undefined ? (
              <Text style={styles.distanceText}>
                +{item.distance_from_previous_km} km leg ({item.total_distance_km} km total)
              </Text>
            ) : (
              <Text style={styles.coordsText}>
                {item.lat.toFixed(4)}, {item.lon.toFixed(4)}
              </Text>
            )}
          </View>

          {!isDelivered && (
            <TouchableOpacity
              style={styles.deliverButton}
              onPress={() =>
                navigation.navigate('Scanner', { packageId: item.id })
              }
            >
              <Text style={styles.deliverButtonText}>Deliver Stop</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <StatusBar barStyle="light-content" backgroundColor="#0f172a" />
        <ActivityIndicator size="large" color="#0284c7" />
        <Text style={styles.loadingText}>Sequencing route stops...</Text>
      </View>
    );
  }

  const calculatedTopPadding = Math.max(
    insets.top + 14,
    Platform.OS === 'android' ? (StatusBar.currentHeight || 24) + 18 : 26
  );

  return (
    <View style={[styles.container, { paddingTop: calculatedTopPadding }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" translucent={false} />

      {/* Top Header */}
      <View style={styles.headerContainer}>
        <View style={styles.titleRow}>
          <View>
            <Text style={styles.screenTitle}>Route Manifest</Text>
            <Text style={styles.driverSubtext}>Driver D001 • {pendingCount} stops remaining</Text>
          </View>
        </View>

        {/* Telemetry Status & Dev Mode Row */}
        <View style={styles.telemetryBar}>
          <View style={styles.telemetryStatusLeft}>
            <View style={[styles.statusDot, isOptimized ? styles.dotActive : styles.dotInactive]} />
            <Text style={styles.telemetryStatusText}>{gpsStatus}</Text>
          </View>
          {totalKm !== null && totalKm !== undefined && (
            <Text style={styles.totalDistanceText}>{totalKm} km estimated</Text>
          )}
        </View>

        {/* Dev Mock Toggle Bar */}
        <View style={styles.devBar}>
          <Text style={styles.devBarText}>Simulate Chicago Hub (Dev)</Text>
          <Switch
            value={devMockActive}
            onValueChange={handleToggleDevMock}
            trackColor={{ false: '#334155', true: '#0284c7' }}
            thumbColor={devMockActive ? '#38bdf8' : '#94a3b8'}
            style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
          />
        </View>
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterContainer}>
        <TouchableOpacity
          style={[styles.filterTab, filter === 'ALL' && styles.filterTabActive]}
          onPress={() => setFilter('ALL')}
        >
          <Text
            style={[styles.filterTabText, filter === 'ALL' && styles.filterTabTextActive]}
          >
            All ({stops.length})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterTab, filter === 'PENDING' && styles.filterTabActive]}
          onPress={() => setFilter('PENDING')}
        >
          <Text
            style={[
              styles.filterTabText,
              filter === 'PENDING' && styles.filterTabTextActive,
            ]}
          >
            Pending ({pendingCount})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterTab, filter === 'DELIVERED' && styles.filterTabActive]}
          onPress={() => setFilter('DELIVERED')}
        >
          <Text
            style={[
              styles.filterTabText,
              filter === 'DELIVERED' && styles.filterTabTextActive,
            ]}
          >
            Delivered ({deliveredCount})
          </Text>
        </TouchableOpacity>
      </View>

      {/* Manifest List */}
      <FlatList
        data={filteredStops}
        keyExtractor={(item) => item.id}
        renderItem={renderStopItem}
        contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 20 }]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#0284c7"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No stops matching filter.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#94a3b8',
    fontSize: 14,
  },
  headerContainer: {
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  screenTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: '#f8fafc',
    letterSpacing: -0.5,
  },
  driverSubtext: {
    fontSize: 13,
    color: '#94a3b8',
    marginTop: 2,
  },
  telemetryBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  telemetryStatusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotActive: {
    backgroundColor: '#22c55e',
  },
  dotInactive: {
    backgroundColor: '#f59e0b',
  },
  telemetryStatusText: {
    fontSize: 12,
    color: '#38bdf8',
    fontWeight: '600',
  },
  totalDistanceText: {
    fontSize: 12,
    color: '#22c55e',
    fontWeight: '700',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  devBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(30, 41, 59, 0.6)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 6,
    marginTop: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  devBarText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '500',
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 12,
    gap: 8,
  },
  filterTab: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 20,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  filterTabActive: {
    backgroundColor: '#0284c7',
    borderColor: '#0284c7',
  },
  filterTabText: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600',
  },
  filterTabTextActive: {
    color: '#ffffff',
  },
  listContent: {
    paddingHorizontal: 16,
    gap: 12,
  },
  stopCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  deliveredCard: {
    opacity: 0.6,
    borderColor: '#1e293b',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  sequenceBadge: {
    backgroundColor: '#0284c7',
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    marginRight: 8,
  },
  sequenceText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700',
  },
  packageIdText: {
    color: '#f8fafc',
    fontSize: 15,
    fontWeight: '700',
    flex: 1,
  },
  statusPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  pillPending: {
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
  },
  pillDelivered: {
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
  },
  statusPillText: {
    fontSize: 11,
    fontWeight: '700',
  },
  textPending: {
    color: '#f59e0b',
  },
  textDelivered: {
    color: '#22c55e',
  },
  addressText: {
    color: '#cbd5e1',
    fontSize: 14,
    marginBottom: 10,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  distanceContainer: {
    flex: 1,
  },
  distanceText: {
    color: '#38bdf8',
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: '600',
  },
  coordsText: {
    color: '#64748b',
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  deliverButton: {
    backgroundColor: '#0284c7',
    paddingVertical: 7,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  deliverButtonText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '600',
  },
  emptyContainer: {
    paddingTop: 40,
    alignItems: 'center',
  },
  emptyText: {
    color: '#64748b',
    fontSize: 14,
  },
});