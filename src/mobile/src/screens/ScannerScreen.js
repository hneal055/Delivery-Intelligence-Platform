import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  ScrollView,
  Platform,
  PanResponder,
} from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { getMyPackages, scanPackage } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { getEffectiveLocation } from '../utils/location';
import { enqueueOfflineDelivery, uploadConfirmation } from '../utils/offlineQueue';

export default function ScannerScreen({ route, navigation }) {
  const { packageId: initialPackageId } = route.params || {};
  const driverId = useAuthStore((s) => s.driverId);

  const [scannedPackageId, setScannedPackageId] = useState(initialPackageId || null);
  const [isScanning, setIsScanning] = useState(!initialPackageId);

  // The driver's undelivered packages, for quick selection without scanning
  const [pendingPackages, setPendingPackages] = useState([]);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [photoUri, setPhotoUri] = useState(null);
  const cameraRef = useRef(null);

  const [paths, setPaths] = useState([]);
  const [currentPath, setCurrentPath] = useState('');

  const [currentCoords, setCurrentCoords] = useState(null);
  const [locationStatus, setLocationStatus] = useState('Acquiring GPS fix...');
  const [submitting, setSubmitting] = useState(false);

  // Load the driver's undelivered packages for the quick-select chips
  useEffect(() => {
    async function loadPendingStops() {
      try {
        const packages = await getMyPackages();
        const pending = packages
          .filter((p) => p.status !== 'delivered' && p.status !== 'exception')
          .map((p) => p.id);
        setPendingPackages(pending);
      } catch (e) {
        // Offline: the driver can still scan the barcode
      }
    }

    loadPendingStops();
  }, [initialPackageId]);

  // Opening from the manifest's "Deliver" button selects that package
  useEffect(() => {
    if (initialPackageId) {
      setScannedPackageId(initialPackageId);
      setIsScanning(false);
    }
  }, [initialPackageId]);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        const { locationX, locationY } = evt.nativeEvent;
        setCurrentPath(`M ${locationX.toFixed(1)} ${locationY.toFixed(1)}`);
      },
      onPanResponderMove: (evt) => {
        const { locationX, locationY } = evt.nativeEvent;
        setCurrentPath((prev) => `${prev} L ${locationX.toFixed(1)} ${locationY.toFixed(1)}`);
      },
      onPanResponderRelease: () => {
        setCurrentPath((prev) => {
          if (prev) {
            setPaths((existing) => [...existing, prev]);
          }
          return '';
        });
      },
    })
  ).current;

  const clearSignature = () => {
    setPaths([]);
    setCurrentPath('');
  };

  useEffect(() => {
    let isMounted = true;

    async function syncLocation() {
      const { coords, statusText } = await getEffectiveLocation();
      if (isMounted) {
        setCurrentCoords(coords);
        setLocationStatus(statusText);
      }
    }

    syncLocation();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleBarcodeScanned = async ({ type, data }) => {
    if (!isScanning) return;
    setIsScanning(false);
    try {
      // Resolves a tracking code to the package and marks it loaded
      const result = await scanPackage(data, type);
      setScannedPackageId(result.package_id);
    } catch (err) {
      if (err.response?.status === 404) {
        Alert.alert('Unknown Package', `No package matches barcode ${data}.`);
        setScannedPackageId(null);
        return;
      }
      // Offline: use the barcode as the package ID; the server checks it on sync
      setScannedPackageId(data);
    }
  };

  const takePicture = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.7,
          skipProcessing: false,
        });
        setPhotoUri(photo.uri);
      } catch (err) {
        Alert.alert('Camera Error', 'Could not capture delivery photo.');
      }
    }
  };

  const resetAfterDelivery = () => {
    setPhotoUri(null);
    clearSignature();
    setScannedPackageId(null);
    setIsScanning(true);
    navigation.navigate('Home');
  };

  const handleConfirmDelivery = async () => {
    if (!scannedPackageId) {
      Alert.alert('Missing Package ID', 'Please select or scan a package first.');
      return;
    }
    if (!photoUri) {
      Alert.alert('Photo Required', 'Capture a proof-of-delivery photo first.');
      return;
    }

    setSubmitting(true);

    // Record the real position only. No fix (or the dev simulator) means no
    // GPS on the proof rather than a made-up one.
    const effectiveLoc = await getEffectiveLocation();
    const coords = effectiveLoc.coords && !effectiveLoc.isMocked ? effectiveLoc.coords : null;
    setLocationStatus(
      effectiveLoc.isMocked ? 'Chicago Sim (Dev Mode) - not recorded' : effectiveLoc.statusText
    );
    setCurrentCoords(coords);
    const signatureData = paths.length > 0 ? paths.join(' ') : null;

    const delivery = {
      package_id: scannedPackageId,
      driver_id: driverId,
      dest_lat: coords ? coords.latitude : null,
      dest_lon: coords ? coords.longitude : null,
      signature_path: signatureData,
    };

    try {
      await uploadConfirmation(delivery, photoUri);
      Alert.alert(
        'Delivery Verified',
        `Package ${scannedPackageId} confirmed!${
          coords
            ? `\nGPS: ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`
            : `\nNo GPS recorded (${effectiveLoc.statusText})`
        }${signatureData ? '\nCustomer Signature Captured' : ''}`,
        [{ text: 'OK', onPress: resetAfterDelivery }]
      );
    } catch (err) {
      if (err.status === 400) {
        // Photo failed the quality check: retake, nothing is queued
        Alert.alert('Retake Photo', err.message);
        setPhotoUri(null);
      } else if (err.status === 409) {
        // Already closed out (e.g. an earlier attempt did get through)
        Alert.alert('Already Delivered', err.message, [{ text: 'OK', onPress: resetAfterDelivery }]);
      } else if (err.status === 403) {
        Alert.alert('Not Your Package', `${scannedPackageId} is not assigned to you. Check with dispatch.`);
      } else if (err.status === 401) {
        Alert.alert('Session Expired', 'Log in again, then confirm this delivery.');
      } else if (err.status === 404) {
        Alert.alert('Unknown Package', `The server has no package ${scannedPackageId}.`);
      } else {
        // No connection or server error: keep the proof and sync later
        console.warn('Upload failed, saving to offline queue:', err.message);
        try {
          await enqueueOfflineDelivery({ ...delivery, photoUri });
          Alert.alert(
            'Saved Offline',
            `Delivery for ${scannedPackageId} was saved and will sync when the connection is back.`,
            [{ text: 'OK', onPress: resetAfterDelivery }]
          );
        } catch (queueErr) {
          Alert.alert('Storage Error', 'Failed to save delivery offline.');
        }
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!cameraPermission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#0284c7" />
        <Text style={styles.statusText}>Requesting camera permission...</Text>
      </View>
    );
  }

  if (!cameraPermission.granted) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Camera access is required for proof capture.</Text>
        <TouchableOpacity style={styles.primaryButton} onPress={requestCameraPermission}>
          <Text style={styles.buttonText}>Grant Camera Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container} bounces={false}>
      {/* Telemetry Header */}
      <View style={styles.telemetryCard}>
        <View style={styles.telemetryRow}>
          <Text style={styles.telemetryLabel}>Target Stop:</Text>
          <Text style={styles.telemetryValue}>
            {scannedPackageId ? scannedPackageId : 'Select Stop Below'}
          </Text>
        </View>

        {/* Quick package selection chips if driver opens scanner directly */}
        <View style={styles.chipRow}>
          <Text style={styles.chipLabel}>Select Stop:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsContainer}>
            {pendingPackages.map((pkg) => {
              const isSelected = scannedPackageId === pkg;
              return (
                <TouchableOpacity
                  key={pkg}
                  style={[styles.pkgChip, isSelected && styles.pkgChipSelected]}
                  onPress={() => setScannedPackageId(pkg)}
                >
                  <Text style={[styles.pkgChipText, isSelected && styles.pkgChipTextSelected]}>
                    {pkg}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>

        <View style={styles.telemetryRow}>
          <Text style={styles.telemetryLabel}>GPS Status:</Text>
          <Text
            style={[
              styles.telemetryValue,
              // Only a real fix is recorded on the proof; the simulator is not
              locationStatus.includes('Live') || locationStatus.includes('Last known')
                ? styles.gpsActive
                : styles.gpsInactive,
            ]}
          >
            {locationStatus}
          </Text>
        </View>

        {currentCoords && (
          <Text style={styles.coordSubtext}>
            Lat: {currentCoords.latitude.toFixed(5)} | Lon: {currentCoords.longitude.toFixed(5)}
          </Text>
        )}
      </View>

      {/* Camera / Photo Review Section */}
      <View style={styles.cameraContainer}>
        {photoUri ? (
          <View style={styles.previewWrapper}>
            <Image source={{ uri: photoUri }} style={styles.previewImage} />
            <TouchableOpacity style={styles.retakeButton} onPress={() => setPhotoUri(null)}>
              <Text style={styles.retakeButtonText}>Retake Photo</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <CameraView
            ref={cameraRef}
            style={styles.camera}
            facing="back"
            barcodeScannerSettings={{
              barcodeTypes: ['qr', 'code128', 'ean13', 'upc_a'],
            }}
            onBarcodeScanned={isScanning ? handleBarcodeScanned : undefined}
          >
            {isScanning && (
              <View style={styles.scannerOverlay}>
                <View style={styles.scannerTarget} />
                <Text style={styles.overlayPrompt}>Align barcode within square</Text>
              </View>
            )}
          </CameraView>
        )}
      </View>

      {/* Signature Canvas */}
      <View style={styles.signatureCard}>
        <View style={styles.signatureHeader}>
          <Text style={styles.signatureTitle}>Customer Signature (Optional)</Text>
          {paths.length > 0 && (
            <TouchableOpacity onPress={clearSignature}>
              <Text style={styles.clearText}>Clear</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.canvasContainer} {...panResponder.panHandlers}>
          <Svg style={StyleSheet.absoluteFill}>
            {paths.map((p, i) => (
              <Path key={i} d={p} stroke="#38bdf8" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ))}
            {currentPath ? (
              <Path d={currentPath} stroke="#38bdf8" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ) : null}
          </Svg>
          {paths.length === 0 && !currentPath && (
            <Text style={styles.signaturePlaceholder}>Sign with finger above</Text>
          )}
        </View>
      </View>

      {/* Action Controls */}
      <View style={styles.actionContainer}>
        {!photoUri && (
          <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
            <Text style={styles.buttonText}>Capture Photo Proof</Text>
          </TouchableOpacity>
        )}

        {isScanning ? (
          <TouchableOpacity style={styles.secondaryButton} onPress={() => setIsScanning(false)}>
            <Text style={styles.secondaryButtonText}>Hide Barcode Reticle</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.secondaryButton} onPress={() => setIsScanning(true)}>
            <Text style={styles.secondaryButtonText}>Rescan Barcode</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[
            styles.submitButton,
            (!scannedPackageId || !photoUri || submitting) && styles.disabledButton,
          ]}
          onPress={handleConfirmDelivery}
          disabled={!scannedPackageId || !photoUri || submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.submitButtonText}>
              {!scannedPackageId
                ? 'Select Stop to Deliver'
                : !photoUri
                ? 'Capture Photo to Confirm'
                : `Confirm & Log ${scannedPackageId}`}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#0f172a',
    padding: 16,
    paddingBottom: 40,
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  statusText: {
    marginTop: 16,
    color: '#94a3b8',
    fontSize: 15,
  },
  errorText: {
    color: '#f87171',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  telemetryCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  telemetryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 3,
  },
  telemetryLabel: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600',
  },
  telemetryValue: {
    color: '#f1f5f9',
    fontSize: 13,
    fontWeight: '700',
  },
  chipRow: {
    marginTop: 8,
    marginBottom: 6,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  chipLabel: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 6,
  },
  chipsContainer: {
    gap: 8,
  },
  pkgChip: {
    backgroundColor: '#0f172a',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155',
  },
  pkgChipSelected: {
    backgroundColor: '#0284c7',
    borderColor: '#38bdf8',
  },
  pkgChipText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
  pkgChipTextSelected: {
    color: '#ffffff',
    fontWeight: '700',
  },
  coordSubtext: {
    marginTop: 6,
    fontSize: 12,
    color: '#38bdf8',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    textAlign: 'right',
  },
  gpsActive: {
    color: '#22c55e',
  },
  gpsInactive: {
    color: '#f59e0b',
  },
  cameraContainer: {
    width: '100%',
    height: 280,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#000',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  camera: {
    flex: 1,
  },
  scannerOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  scannerTarget: {
    width: 200,
    height: 200,
    borderWidth: 2,
    borderColor: '#38bdf8',
    borderRadius: 12,
    backgroundColor: 'transparent',
  },
  overlayPrompt: {
    marginTop: 14,
    color: '#e2e8f0',
    fontSize: 13,
    fontWeight: '500',
  },
  previewWrapper: {
    flex: 1,
    position: 'relative',
  },
  previewImage: {
    width: '100%',
    height: '100%',
  },
  retakeButton: {
    position: 'absolute',
    bottom: 14,
    alignSelf: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    paddingVertical: 8,
    paddingHorizontal: 18,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#64748b',
  },
  retakeButtonText: {
    color: '#f8fafc',
    fontSize: 13,
    fontWeight: '600',
  },
  signatureCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 16,
  },
  signatureHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  signatureTitle: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600',
  },
  clearText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '700',
  },
  canvasContainer: {
    height: 120,
    backgroundColor: '#0f172a',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  signaturePlaceholder: {
    color: '#475569',
    fontSize: 13,
    fontStyle: 'italic',
  },
  actionContainer: {
    gap: 10,
  },
  captureButton: {
    backgroundColor: '#334155',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  secondaryButton: {
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#475569',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#94a3b8',
    fontSize: 14,
    fontWeight: '600',
  },
  submitButton: {
    backgroundColor: '#0284c7',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 6,
  },
  disabledButton: {
    backgroundColor: '#1e293b',
    opacity: 0.5,
  },
  primaryButton: {
    backgroundColor: '#0284c7',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 15,
    fontWeight: '600',
  },
  submitButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
});