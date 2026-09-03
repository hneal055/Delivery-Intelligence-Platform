import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Linking,
  Alert,
  Modal,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import * as ScreenOrientation from 'expo-screen-orientation';
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
  const [driverCoords, setDriverCoords] = useState(null);

  const [showMap, setShowMap] = useState(true);
  const [isLandscapeModalOpen, setIsLandscapeModalOpen] = useState(false);

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

      setDriverCoords(coords);

      const proofs = await getRecentProofs(50).catch(() => []);
      const deliveredSet = new Set(proofs.map((p) => p.package_id));
      setDeliveredIds(deliveredSet);

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

  // Clean up orientation lock if unmounting
  useEffect(() => {
    return () => {
      ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP).catch(() => {});
    };
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchRouteAndProofs();
  };

  const handleToggleDevMock = async (newValue) => {
    setDevMockActive(newValue);
    await updateDevMockGps(newValue);
    const targetCoords = newValue ? CHICAGO_DEPOT : null;
    await fetchRouteAndProofs(targetCoords);
  };

  const openTurnByTurnNavigation = (item) => {
    const scheme = Platform.select({
      ios: `maps://app?daddr=${item.lat},${item.lon}&dirflg=d`,
      android: `google.navigation:q=${item.lat},${item.lon}&mode=d`,
    });

    const fallbackUrl = `https://www.google.com/maps/dir/?api=1&destination=${item.lat},${item.lon}&travelmode=driving`;

    Linking.canOpenURL(scheme)
      .then((supported) => {
        if (supported) {
          return Linking.openURL(scheme);
        } else {
          return Linking.openURL(fallbackUrl);
        }
      })
      .catch(() => {
        Alert.alert('Navigation Error', 'Could not open navigation application.');
      });
  };

  // Orientation handling
  const openLandscapeMap = async () => {
    try {
      await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE);
      setIsLandscapeModalOpen(true);
    } catch (e) {
      console.warn('Could not lock landscape orientation:', e);
      setIsLandscapeModalOpen(true);
    }
  };

  const closeLandscapeMap = async () => {
    try {
      await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP);
    } catch (e) {
      console.warn('Could not restore portrait orientation:', e);
    } finally {
      setIsLandscapeModalOpen(false);
    }
  };

  const filteredStops = stops.filter((stop) => {
    const isDelivered = deliveredIds.has(stop.id);
    if (filter === 'PENDING') return !isDelivered;
    if (filter === 'DELIVERED') return isDelivered;
    return true;
  });

  const deliveredCount = stops.filter((s) => deliveredIds.has(s.id)).length;
  const pendingCount = stops.length - deliveredCount;

  // Generate lightweight HTML Leaflet map payload
  const mapHtml = useMemo(() => {
    const center = driverCoords || CHICAGO_DEPOT;
    const markersData = stops.map((s, idx) => ({
      lat: s.lat,
      lon: s.lon,
      num: s.sequence || idx + 1,
      id: s.id,
      delivered: deliveredIds.has(s.id),
    }));

    const polyPoints = [];
    if (driverCoords) {
      polyPoints.push([driverCoords.latitude, driverCoords.longitude]);
    }
    stops.forEach((s) => {
      polyPoints.push([s.lat, s.lon]);
    });

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
          <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
          <style>
            html, body, #map { margin: 0; padding: 0; width: 100%; height: 100%; background: #0f172a; }
            .driver-pin {
              width: 18px; height: 18px; border-radius: 9px; background: #0284c7;
              border: 2px solid #ffffff; box-shadow: 0 0 8px #38bdf8;
            }
            .stop-pin {
              width: 24px; height: 24px; border-radius: 12px;
              color: #ffffff; font-size: 12px; font-weight: bold;
              display: flex; align-items: center; justify-content: center;
              border: 1.5px solid #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.5);
            }
            .pin-pending { background: #f59e0b; }
            .pin-delivered { background: #22c55e; opacity: 0.7; }
          </style>
        </head>
        <body>
          <div id="map"></div>
          <script>
            var map = L.map('map', { zoomControl: true, attributionControl: false }).setView([${center.latitude}, ${center.longitude}], 14);

            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
              maxZoom: 19
            }).addTo(map);

            var polyPoints = ${JSON.stringify(polyPoints)};
            if (polyPoints.length > 1) {
              L.polyline(polyPoints, { color: '#0284c7', weight: 4, dashArray: '6, 6' }).addTo(map);
            }

            ${
              driverCoords
                ? `
              var driverIcon = L.divIcon({ className: 'driver-pin', iconSize: [18, 18], iconAnchor: [9, 9] });
              L.marker([${driverCoords.latitude}, ${driverCoords.longitude}], { icon: driverIcon }).addTo(map);
            `
                : ''
            }

            var markers = ${JSON.stringify(markersData)};
            var bounds = [];
            ${driverCoords ? `bounds.push([${driverCoords.latitude}, ${driverCoords.longitude}]);` : ''}

            markers.forEach(function(m) {
              bounds.push([m.lat, m.lon]);
              var colorClass = m.delivered ? 'pin-delivered' : 'pin-pending';
              var html = '<div class="stop-pin ' + colorClass + '">' + m.num + '</div>';
              var icon = L.divIcon({ html: html, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });
              L.marker([m.lat, m.lon], { icon: icon }).addTo(map);
            });

            if (bounds.length > 0) {
              map.fitBounds(bounds, { padding: [30, 30] });
            }

            window.addEventListener('resize', function() {
              map.invalidateSize();
            });
          </script>
        </body>
      </html>
    `;
  }, [stops, deliveredIds, driverCoords]);

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

          <View style={styles.buttonGroup}>
            <TouchableOpacity
              style={styles.navButton}
              onPress={() => openTurnByTurnNavigation(item)}
            >
              <Text style={styles.navButtonText}>Directions</Text>
            </TouchableOpacity>

            {!isDelivered && (
              <TouchableOpacity
                style={styles.deliverButton}
                onPress={() => navigation.navigate('Scanner', { packageId: item.id })}
              >
                <Text style={styles.deliverButtonText}>Deliver</Text>
              </TouchableOpacity>
            )}
          </View>
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

        {/* Telemetry Status Bar */}
        <View style={styles.telemetryBar}>
          <View style={styles.telemetryStatusLeft}>
            <View style={[styles.statusDot, isOptimized ? styles.dotActive : styles.dotInactive]} />
            <Text style={styles.telemetryStatusText}>{gpsStatus}</Text>
          </View>
          {totalKm !== null && totalKm !== undefined && (
            <Text style={styles.totalDistanceText}>{totalKm} km estimated</Text>
          )}
        </View>

        {/* Dev Mock Toggle */}
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

      {/* Portrait Map Preview */}
      {showMap ? (
        <View style={styles.mapWrapper}>
          <WebView
            key={`map_portrait_${stops.length}_${devMockActive}`}
            originWhitelist={['*']}
            source={{ html: mapHtml }}
            style={styles.mapWebview}
            scrollEnabled={false}
          />

          {/* Map Controls: Fullscreen Landscape + Hide */}
          <View style={styles.floatingControlsGroup}>
            <TouchableOpacity
              style={styles.floatingControlBtn}
              onPress={openLandscapeMap}
              activeOpacity={0.8}
            >
              <Text style={styles.floatingControlText}>⛶ Landscape</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.floatingControlBtn}
              onPress={() => setShowMap(false)}
              activeOpacity={0.8}
            >
              <Text style={styles.floatingControlText}>Hide</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <TouchableOpacity
          style={styles.expandMapBar}
          onPress={() => setShowMap(true)}
          activeOpacity={0.8}
        >
          <Text style={styles.expandMapBarText}>🗺️ Show Route Map</Text>
        </TouchableOpacity>
      )}

      {/* Filter Tabs */}
      <View style={styles.filterContainer}>
        <TouchableOpacity
          style={[styles.filterTab, filter === 'ALL' && styles.filterTabActive]}
          onPress={() => setFilter('ALL')}
        >
          <Text style={[styles.filterTabText, filter === 'ALL' && styles.filterTabTextActive]}>
            All ({stops.length})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterTab, filter === 'PENDING' && styles.filterTabActive]}
          onPress={() => setFilter('PENDING')}
        >
          <Text
            style={[styles.filterTabText, filter === 'PENDING' && styles.filterTabTextActive]}
          >
            Pending ({pendingCount})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterTab, filter === 'DELIVERED' && styles.filterTabActive]}
          onPress={() => setFilter('DELIVERED')}
        >
          <Text
            style={[styles.filterTabText, filter === 'DELIVERED' && styles.filterTabTextActive]}
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
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#0284c7" />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No stops matching filter.</Text>
          </View>
        }
      />

      {/* Dedicated Edge-to-Edge Fullscreen Landscape Modal */}
      <Modal
        visible={isLandscapeModalOpen}
        animationType="fade"
        supportedOrientations={['landscape', 'landscape-left', 'landscape-right']}
        onRequestClose={closeLandscapeMap}
      >
        <View style={styles.fullscreenModalContainer}>
          <StatusBar hidden={true} />
          <WebView
            key={`map_landscape_${stops.length}_${devMockActive}`}
            originWhitelist={['*']}
            source={{ html: mapHtml }}
            style={styles.fullscreenWebview}
            scrollEnabled={true}
          />

          {/* Close / Return to Portrait Button */}
          <TouchableOpacity
            style={styles.closeLandscapeBtn}
            onPress={closeLandscapeMap}
            activeOpacity={0.8}
          >
            <Text style={styles.closeLandscapeBtnText}>✕ Exit Landscape</Text>
          </TouchableOpacity>
        </View>
      </Modal>
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
    paddingBottom: 8,
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
    paddingVertical: 7,
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
  mapWrapper: {
    height: 200,
    marginHorizontal: 16,
    marginBottom: 10,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#334155',
    position: 'relative',
    backgroundColor: '#0f172a',
  },
  mapWebview: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  floatingControlsGroup: {
    position: 'absolute',
    top: 8,
    right: 8,
    flexDirection: 'row',
    gap: 6,
    zIndex: 10,
  },
  floatingControlBtn: {
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    paddingVertical: 5,
    paddingHorizontal: 9,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  floatingControlText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '700',
  },
  expandMapBar: {
    marginHorizontal: 16,
    marginBottom: 10,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  expandMapBarText: {
    color: '#38bdf8',
    fontSize: 12,
    fontWeight: '600',
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 10,
    gap: 8,
  },
  filterTab: {
    paddingVertical: 5,
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
    gap: 10,
  },
  stopCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 12,
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
    fontSize: 13,
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 2,
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
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
  },
  navButton: {
    backgroundColor: '#334155',
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  navButtonText: {
    color: '#e2e8f0',
    fontSize: 12,
    fontWeight: '600',
  },
  deliverButton: {
    backgroundColor: '#0284c7',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  deliverButtonText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  emptyContainer: {
    paddingTop: 30,
    alignItems: 'center',
  },
  emptyText: {
    color: '#64748b',
    fontSize: 14,
  },
  // Fullscreen Landscape Styles
  fullscreenModalContainer: {
    flex: 1,
    backgroundColor: '#0f172a',
    position: 'relative',
  },
  fullscreenWebview: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  closeLandscapeBtn: {
    position: 'absolute',
    top: 16,
    right: 20,
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    borderWidth: 1,
    borderColor: '#38bdf8',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
    zIndex: 20,
  },
  closeLandscapeBtnText: {
    color: '#f8fafc',
    fontSize: 12,
    fontWeight: '700',
  },
});