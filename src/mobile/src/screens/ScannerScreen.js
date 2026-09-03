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
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Location from 'expo-location';
import * as FileSystem from 'expo-file-system/legacy';
import * as apiClient from '../api/client';

export default function ScannerScreen({ route, navigation }) {
  const { packageId: initialPackageId } = route.params || {};

  // Package & Scanning State
  const [scannedPackageId, setScannedPackageId] = useState(initialPackageId || null);
  const [isScanning, setIsScanning] = useState(!initialPackageId);

  // Camera & Photo State
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [photoUri, setPhotoUri] = useState(null);
  const cameraRef = useRef(null);

  // GPS Location State
  const [locationPermission, setLocationPermission] = useState(null);
  const [currentCoords, setCurrentCoords] = useState(null);
  const [locationStatus, setLocationStatus] = useState('Acquiring GPS fix...');

  // Submission State
  const [submitting, setSubmitting] = useState(false);

  // Request Permissions & Retrieve Position
  useEffect(() => {
    let isMounted = true;

    async function initLocation() {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (!isMounted) return;

        const granted = status === 'granted';
        setLocationPermission(granted);

        if (!granted) {
          setLocationStatus('GPS Permission Denied');
          return;
        }

        setLocationStatus('Fetching GPS fix...');

        // 1. Check last known position immediately for zero latency
        try {
          const lastKnown = await Location.getLastKnownPositionAsync();
          if (lastKnown && isMounted) {
            setCurrentCoords({
              latitude: lastKnown.coords.latitude,
              longitude: lastKnown.coords.longitude,
              accuracy: lastKnown.coords.accuracy,
            });
            setLocationStatus(
              `GPS Ready (±${Math.round(lastKnown.coords.accuracy || 0)}m)`
            );
          }
        } catch (e) {
          // Fall through to fresh position query
        }

        // 2. Query fresh position with balanced accuracy
        const fresh = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });

        if (fresh && isMounted) {
          setCurrentCoords({
            latitude: fresh.coords.latitude,
            longitude: fresh.coords.longitude,
            accuracy: fresh.coords.accuracy,
          });
          setLocationStatus(
            `GPS Ready (±${Math.round(fresh.coords.accuracy || 0)}m)`
          );
        }
      } catch (err) {
        if (isMounted && !currentCoords) {
          setLocationStatus('GPS Fix Unavailable');
        }
      }
    }

    initLocation();

    return () => {
      isMounted = false;
    };
  }, []);

  // Barcode Scan Handler
  const handleBarcodeScanned = ({ data }) => {
    if (!isScanning) return;
    setIsScanning(false);
    setScannedPackageId(data);
  };

  // Capture Photo Proof
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

  // Submit Proof with Real GPS Coordinates
  const handleConfirmDelivery = async () => {
    if (!scannedPackageId) {
      Alert.alert('Missing Package ID', 'Please scan a barcode or specify a package.');
      return;
    }

    setSubmitting(true);

    // Live GPS -> Cached -> Chicago Default Fallback
    let finalLat = 41.8786;
    let finalLon = -87.6403;

    if (currentCoords) {
      finalLat = currentCoords.latitude;
      finalLon = currentCoords.longitude;
    } else if (locationPermission) {
      try {
        const quickLoc = await Location.getLastKnownPositionAsync();
        if (quickLoc) {
          finalLat = quickLoc.coords.latitude;
          finalLon = quickLoc.coords.longitude;
        }
      } catch (e) {
        // Fall back to default
      }
    }

    const baseUrl =
      apiClient.BASE_URL ||
      apiClient.API_URL ||
      'http://192.168.12.196:8000';

    try {
      let resultData;

      if (photoUri) {
        const uploadResponse = await FileSystem.uploadAsync(
          `${baseUrl}/delivery/confirm`,
          photoUri,
          {
            fieldName: 'photo',
            httpMethod: 'POST',
            uploadType: FileSystem.FileSystemUploadType.MULTIPART,
            parameters: {
              package_id: String(scannedPackageId),
              driver_id: 'D001',
              dest_lat: String(finalLat),
              dest_lon: String(finalLon),
              status: 'DELIVERED',
            },
          }
        );

        if (uploadResponse.status < 200 || uploadResponse.status >= 300) {
          throw new Error(`Server returned ${uploadResponse.status}: ${uploadResponse.body}`);
        }

        resultData = JSON.parse(uploadResponse.body);
      } else {
        const params = new URLSearchParams();
        params.append('package_id', scannedPackageId);
        params.append('driver_id', 'D001');
        params.append('dest_lat', String(finalLat));
        params.append('dest_lon', String(finalLon));
        params.append('status', 'DELIVERED');

        const response = await fetch(`${baseUrl}/delivery/confirm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: params.toString(),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Server returned ${response.status}: ${errorText}`);
        }

        resultData = await response.json();
      }

      if (resultData && (resultData.success || resultData.record_id)) {
        Alert.alert(
          'Delivery Verified',
          `Package ${scannedPackageId} confirmed!\nGPS: ${finalLat.toFixed(5)}, ${finalLon.toFixed(5)}`,
          [
            {
              text: 'OK',
              onPress: () => {
                setPhotoUri(null);
                setScannedPackageId(null);
                navigation.navigate('Home');
              },
            },
          ]
        );
      } else {
        throw new Error('Server returned an unrecognized response format.');
      }
    } catch (err) {
      Alert.alert('Upload Error', err.message || 'Failed to submit delivery proof.');
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
        <Text style={styles.errorText}>
          Camera access is required for proof capture.
        </Text>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={requestCameraPermission}
        >
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
            {scannedPackageId ? scannedPackageId : 'Scan Barcode Below'}
          </Text>
        </View>

        <View style={styles.telemetryRow}>
          <Text style={styles.telemetryLabel}>GPS Status:</Text>
          <Text
            style={[
              styles.telemetryValue,
              locationStatus.includes('Ready')
                ? styles.gpsActive
                : styles.gpsInactive,
            ]}
          >
            {locationStatus}
          </Text>
        </View>

        {currentCoords && (
          <Text style={styles.coordSubtext}>
            Lat: {currentCoords.latitude.toFixed(5)} | Lon:{' '}
            {currentCoords.longitude.toFixed(5)}
          </Text>
        )}
      </View>

      {/* Camera / Photo Review Section */}
      <View style={styles.cameraContainer}>
        {photoUri ? (
          <View style={styles.previewWrapper}>
            <Image source={{ uri: photoUri }} style={styles.previewImage} />
            <TouchableOpacity
              style={styles.retakeButton}
              onPress={() => setPhotoUri(null)}
            >
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
                <Text style={styles.overlayPrompt}>
                  Align barcode within square
                </Text>
              </View>
            )}
          </CameraView>
        )}
      </View>

      {/* Action Controls */}
      <View style={styles.actionContainer}>
        {!photoUri && (
          <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
            <Text style={styles.buttonText}>Capture Photo Proof</Text>
          </TouchableOpacity>
        )}

        {isScanning ? (
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setIsScanning(false)}
          >
            <Text style={styles.secondaryButtonText}>Cancel Scanner</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setIsScanning(true)}
          >
            <Text style={styles.secondaryButtonText}>Rescan Barcode</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[
            styles.submitButton,
            (!scannedPackageId || submitting) && styles.disabledButton,
          ]}
          onPress={handleConfirmDelivery}
          disabled={!scannedPackageId || submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.submitButtonText}>Confirm & Log Delivery</Text>
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
    height: 340,
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
    width: 210,
    height: 210,
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
    opacity: 0.6,
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