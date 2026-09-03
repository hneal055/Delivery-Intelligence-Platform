import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  StatusBar,
  Platform,
  Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { getRecentProofs, resetDatabase, BASE_URL } from '../api/client';

export default function DeliveryHistoryScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [proofs, setProofs] = useState([]);
  const [resetting, setResetting] = useState(false);

  const fetchProofs = useCallback(async () => {
    try {
      const data = await getRecentProofs(50);
      setProofs(data || []);
    } catch (err) {
      console.error('Error fetching proofs history:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchProofs();
  }, [fetchProofs]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      fetchProofs();
    });
    return unsubscribe;
  }, [navigation, fetchProofs]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchProofs();
  };

  const handleReset = () => {
    Alert.alert(
      'Reset Proof Database',
      'This will delete all proof records and photo storage on the backend. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset All',
          style: 'destructive',
          onPress: async () => {
            try {
              setResetting(true);
              await resetDatabase();
              await fetchProofs();
              Alert.alert('Success', 'Database and stored photos cleared.');
            } catch (err) {
              Alert.alert('Reset Failed', err.message || 'Could not reset backend state.');
            } finally {
              setResetting(false);
            }
          },
        },
      ]
    );
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return 'Unknown Time';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const renderProofItem = ({ item }) => {
    const photoFullUrl = item.photo_url ? `${BASE_URL}${item.photo_url}` : null;

    return (
      <View style={styles.proofCard}>
        <View style={styles.cardHeader}>
          <View style={styles.headerLeft}>
            <Text style={styles.packageIdText}>{item.package_id}</Text>
            <Text style={styles.driverTag}>Driver {item.driver_id || 'D001'}</Text>
          </View>
          <View style={styles.statusBadge}>
            <Text style={styles.statusBadgeText}>{item.status}</Text>
          </View>
        </View>

        <View style={styles.cardBody}>
          {photoFullUrl ? (
            <Image
              source={{ uri: photoFullUrl }}
              style={styles.proofThumbnail}
              resizeMode="cover"
            />
          ) : (
            <View style={styles.noPhotoPlaceholder}>
              <Text style={styles.noPhotoText}>No Photo</Text>
            </View>
          )}

          <View style={styles.metaContainer}>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Timestamp:</Text>
              <Text style={styles.metaValue}>{formatTimestamp(item.timestamp)}</Text>
            </View>

            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Latitude:</Text>
              <Text style={styles.coordValue}>
                {item.dest_lat !== null && item.dest_lat !== undefined
                  ? Number(item.dest_lat).toFixed(5)
                  : 'N/A'}
              </Text>
            </View>

            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Longitude:</Text>
              <Text style={styles.coordValue}>
                {item.dest_lon !== null && item.dest_lon !== undefined
                  ? Number(item.dest_lon).toFixed(5)
                  : 'N/A'}
              </Text>
            </View>

            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Record ID:</Text>
              <Text style={styles.metaValue}>#{item.id}</Text>
            </View>
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
        <Text style={styles.loadingText}>Loading proof history...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: Math.max(insets.top, 16) }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* Header */}
      <View style={styles.headerContainer}>
        <View style={styles.titleRow}>
          <View>
            <Text style={styles.screenTitle}>Proof History</Text>
            <Text style={styles.subtext}>
              {proofs.length} {proofs.length === 1 ? 'record' : 'records'} logged to SQLite
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.resetButton, resetting && styles.resetButtonDisabled]}
            onPress={handleReset}
            disabled={resetting}
          >
            {resetting ? (
              <ActivityIndicator size="small" color="#f87171" />
            ) : (
              <Text style={styles.resetButtonText}>Clear DB</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {/* Proof List */}
      <FlatList
        data={proofs}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderProofItem}
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
            <Text style={styles.emptyTitle}>No Proofs Found</Text>
            <Text style={styles.emptySubtitle}>
              Deliver a stop in the Scanner screen to generate records.
            </Text>
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
    paddingTop: 8,
    paddingBottom: 12,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  screenTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#f8fafc',
    letterSpacing: -0.5,
  },
  subtext: {
    fontSize: 13,
    color: '#94a3b8',
    marginTop: 2,
  },
  resetButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#7f1d1d',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  resetButtonDisabled: {
    opacity: 0.5,
  },
  resetButtonText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '700',
  },
  listContent: {
    paddingHorizontal: 16,
    gap: 12,
  },
  proofCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
    paddingBottom: 8,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  packageIdText: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '700',
  },
  driverTag: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '500',
  },
  statusBadge: {
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  statusBadgeText: {
    color: '#22c55e',
    fontSize: 11,
    fontWeight: '700',
  },
  cardBody: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
  },
  proofThumbnail: {
    width: 90,
    height: 90,
    borderRadius: 8,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#475569',
  },
  noPhotoPlaceholder: {
    width: 90,
    height: 90,
    borderRadius: 8,
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  noPhotoText: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '600',
  },
  metaContainer: {
    flex: 1,
    gap: 4,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  metaLabel: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '500',
  },
  metaValue: {
    color: '#f1f5f9',
    fontSize: 12,
    fontWeight: '600',
  },
  coordValue: {
    color: '#38bdf8',
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: '600',
  },
  emptyContainer: {
    paddingTop: 60,
    alignItems: 'center',
    gap: 6,
  },
  emptyTitle: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '700',
  },
  emptySubtitle: {
    color: '#64748b',
    fontSize: 13,
    textAlign: 'center',
    maxWidth: 240,
  },
});