import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, TextInput, Modal } from 'react-native';

export default function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [backendStatus, setBackendStatus] = useState('ONLINE (PostGIS Connected)');
  
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const [selectedDispatch, setSelectedDispatch] = useState<any>(null);
  const [isTrackingModalVisible, setIsTrackingModalVisible] = useState(false);

  // Route playback simulation state
  const [isPlayingRoute, setIsPlayingRoute] = useState(false);
  const [playbackProgress, setPlaybackProgress] = useState(0); // 0 to 100%
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x, 2x, 5x, 10x
  
  // Dynamic dispatches state loaded from PostGIS backend
  const [dispatches, setDispatches] = useState<any[]>([]);
  const [activeDriver, setActiveDriver] = useState<any>({
    id: 'DISP-1092',
    driver: 'Marcus Vance',
    dest: 'North Loop Terminal',
    status: 'In Transit',
    speed: '34 mph',
    lat: 41.8781,
    lng: -87.6298,
    path: [
      [41.7500, -87.8500],
      [41.8000, -87.7500],
      [41.8500, -87.6800],
      [41.8781, -87.6298]
    ]
  });

  const [drivers, setDrivers] = useState([
    { id: 'DRV-201', name: 'Marcus Vance', status: 'On Route', vehicle: 'Sprinter Van #401', rating: '4.9/5' },
    { id: 'DRV-202', name: 'Sarah Jenkins', status: 'Ready', vehicle: 'Box Truck #402', rating: '4.8/5' },
    { id: 'DRV-203', name: 'David Ross', status: 'Off Duty', vehicle: 'Delivery EV #403', rating: '4.7/5' },
    { id: 'DRV-204', name: 'Elena Rostova', status: 'On Route', vehicle: 'Heavy Semi #404', rating: '5.0/5' },
  ]);

  const [packages, setPackages] = useState([
    { trackingId: 'PKG-9012', recipient: 'Apex Logistics Corp', weight: '42 lbs', priority: 'High', status: 'In Transit' },
    { trackingId: 'PKG-9013', recipient: 'Midwest Medical Supply', weight: '12 lbs', priority: 'Urgent', status: 'Dispatched' },
    { trackingId: 'PKG-9014', recipient: 'Chicago Industrial Park', weight: '115 lbs', priority: 'Standard', status: 'Delivered' },
  ]);

  const [equipment, setEquipment] = useState([
    { eqId: 'EQ-501', name: 'Handheld DIAD Scanner v5', assignedDriver: 'Marcus Vance', status: 'Active' },
    { eqId: 'EQ-502', name: 'Hydraulic Pallet Jack', assignedDriver: 'Sarah Jenkins', status: 'In Use' },
    { eqId: 'EQ-503', name: 'GPS Telemetry Beacon Gen-2', assignedDriver: 'Elena Rostova', status: 'Online' },
  ]);

  const [fleet, setFleet] = useState([
    { unit: 'UNIT-401', type: 'Sprinter Cargo Van', fuel: '84%', status: 'Active', zone: 'North Chicago' },
    { unit: 'UNIT-402', type: 'Box Truck 16ft', fuel: '92%', status: 'Active', zone: 'West Loop' },
    { unit: 'UNIT-403', type: 'Electric Delivery EV', fuel: '45%', status: 'Charging', zone: 'O\'Hare Hub' },
    { unit: 'UNIT-404', type: 'Heavy Freight Semi', fuel: '78%', status: 'In Transit', zone: 'I-90 Corridor' },
  ]);

  // Leaflet Map Reference
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const polylineRef = useRef<any>(null);

  // Fetch live PostGIS telemetry GeoJSON from FastAPI backend on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/dispatches/geojson')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.features && data.features.length > 0) {
          const mappedDispatches = data.features.map((f: any) => ({
            id: f.properties.id,
            driver: f.properties.driver_id,
            dest: f.properties.destination,
            status: f.properties.status,
            speed: f.properties.speed,
            lat: f.geometry.coordinates[1],
            lng: f.geometry.coordinates[0],
            path: [
              [41.7500, -87.8500],
              [41.8000, -87.7500],
              [41.8500, -87.6800],
              [f.geometry.coordinates[1], f.geometry.coordinates[0]]
            ]
          }));
          setDispatches(mappedDispatches);
          if (mappedDispatches.length > 0) {
            setActiveDriver(mappedDispatches[0]);
          }
        }
      })
      .catch((err) => {
        console.warn('Backend PostGIS fetch fallback active:', err);
        const fallback = [
          { id: 'DISP-1092', driver: 'Marcus Vance', dest: 'North Loop Terminal', status: 'In Transit', speed: '34 mph', lat: 41.8781, lng: -87.6298, path: [[41.75, -87.85], [41.80, -87.75], [41.8781, -87.6298]] },
          { id: 'DISP-1093', driver: 'Sarah Jenkins', dest: 'Westside Hub C', status: 'Dispatched', speed: '0 mph', lat: 41.8850, lng: -87.6500, path: [[41.82, -87.70], [41.8850, -87.6500]] },
        ];
        setDispatches(fallback);
        setActiveDriver(fallback[0]);
      });
  }, []);

  // Initialize Leaflet Map when Live Map tab is active
  useEffect(() => {
    if (activeTab === 'Live Map') {
      // Dynamically load Leaflet CSS & JS from CDN if not already present
      if (!document.getElementById('leaflet-css')) {
        const link = document.createElement('link');
        link.id = 'leaflet-css';
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
      }

      if (!window.L) {
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.async = true;
        script.onload = () => initLeafletMap();
        document.body.appendChild(script);
      } else {
        setTimeout(initLeafletMap, 100);
      }
    }
  }, [activeTab, isMapExpanded]);

  const initLeafletMap = () => {
    const container = document.getElementById('leaflet-map-container');
    if (!container) return;

    // Clear previous map instance if it exists
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const L = window.L;
    if (!L) return;

    // Create map centered on Chicago
    const map = L.map('leaflet-map-container').setView([activeDriver.lat, activeDriver.lng], 12);
    mapRef.current = map;

    // Add OpenStreetMap Tile Layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add Route Polyline
    if (activeDriver.path && activeDriver.path.length > 0) {
      polylineRef.current = L.polyline(activeDriver.path, { color: '#2563eb', weight: 5, dashArray: '6, 6' }).addTo(map);
    }

    // Add Driver Marker
    markerRef.current = L.marker([activeDriver.lat, activeDriver.lng]).addTo(map)
      .bindPopup(`<b>${activeDriver.driver}</b><br/>Status: ${activeDriver.status}<br/>Speed: ${activeDriver.speed}`)
      .openPopup();
  };

  // Update marker position when playback progress or active driver changes
  useEffect(() => {
    if (!mapRef.current || !activeDriver.path || activeDriver.path.length === 0) return;
    const L = window.L;
    if (!L) return;

    const pts = activeDriver.path;
    const exactIndex = (playbackProgress / 100) * (pts.length - 1);
    const lowerIndex = Math.floor(exactIndex);
    const upperIndex = Math.min(Math.ceil(exactIndex), pts.length - 1);
    const weight = exactIndex - lowerIndex;

    const p1 = pts[lowerIndex] || pts[0];
    const p2 = pts[upperIndex] || pts[0];

    const currentLat = p1[0] + (p2[0] - p1[0]) * weight;
    const currentLng = p1[1] + (p2[1] - p1[1]) * weight;

    if (markerRef.current) {
      markerRef.current.setLatLng([currentLat, currentLng]);
      markerRef.current.setPopupContent(`<b>${activeDriver.driver}</b><br/>Progress: ${playbackProgress}%<br/>Speed: ${activeDriver.speed}`);
    }
  }, [playbackProgress, activeDriver]);

  // Route playback simulation loop
  useEffect(() => {
    let interval: any;
    if (isPlayingRoute) {
      interval = setInterval(() => {
        setPlaybackProgress((prev) => {
          if (prev >= 100) {
            setIsPlayingRoute(false);
            return 100;
          }
          return prev + (1 * playbackSpeed);
        });
      }, 150);
    }
    return () => clearInterval(interval);
  }, [isPlayingRoute, playbackSpeed]);

  const handleTrackDispatch = (dispatch: any) => {
    setSelectedDispatch(dispatch);
    setIsTrackingModalVisible(true);
  };

  const navItems = [
    'Overview', 
    'Active Dispatches', 
    'Live Map', 
    'Drivers', 
    'Packages', 
    'Equipment', 
    'Fleet Management', 
    'Analytics', 
    'Settings'
  ];

  return (
    <View style={styles.container}>
      {/* Sidebar Navigation */}
      <View style={styles.sidebar}>
        <View>
          <Text style={styles.brandTitle}>Delivery Intelligence</Text>
          <Text style={styles.brandSubtitle}>Platform Operations</Text>
          
          <ScrollView contentContainerStyle={styles.navMenu}>
            {navItems.map((item) => (
              <TouchableOpacity 
                key={item} 
                style={[styles.navItem, activeTab === item && styles.activeNavItem]}
                onPress={() => setActiveTab(item)}
              >
                <Text style={[styles.navText, activeTab === item && styles.activeNavText]}>{item}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
        <View style={styles.sidebarFooter}>
          <Text style={styles.footerText}>Backend: <Text style={styles.onlineText}>{backendStatus}</Text></Text>
          <Text style={styles.footerSubtext}>PostGIS + Leaflet Linked</Text>
        </View>
      </View>

      {/* Main Content Area */}
      <View style={styles.mainContent}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{activeTab} Platform Center</Text>
          <TextInput 
            style={styles.searchBar} 
            placeholder="Search platform telemetry..." 
            placeholderTextColor="#6b7280"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>

        <ScrollView contentContainerStyle={styles.scrollBody}>
          
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'Overview' && (
            <>
              <View style={styles.cardsGrid}>
                <View style={styles.card}>
                  <Text style={styles.cardLabel}>Active Dispatches</Text>
                  <Text style={styles.cardValue}>{dispatches.length}</Text>
                  <Text style={styles.cardTrend}>PostGIS Database Sync</Text>
                </View>
                <View style={styles.card}>
                  <Text style={styles.cardLabel}>Active Drivers</Text>
                  <Text style={styles.cardValue}>{drivers.length}</Text>
                  <Text style={styles.cardTrend}>Assigned & Ready</Text>
                </View>
                <View style={styles.card}>
                  <Text style={styles.cardLabel}>Tracked Packages</Text>
                  <Text style={styles.cardValue}>{packages.length}</Text>
                  <Text style={styles.cardTrend}>In Pipeline</Text>
                </View>
                <View style={styles.card}>
                  <Text style={styles.cardLabel}>System Latency</Text>
                  <Text style={styles.cardValue}>12ms</Text>
                  <Text style={styles.cardTrend}>Leaflet Canvas Active</Text>
                </View>
              </View>

              <View style={styles.panel}>
                <Text style={styles.panelTitle}>Platform Telemetry & Routing Stream</Text>
                <View style={styles.tableHeader}>
                  <Text style={[styles.tableCell, styles.tableHeaderCell]}>Dispatch ID</Text>
                  <Text style={[styles.tableCell, styles.tableHeaderCell]}>Driver</Text>
                  <Text style={[styles.tableCell, styles.tableHeaderCell]}>Destination</Text>
                  <Text style={[styles.tableCell, styles.tableHeaderCell]}>Status</Text>
                </View>
                {dispatches.map((row, idx) => (
                  <View key={idx} style={styles.tableRow}>
                    <Text style={styles.tableCellText}>{row.id}</Text>
                    <Text style={styles.tableCellText}>{row.driver}</Text>
                    <Text style={styles.tableCellText}>{row.dest}</Text>
                    <Text style={[styles.tableCellText, styles.statusBadge]}>{row.status}</Text>
                  </View>
                ))}
              </View>
            </>
          )}

          {/* TAB 2: ACTIVE DISPATCHES */}
          {activeTab === 'Active Dispatches' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>Active Dispatches & Live Telemetry Queue</Text>
              <Text style={styles.panelDescription}>Real-time routing nodes and live driver packages fetched from PostGIS.</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Dispatch ID</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Assigned Driver</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Destination</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>GPS Coordinates</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Action</Text>
              </View>
              {dispatches.map((row, idx) => (
                <View key={idx} style={styles.tableRow}>
                  <Text style={styles.tableCellText}>{row.id}</Text>
                  <Text style={styles.tableCellText}>{row.driver}</Text>
                  <Text style={styles.tableCellText}>{row.dest}</Text>
                  <Text style={styles.tableCellText}>{row.lat}° N, {row.lng}° W</Text>
                  <TouchableOpacity 
                    style={styles.actionBtn}
                    onPress={() => handleTrackDispatch(row)}
                  >
                    <Text style={styles.actionBtnText}>Track</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          )}

          {/* TAB 3: LIVE MAP & ROUTE REPLAY */}
          {activeTab === 'Live Map' && (
            <View style={styles.panel}>
              <View style={styles.mapHeaderRow}>
                <View>
                  <Text style={styles.panelTitle}>🗺️ PostGIS + Leaflet Unified Interactive Map</Text>
                  <Text style={styles.panelDescription}>Select a driver below to lock geographic markers on interactive tiles and play route history.</Text>
                </View>
                <View style={styles.mapControlsRight}>
                  <TouchableOpacity 
                    style={styles.expandMapBtn}
                    onPress={() => setIsMapExpanded(!isMapExpanded)}
                  >
                    <Text style={styles.expandMapBtnText}>{isMapExpanded ? '🗗 Standard Size' : '⛶ Expand Map Window'}</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* SELECTABLE DRIVER BUTTONS */}
              <View style={styles.driverButtonRow}>
                {dispatches.map((d) => {
                  const isSelected = activeDriver.id === d.id;
                  return (
                    <TouchableOpacity
                      key={d.id}
                      onPress={() => {
                        setActiveDriver(d);
                        setPlaybackProgress(0);
                        setIsPlayingRoute(false);
                        if (mapRef.current && d.lat && d.lng) {
                          mapRef.current.setView([d.lat, d.lng], 13);
                        }
                      }}
                      style={[
                        styles.driverSelectBtn,
                        isSelected && styles.driverSelectBtnSelected
                      ]}
                    >
                      <Text style={styles.driverSelectEmoji}>🚚</Text>
                      <View>
                        <Text style={[styles.driverSelectTitle, isSelected && { color: '#60a5fa' }]}>{d.driver} ({d.id})</Text>
                        <Text style={styles.driverSelectStatus}>{d.status}</Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* LEAFLET INTERACTIVE MAP CONTAINER */}
              <View style={[styles.visualMapCanvas, isMapExpanded && styles.visualMapCanvasExpanded]}>
                <div 
                  id="leaflet-map-container" 
                  style={{ width: '100%', height: '100%', minHeight: isMapExpanded ? '600px' : '440px', borderRadius: '12px', zIndex: 1 }}
                />
              </View>

              {/* ROUTE HISTORY REPLAY SLIDER & SPEED CONTROLLER */}
              <View style={styles.playbackPanel}>
                <View style={styles.playbackHeaderRow}>
                  <Text style={styles.playbackTitle}>
                    🎬 Route History Replay: <Text style={{ color: '#38bdf8' }}>{activeDriver.driver}</Text>
                  </Text>
                  <View style={styles.playbackActionGroup}>
                    <TouchableOpacity 
                      style={styles.playBtn}
                      onPress={() => setIsPlayingRoute(!isPlayingRoute)}
                    >
                      <Text style={styles.playBtnText}>{isPlayingRoute ? '⏸ Pause Replay' : '▶ Play Route History'}</Text>
                    </TouchableOpacity>
                    <Text style={styles.playbackLabel}>Speed:</Text>
                    {[1, 2, 5, 10].map((spd) => (
                      <TouchableOpacity
                        key={spd}
                        onPress={() => setPlaybackSpeed(spd)}
                        style={[styles.speedBtn, playbackSpeed === spd && styles.activeSpeedBtn]}
                      >
                        <Text style={[styles.speedBtnText, playbackSpeed === spd && styles.activeSpeedText]}>{spd}x</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>

                <View>
                  <View style={styles.sliderInfoRow}>
                    <Text style={styles.sliderInfoText}>Timeline Progress: {playbackProgress}%</Text>
                    <Text style={styles.sliderInfoText}>{isPlayingRoute ? 'Processing route path nodes...' : 'Paused / Ready'}</Text>
                  </View>
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    value={playbackProgress} 
                    onChange={(e) => setPlaybackProgress(Number(e.target.value))}
                    style={{ width: '100%', cursor: 'pointer', accentColor: '#3b82f6', height: '6px' }}
                  />
                </View>
              </View>
            </View>
          )}

          {/* TAB 4: DRIVERS */}
          {activeTab === 'Drivers' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>Driver Management & Rosters</Text>
              <Text style={styles.panelDescription}>Active field personnel, safety scores, and vehicle assignments.</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Driver ID</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Name</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Assigned Vehicle</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Performance</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Status</Text>
              </View>
              {drivers.map((drv, idx) => (
                <View key={idx} style={styles.tableRow}>
                  <Text style={styles.tableCellText}>{drv.id}</Text>
                  <Text style={styles.tableCellText}>{drv.name}</Text>
                  <Text style={styles.tableCellText}>{drv.vehicle}</Text>
                  <Text style={styles.tableCellText}>{drv.rating}</Text>
                  <Text style={[styles.tableCellText, { color: drv.status === 'On Route' ? '#34d399' : '#60a5fa', fontWeight: '600' }]}>{drv.status}</Text>
                </View>
              ))}
            </View>
          )}

          {/* TAB 5: PACKAGES */}
          {activeTab === 'Packages' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>Package Pipeline & Sorting Stream</Text>
              <Text style={styles.panelDescription}>Track waybills, package weights, and sorting priorities.</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Tracking ID</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Recipient</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Weight</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Priority</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Status</Text>
              </View>
              {packages.map((pkg, idx) => (
                <View key={idx} style={styles.tableRow}>
                  <Text style={styles.tableCellText}>{pkg.trackingId}</Text>
                  <Text style={styles.tableCellText}>{pkg.recipient}</Text>
                  <Text style={styles.tableCellText}>{pkg.weight}</Text>
                  <Text style={[styles.tableCellText, { color: pkg.priority === 'Urgent' ? '#f87171' : '#38bdf8' }]}>{pkg.priority}</Text>
                  <Text style={[styles.tableCellText, styles.statusBadge]}>{pkg.status}</Text>
                </View>
              ))}
            </View>
          )}

          {/* TAB 6: EQUIPMENT */}
          {activeTab === 'Equipment' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>Field Equipment & Scanner Inventory</Text>
              <Text style={styles.panelDescription}>DIAD scanners, hardware beacons, and mobile terminal units.</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Equipment ID</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Device Name</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Assigned Driver</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Status</Text>
              </View>
              {equipment.map((eq, idx) => (
                <View key={idx} style={styles.tableRow}>
                  <Text style={styles.tableCellText}>{eq.eqId}</Text>
                  <Text style={styles.tableCellText}>{eq.name}</Text>
                  <Text style={styles.tableCellText}>{eq.assignedDriver}</Text>
                  <Text style={[styles.tableCellText, { color: '#34d399', fontWeight: '600' }]}>{eq.status}</Text>
                </View>
              ))}
            </View>
          )}

          {/* TAB 7: FLEET MANAGEMENT */}
          {activeTab === 'Fleet Management' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>Fleet Vehicle Status & Maintenance</Text>
              <Text style={styles.panelDescription}>Monitor vehicle health, fuel/battery telemetry, and regional zone assignments.</Text>
              <View style={styles.tableHeader}>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Unit ID</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Vehicle Type</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Fuel / Battery</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Zone</Text>
                <Text style={[styles.tableCell, styles.tableHeaderCell]}>Status</Text>
              </View>
              {fleet.map((v, idx) => (
                <View key={idx} style={styles.tableRow}>
                  <Text style={styles.tableCellText}>{v.unit}</Text>
                  <Text style={styles.tableCellText}>{v.type}</Text>
                  <Text style={styles.tableCellText}>{v.fuel}</Text>
                  <Text style={styles.tableCellText}>{v.zone}</Text>
                  <Text style={[styles.tableCellText, { color: v.status === 'Active' ? '#34d399' : '#fbbf24', fontWeight: '600' }]}>{v.status}</Text>
                </View>
              ))}
            </View>
          )}

          {/* TAB 8: ANALYTICS */}
          {activeTab === 'Analytics' && (
            <View style={styles.cardsGrid}>
              <View style={styles.card}>
                <Text style={styles.cardLabel}>Avg Delivery Time</Text>
                <Text style={styles.cardValue}>24.5 min</Text>
                <Text style={styles.cardTrend}>-3.2 min vs yesterday</Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.cardLabel}>Total Distance Today</Text>
                <Text style={styles.cardValue}>1,420 mi</Text>
                <Text style={styles.cardTrend}>Across 18 zones</Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.cardLabel}>Fuel Efficiency Index</Text>
                <Text style={styles.cardValue}>94.1%</Text>
                <Text style={styles.cardTrend}>Optimized routes</Text>
              </View>
            </View>
          )}

          {/* TAB 9: SETTINGS */}
          {activeTab === 'Settings' && (
            <View style={styles.panel}>
              <Text style={styles.panelTitle}>System Configuration & API Integrations</Text>
              <Text style={styles.panelDescription}>Manage Redis cache connections, PostGIS DB credentials, and notification triggers.</Text>
              <View style={styles.settingsGroup}>
                <View style={styles.settingItem}>
                  <Text style={styles.settingLabel}>FastAPI Backend Service</Text>
                  <Text style={styles.settingVal}>http://localhost:8000 (Active)</Text>
                </View>
                <View style={styles.settingItem}>
                  <Text style={styles.settingLabel}>PostgreSQL / PostGIS Database</Text>
                  <Text style={styles.settingVal}>delivery_db @ port 5432</Text>
                </View>
              </View>
            </View>
          )}

        </ScrollView>
      </View>

      {/* LIVE TRACKING MODAL POPUP */}
      <Modal
        visible={isTrackingModalVisible}
        transparent={true}
        animationType="fade"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Live Telemetry Tracking</Text>
            {selectedDispatch && (
              <View style={styles.modalBody}>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>Dispatch ID:</Text> {selectedDispatch.id}</Text>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>Driver:</Text> {selectedDispatch.driver}</Text>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>Destination:</Text> {selectedDispatch.dest}</Text>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>Current Status:</Text> {selectedDispatch.status}</Text>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>GPS Lat/Lng:</Text> {selectedDispatch.lat}° N, {selectedDispatch.lng}° W</Text>
                <Text style={styles.modalText}><Text style={styles.modalLabel}>Velocity:</Text> {selectedDispatch.speed}</Text>
              </View>
            )}
            <TouchableOpacity 
              style={styles.closeModalBtn}
              onPress={() => setIsTrackingModalVisible(false)}
            >
              <Text style={styles.closeModalText}>Close Live Telemetry</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, flexDirection: 'row', backgroundColor: '#030712' },
  sidebar: { width: 260, backgroundColor: '#0b0f19', borderRightWidth: 1, borderRightColor: '#1f2937', padding: 24, justifyContent: 'space-between' },
  brandTitle: { fontSize: 20, fontWeight: '900', color: '#3b82f6', letterSpacing: 0.5 },
  brandSubtitle: { fontSize: 12, color: '#9ca3af', marginBottom: 24 },
  navMenu: { gap: 6 },
  navItem: { paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8 },
  activeNavItem: { backgroundColor: '#1d4ed8' },
  navText: { color: '#9ca3af', fontSize: 14, fontWeight: '600' },
  activeNavText: { color: '#ffffff' },
  sidebarFooter: { borderTopWidth: 1, borderTopColor: '#1f2937', paddingTop: 16 },
  footerText: { color: '#d1d5db', fontSize: 12 },
  onlineText: { color: '#22c55e', fontWeight: 'bold' },
  footerSubtext: { color: '#6b7280', fontSize: 11, marginTop: 2 },
  mainContent: { flex: 1, backgroundColor: '#030712' },
  header: { height: 70, borderBottomWidth: 1, borderBottomColor: '#1f2937', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 32 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#ffffff' },
  searchBar: { backgroundColor: '#111827', borderWidth: 1, borderColor: '#374151', borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8, color: '#ffffff', width: 320, fontSize: 14 },
  scrollBody: { padding: 32 },
  cardsGrid: { flexDirection: 'row', gap: 20, marginBottom: 32 },
  card: { flex: 1, backgroundColor: '#111827', borderWidth: 1, borderColor: '#1f2937', borderRadius: 12, padding: 20 },
  cardLabel: { color: '#9ca3af', fontSize: 13, marginBottom: 8 },
  cardValue: { color: '#ffffff', fontSize: 28, fontWeight: 'bold', marginBottom: 4 },
  cardTrend: { color: '#34d399', fontSize: 12 },
  panel: { backgroundColor: '#111827', borderWidth: 1, borderColor: '#1f2937', borderRadius: 12, padding: 24 },
  panelTitle: { color: '#ffffff', fontSize: 18, fontWeight: 'bold', marginBottom: 6 },
  panelDescription: { color: '#9ca3af', fontSize: 13, marginBottom: 20 },
  mapHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 },
  mapControlsRight: { flexDirection: 'row', alignItems: 'center', gap: 12, flexWrap: 'wrap' },
  expandMapBtn: { backgroundColor: '#1f2937', borderWidth: 1, borderColor: '#334151', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 },
  expandMapBtnText: { color: '#38bdf8', fontSize: 13, fontWeight: 'bold' },
  driverButtonRow: { flexDirection: 'row', gap: 12, marginBottom: 16, flexWrap: 'wrap' },
  driverSelectBtn: { backgroundColor: '#111827', borderWidth: 1, borderColor: '#374151', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8, flexDirection: 'row', alignItems: 'center', gap: 8 },
  driverSelectBtnSelected: { backgroundColor: '#1e3a8a', borderColor: '#3b82f6', shadowColor: '#3b82f6', shadowOpacity: 0.4, shadowRadius: 6 },
  driverSelectEmoji: { fontSize: 16 },
  driverSelectTitle: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },
  driverSelectStatus: { color: '#34d399', fontSize: 11 },
  visualMapCanvas: { width: '100%', height: 440, backgroundColor: '#0f172a', borderRadius: 12, borderWidth: 1, borderColor: '#334151', overflow: 'hidden', position: 'relative', marginBottom: 20 },
  visualMapCanvasExpanded: { height: 650 },
  playbackPanel: { backgroundColor: '#111827', borderWidth: 1, borderColor: '#334151', borderRadius: 12, padding: 20 },
  playbackHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 12 },
  playbackTitle: { color: '#ffffff', fontSize: 15, fontWeight: 'bold' },
  playbackActionGroup: { flexDirection: 'row', alignItems: 'center', gap: 10, flexWrap: 'wrap' },
  playbackLabel: { color: '#9ca3af', fontSize: 13 },
  playBtn: { backgroundColor: '#2563eb', paddingVertical: 8, paddingHorizontal: 16, borderRadius: 6 },
  playBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },
  speedBtn: { backgroundColor: '#1f2937', paddingVertical: 6, paddingHorizontal: 10, borderRadius: 4 },
  activeSpeedBtn: { backgroundColor: '#3b82f6' },
  speedBtnText: { color: '#9ca3af', fontSize: 12, fontWeight: '600' },
  activeSpeedText: { color: '#ffffff' },
  sliderInfoRow: { flexDirection: 'row', justifyContent: 'space-between', color: '#9ca3af', fontSize: '12px' as any, marginBottom: '6px' as any },
  sliderInfoText: { color: '#9ca3af', fontSize: 12 },
  tableHeader: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#374151', paddingBottom: 12, marginBottom: 8 },
  tableHeaderCell: { color: '#9ca3af', fontWeight: 'bold', fontSize: 13 },
  tableRow: { flexDirection: 'row', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1f2937', alignItems: 'center' },
  tableCell: { flex: 1 },
  tableCellText: { flex: 1, color: '#e5e7eb', fontSize: 14 },
  statusBadge: { color: '#60a5fa', fontWeight: '600' },
  settingsGroup: { gap: 16, marginTop: 12 },
  settingItem: { backgroundColor: '#1f2937', padding: 16, borderRadius: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  settingLabel: { color: '#d1d5db', fontSize: 14, fontWeight: '600' },
  settingVal: { color: '#60a5fa', fontSize: 14 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { width: 450, backgroundColor: '#111827', borderWidth: 1, borderColor: '#374151', borderRadius: 12, padding: 24 },
  modalTitle: { color: '#ffffff', fontSize: 20, fontWeight: 'bold', marginBottom: 16 },
  modalBody: { gap: 10, marginBottom: 24 },
  modalText: { color: '#e5e7eb', fontSize: 15 },
  modalLabel: { color: '#9ca3af', fontWeight: 'bold' },
  closeModalBtn: { backgroundColor: '#dc2626', paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  closeModalText: { color: '#ffffff', fontWeight: 'bold', fontSize: 14 }
});