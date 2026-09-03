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
import Svg, { Path } from 'react-native-svg';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { getRecentProofs, resetDatabase, BASE_URL } from '../api/client';
import { getOfflineQueue, syncOfflineQueue } from '../utils/offlineQueue';

export default function DeliveryHistoryScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [proofs, setProofs] = useState([]);
  const [resetting, setResetting] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Offline queue state
  const [offlineCount, setOfflineCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  const fetchProofsAndQueue = useCallback(async () => {
    try {
      const [data, queue] = await Promise.all([
        getRecentProofs(50).catch(() => []),
        getOfflineQueue().catch(() => []),
      ]);
      setProofs(data || []);
      setOfflineCount(queue.length);
    } catch (err) {
      console.error('Error fetching proofs history:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchProofsAndQueue();
  }, [fetchProofsAndQueue]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      fetchProofsAndQueue();
    });
    return unsubscribe;
  }, [navigation, fetchProofsAndQueue]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchProofsAndQueue();
  };

  const handleSyncQueue = async () => {
    if (offlineCount === 0 || isSyncing) return;
    setIsSyncing(true);
    try {
      const { syncedCount, remainingCount } = await syncOfflineQueue();
      await fetchProofsAndQueue();

      if (remainingCount === 0) {
        Alert.alert('Sync Complete', `Successfully synced ${syncedCount} queued delivery records.`);
      } else {
        Alert.alert(
          'Partial Sync',
          `Synced ${syncedCount} records. ${remainingCount} remain queued (check network).`
        );
      }
    } catch (err) {
      Alert.alert('Sync Error', err.message || 'Could not reach server to sync queue.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleReset = () => {
    Alert.alert(
      'Reset Proof Database',
      'This will delete all delivery proof records and clear photo storage on the backend. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset All',
          style: 'destructive',
          onPress: async () => {
            try {
              setResetting(true);
              await resetDatabase();
              await fetchProofsAndQueue();
              Alert.alert('Success', 'Database and stored delivery proofs cleared.');
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

  const downloadAndShareExport = async (format) => {
    try {
      setExporting(true);
      const isSharingAvailable = await Sharing.isAvailableAsync();
      if (!isSharingAvailable) {
        Alert.alert('Sharing Unavailable', 'Sharing files is not supported on this device.');
        return;
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `delivery_proofs_${timestamp}.${format}`;
      const fileUri = `${FileSystem.cacheDirectory}${filename}`;

      const downloadUrl = `${BASE_URL}/delivery/export?format=${format}`;
      const downloadResult = await FileSystem.downloadAsync(downloadUrl, fileUri);

      if (downloadResult.status !== 200) {
        throw new Error(`Download failed with status ${downloadResult.status}`);
      }

      await Sharing.shareAsync(downloadResult.uri, {
        mimeType: format === 'csv' ? 'text/csv' : 'application/json',
        dialogTitle: `Export Delivery Proofs (${format.toUpperCase()})`,
        UTI: format === 'csv' ? 'public.comma-separated-values-text' : 'public.json',
      });
    } catch (err) {
      Alert.alert('Export Error', err.message || 'Failed to export delivery report.');
    } finally {
      setExporting(false);
    }
  };

  const handleExportPress = () => {
    if (proofs.length === 0) {
      Alert.alert('No Data', 'There are no delivery proofs available to export.');
      return;
    }

    Alert.alert('Export Delivery Proofs', 'Select your preferred export report format:', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'CSV (.csv)', onPress: () => downloadAndShareExport('csv') },
      { text: 'JSON (.json)', onPress: () => downloadAndShareExport('json') },
    ]);
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
        {/* Card Header */}
        <View style={styles.cardHeader}>
          <View style={styles.headerLeft}>
            <Text style={styles.packageIdText}>{item.package_id}</Text>
            <Text style={styles.driverTag}>Driver {item.driver_id || 'D001'}</Text>
          </View>
          <View style={styles.statusBadge}>
            <Text style={styles.statusBadgeText}>{item.status}</Text>
          </View>
        </View>

        {/* Content Section */}
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

        {/* Signature Vector Preview */}
        {item.signature_path ? (
          <View style={styles.signaturePreviewWrapper}>
            <Text style={styles.signaturePreviewLabel}>Customer Signature:</Text>
            <View style={styles.signatureMiniCanvas}>
              <Svg style={StyleSheet.absoluteFill} viewBox="0 0 320 100">
                {item.signature_path.split(/(?=M)/).map((segment, idx) => (
                  <Path
                    key={idx}
                    d={segment.trim()}
                    stroke="#38bdf8"
                    strokeWidth={2.5}
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                ))}
              </Svg>
            </View>
          </View>
        ) : null}
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

  const calculatedTopPadding = Math.max(
    insets.top + 18,
    Platform.OS === 'android' ? (StatusBar.currentHeight || 24) + 24 : 32
  );

  return (
    <View style={[styles.container, { paddingTop: calculatedTopPadding }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" translucent={false} />

      {/* Header */}
      <View style={styles.headerContainer}>
        <View style={styles.titleRow}>
          <Text style={styles.screenTitle}>Proof History</Text>
        </View>

        <View style={styles.subHeaderRow}>
          <Text style={styles.subtext}>
            {proofs.length} {proofs.length === 1 ? 'record' : 'records'} logged
          </Text>

          <View style={styles.headerButtons}>
            <TouchableOpacity
              style={[styles.exportButton, exporting && styles.buttonDisabled]}
              onPress={handleExportPress}
              disabled={exporting}
            >
              {exporting ? (
                <ActivityIndicator size="small" color="#38bdf8" />
              ) : (
                <Text style={styles.exportButtonText}>Export</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.resetButton, resetting && styles.buttonDisabled]}
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

        {/* Offline Queue Indicator Banner */}
        {offlineCount > 0 && (
          <View style={styles.offlineBanner}>
            <View style={styles.offlineTextWrapper}>
              <View style={styles.amberDot} />
              <Text style={styles.offlineBannerText}>
                {offlineCount} {offlineCount === 1 ? 'record' : 'records'} pending sync
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.syncButton, isSyncing && styles.buttonDisabled]}
              onPress={handleSyncQueue}
              disabled={isSyncing}
            >
              {isSyncing ? (
                <ActivityIndicator size="small" color="#ffffff" />
              ) : (
                <Text style={styles.syncButtonText}>Sync Now</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Proof List */}
      <FlatList
        data={proofs}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderProofItem}
        contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 28 }]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#0284c7" />
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
    paddingBottom: 16,
  },
  titleRow: {
    marginBottom: 8,
  },
  subHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  screenTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: '#f8fafc',
    letterSpacing: -0.5,
  },
  subtext: {
    fontSize: 13,
    color: '#94a3b8',
  },
  headerButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  exportButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#0284c7',
    backgroundColor: 'rgba(2, 132, 199, 0.15)',
  },
  exportButtonText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '700',
  },
  resetButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#7f1d1d',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  resetButtonText: {
    color: '#f87171',
    fontSize: 11,
    fontWeight: '700',
  },
  offlineBanner: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderWidth: 1,
    borderColor: '#b45309',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  offlineTextWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  amberDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#f59e0b',
  },
  offlineBannerText: {
    color: '#fbbf24',
    fontSize: 12,
    fontWeight: '600',
  },
  syncButton: {
    backgroundColor: '#f59e0b',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
  },
  syncButtonText: {
    color: '#0f172a',
    fontSize: 11,
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
  signaturePreviewWrapper: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  signaturePreviewLabel: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 4,
  },
  signatureMiniCanvas: {
    height: 50,
    backgroundColor: '#0f172a',
    borderRadius: 6,
    overflow: 'hidden',
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