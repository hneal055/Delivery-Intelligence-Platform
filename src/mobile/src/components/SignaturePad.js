import React, { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  PanResponder,
} from "react-native";
import Svg, { Path } from "react-native-svg";

export default function SignaturePad({ onConfirm, onCancel }) {
  const [paths, setPaths] = useState([]);
  const [currentPath, setCurrentPath] = useState("");
  const isDrawing = useRef(false);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        const { locationX, locationY } = evt.nativeEvent;
        isDrawing.current = true;
        setCurrentPath(`M ${locationX} ${locationY}`);
      },
      onPanResponderMove: (evt) => {
        if (!isDrawing.current) return;
        const { locationX, locationY } = evt.nativeEvent;
        setCurrentPath((prev) => `${prev} L ${locationX} ${locationY}`);
      },
      onPanResponderRelease: () => {
        if (!isDrawing.current) return;
        isDrawing.current = false;
        setCurrentPath((prev) => {
          if (prev) {
            setPaths((p) => [...p, prev]);
          }
          return "";
        });
      },
    })
  ).current;

  const handleClear = () => {
    setPaths([]);
    setCurrentPath("");
  };

  const handleSave = () => {
    if (paths.length === 0 && !currentPath) {
      alert("Please provide a recipient signature before confirming.");
      return;
    }
    const fullSvgData = [...paths, currentPath].filter(Boolean).join(" ");
    onConfirm(fullSvgData);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.headerTitle}>Recipient Signature</Text>
      <Text style={styles.subtitle}>Please sign inside the box below to accept delivery</Text>

      {/* Drawing Canvas */}
      <View style={styles.canvasWrapper} {...panResponder.panHandlers}>
        <Svg style={StyleSheet.absoluteFill}>
          {paths.map((d, index) => (
            <Path
              key={index}
              d={d}
              stroke="#0f172a"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          ))}
          {currentPath ? (
            <Path
              d={currentPath}
              stroke="#0f172a"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          ) : null}
        </Svg>

        {/* Signing Guideline */}
        <View style={styles.signLine} />
        <Text style={styles.signHereText}>? SIGN HERE</Text>
      </View>

      {/* Action Buttons */}
      <View style={styles.btnRow}>
        <TouchableOpacity style={styles.clearBtn} onPress={handleClear}>
          <Text style={styles.clearBtnText}>Clear Canvas</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cancelBtn} onPress={onCancel}>
          <Text style={styles.cancelBtnText}>Back</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <Text style={styles.saveBtnText}>Confirm Delivery</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    width: "100%",
    maxWidth: 440,
    elevation: 6,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0f172a",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: "#64748b",
    marginBottom: 16,
  },
  canvasWrapper: {
    height: 180,
    backgroundColor: "#f8fafc",
    borderWidth: 2,
    borderColor: "#cbd5e1",
    borderStyle: "dashed",
    borderRadius: 12,
    position: "relative",
    overflow: "hidden",
    justifyContent: "flex-end",
  },
  signLine: {
    height: 1,
    backgroundColor: "#94a3b8",
    marginHorizontal: 20,
    marginBottom: 28,
  },
  signHereText: {
    position: "absolute",
    bottom: 8,
    left: 20,
    fontSize: 10,
    fontWeight: "700",
    color: "#94a3b8",
    letterSpacing: 1,
  },
  btnRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 18,
    alignItems: "center",
  },
  clearBtn: {
    paddingVertical: 12,
    paddingHorizontal: 12,
    backgroundColor: "#f1f5f9",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#cbd5e1",
  },
  clearBtnText: {
    color: "#475569",
    fontWeight: "600",
    fontSize: 12,
  },
  cancelBtn: {
    paddingVertical: 12,
    paddingHorizontal: 12,
    backgroundColor: "#f8fafc",
    borderRadius: 8,
  },
  cancelBtnText: {
    color: "#64748b",
    fontWeight: "600",
    fontSize: 12,
  },
  saveBtn: {
    flex: 1,
    paddingVertical: 12,
    backgroundColor: "#16a34a",
    borderRadius: 8,
    alignItems: "center",
  },
  saveBtnText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 13,
  },
});
