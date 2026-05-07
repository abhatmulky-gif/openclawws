import { StatusBar } from 'expo-status-bar';
import {
  StyleSheet, Text, View, TouchableOpacity,
  SafeAreaView, ScrollView,
} from 'react-native';
import React, { useState, useEffect, useCallback } from 'react';
import * as Network from 'expo-network';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:5000';
const CPE_ID = 'CPE-MOBILE-001';
const POLL_INTERVAL_MS = 5000;

// Maps expo-network type to intelligence tier label
function getTierLabel(networkType) {
  if (networkType === 'cellular') return 'Tier 1 — Standards-Based (TR-369)';
  if (networkType === 'wifi') return 'Tier 1 — TR-369 (Wi-Fi path)';
  return 'Tier 1 — Connecting...';
}

function getThermalState(txPower) {
  if (txPower >= 25.5) return 'THROTTLING';
  if (txPower >= 24.0) return 'WARM';
  return 'NORMAL';
}

function getHopLabel(sinr, bler, thermal) {
  if (thermal === 'THROTTLING') return 'THERMAL-LIMITED';
  if (sinr < 5.0) return 'UPLINK-CONSTRAINED';
  if (bler > 8.0) return 'INTERFERENCE-BOUND';
  if (sinr >= 15.0) return 'PREMIUM-TIER';
  return 'BALANCED';
}

function getAutonomyAction(sinr, rank) {
  if (sinr < 5.0 && rank === 2) return { text: 'Rank 2→1 queued', color: '#4ade80' };
  if (sinr >= 5.0 && rank === 1) return { text: 'Rank 1→2 eligible', color: '#38bdf8' };
  return { text: 'No action needed', color: '#64748b' };
}

export default function App() {
  const [monitoring, setMonitoring] = useState(false);
  const [networkType, setNetworkType] = useState('UNKNOWN');
  const [latency, setLatency] = useState(null);

  // FWA-specific uplink metrics
  const [sinr, setSinr] = useState(null);
  const [rsrp, setRsrp] = useState(null);
  const [rsrq, setRsrq] = useState(null);
  const [txPower, setTxPower] = useState(null);
  const [mimoRank, setMimoRank] = useState(null);
  const [ulThroughput, setUlThroughput] = useState(null);
  const [dlThroughput, setDlThroughput] = useState(null);
  const [ulBler, setUlBler] = useState(null);
  const [phr, setPhr] = useState(null);

  const [hop, setHop] = useState('UNKNOWN');
  const [lastBackendStatus, setLastBackendStatus] = useState(null);
  const [logs, setLogs] = useState([]);

  const addLog = useCallback((msg) => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 8));
  }, []);

  const measureLatency = async () => {
    const start = Date.now();
    try {
      await fetch('https://1.1.1.1', { method: 'HEAD', cache: 'no-cache' });
    } catch (_) {}
    return Date.now() - start;
  };

  // Simulate FWA CPE radio metrics (replace with native module or TR-369 bridge in production)
  const simulateCpeMetrics = (rtt) => {
    // Simulate realistic SINR/RSRP variation for a static FWA CPE
    const baseSinr = 8.5;
    const sinrJitter = (Math.random() - 0.5) * 6;
    const s = parseFloat((baseSinr + sinrJitter).toFixed(1));

    const baseRsrp = -92;
    const r = Math.floor(baseRsrp + (Math.random() - 0.5) * 10);

    const rsrqVal = parseFloat((-10 + (Math.random() - 0.5) * 4).toFixed(1));

    // Rank: FWA CPE stays at rank 2 unless SINR drops below threshold
    const rank = s < 5.0 ? 1 : 2;

    const txP = parseFloat((23.0 + Math.random() * 3).toFixed(1));
    const ul = parseFloat((s > 10 ? 55 + Math.random() * 30 : 10 + Math.random() * 25).toFixed(1));
    const dl = parseFloat((ul * 1.8 + Math.random() * 10).toFixed(1));
    const bler = parseFloat((s < 5 ? 12 + Math.random() * 8 : Math.random() * 4).toFixed(1));
    const phrVal = parseFloat((s > 8 ? 2 + Math.random() * 3 : -3 + Math.random() * 2).toFixed(1));

    return { sinr: s, rsrp: r, rsrq: rsrqVal, rank, txPower: txP, ul, dl, bler, phr: phrVal };
  };

  const pollNetwork = useCallback(async () => {
    const state = await Network.getNetworkStateAsync();
    const type = state.type || 'UNKNOWN';
    setNetworkType(type);

    const rtt = await measureLatency();
    setLatency(rtt);

    const metrics = simulateCpeMetrics(rtt);
    setSinr(metrics.sinr);
    setRsrp(metrics.rsrp);
    setRsrq(metrics.rsrq);
    setTxPower(metrics.txPower);
    setMimoRank(metrics.rank);
    setUlThroughput(metrics.ul);
    setDlThroughput(metrics.dl);
    setUlBler(metrics.bler);
    setPhr(metrics.phr);

    const thermal = getThermalState(metrics.txPower);
    const hopLabel = getHopLabel(metrics.sinr, metrics.bler, thermal);
    setHop(hopLabel);

    // Build TR-369-style payload for ASTRA backend (Tier 1)
    const payload = {
      source: 'tr369',
      cpe_id: CPE_ID,
      cpe_vendor: 'Mobile-Client',
      ts: Date.now() / 1000,
      poll_interval_s: POLL_INTERVAL_MS / 1000,
      'Device.Cellular.Interface': {
        X_RSRP: metrics.rsrp,
        X_RSRQ: metrics.rsrq,
        X_SINR: metrics.sinr,
        TransmitPower: metrics.txPower,
        X_MIMORank: metrics.rank,
        X_ServingCellId: '310410-FWA-001',
        Stats: {
          BytesSent: Math.floor(metrics.ul * 1e6 * POLL_INTERVAL_MS / 8000),
          BytesReceived: Math.floor(metrics.dl * 1e6 * POLL_INTERVAL_MS / 8000),
        },
      },
      'Device.DeviceInfo.TemperatureStatus': {
        Value: thermal === 'THROTTLING' ? 75 : thermal === 'WARM' ? 65 : 45,
      },
    };

    try {
      const resp = await fetch(`${BACKEND_URL}/cpe/telemetry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      setLastBackendStatus(`Confidence: ${result.confidence_score}`);
      addLog(`Telemetry accepted — HOP: ${hopLabel}, Tier: ${result.intelligence_tier}`);
    } catch (_) {
      setLastBackendStatus('Backend unreachable');
      addLog(`SINR: ${metrics.sinr}dB | Rank: ${metrics.rank} | UL: ${metrics.ul}Mbps [offline]`);
    }
  }, [addLog]);

  useEffect(() => {
    let interval;
    if (monitoring) {
      pollNetwork();
      interval = setInterval(pollNetwork, POLL_INTERVAL_MS);
    }
    return () => clearInterval(interval);
  }, [monitoring, pollNetwork]);

  const thermal = txPower ? getThermalState(txPower) : 'UNKNOWN';
  const autoAction = sinr !== null && mimoRank !== null
    ? getAutonomyAction(sinr, mimoRank)
    : null;

  const hopColor = {
    'UPLINK-CONSTRAINED': '#f87171',
    'THERMAL-LIMITED':    '#fb923c',
    'INTERFERENCE-BOUND': '#facc15',
    'CAPACITY-STARVED':   '#f87171',
    'PREMIUM-TIER':       '#4ade80',
    'BALANCED':           '#38bdf8',
    'UNKNOWN':            '#64748b',
  }[hop] || '#64748b';

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        <Text style={styles.header}>ASTRA FWA</Text>
        <Text style={styles.subheader}>CPE Quality Monitor</Text>

        {/* Household Outcome Profile */}
        <View style={[styles.hopBadge, { borderColor: hopColor }]}>
          <Text style={styles.hopLabel}>Household Outcome Profile</Text>
          <Text style={[styles.hopValue, { color: hopColor }]}>{hop}</Text>
          <Text style={styles.tierLabel}>{getTierLabel(networkType)}</Text>
        </View>

        {/* Uplink metrics — FWA's Achilles' heel */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Uplink Intelligence</Text>

          <View style={styles.row}>
            <MetricBox label="SINR" value={sinr} unit="dB"
              color={sinr === null ? '#64748b' : sinr < 5 ? '#f87171' : sinr < 10 ? '#facc15' : '#4ade80'} />
            <MetricBox label="MIMO Rank" value={mimoRank} unit=""
              color={mimoRank === 1 ? '#facc15' : '#4ade80'} />
          </View>

          <View style={styles.row}>
            <MetricBox label="UL Throughput" value={ulThroughput} unit="Mbps"
              color={ulThroughput === null ? '#64748b' : ulThroughput < 10 ? '#f87171' : '#4ade80'} />
            <MetricBox label="UL BLER" value={ulBler} unit="%"
              color={ulBler === null ? '#64748b' : ulBler > 10 ? '#f87171' : ulBler > 5 ? '#facc15' : '#4ade80'} />
          </View>

          <View style={styles.row}>
            <MetricBox label="Power Headroom" value={phr} unit="dB"
              color={phr === null ? '#64748b' : phr < 0 ? '#f87171' : '#4ade80'} />
            <MetricBox label="Tx Power" value={txPower} unit="dBm"
              color={thermal === 'THROTTLING' ? '#f87171' : thermal === 'WARM' ? '#facc15' : '#4ade80'} />
          </View>
        </View>

        {/* Signal quality */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Signal Quality</Text>
          <View style={styles.row}>
            <MetricBox label="RSRP" value={rsrp} unit="dBm"
              color={rsrp === null ? '#64748b' : rsrp < -110 ? '#f87171' : rsrp < -95 ? '#facc15' : '#4ade80'} />
            <MetricBox label="RSRQ" value={rsrq} unit="dB"
              color={rsrq === null ? '#64748b' : rsrq < -15 ? '#f87171' : '#4ade80'} />
          </View>
          <View style={styles.row}>
            <MetricBox label="DL Throughput" value={dlThroughput} unit="Mbps"
              color='#38bdf8' />
            <MetricBox label="Latency" value={latency} unit="ms"
              color={latency === null ? '#64748b' : latency > 100 ? '#f87171' : '#4ade80'} />
          </View>
        </View>

        {/* Thermal state */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>CPE Thermal State</Text>
          <View style={[styles.thermalBadge,
            { borderColor: thermal === 'THROTTLING' ? '#f87171' : thermal === 'WARM' ? '#fb923c' : '#4ade80' }]}>
            <Text style={[styles.thermalText,
              { color: thermal === 'THROTTLING' ? '#f87171' : thermal === 'WARM' ? '#fb923c' : '#4ade80' }]}>
              {thermal}
            </Text>
          </View>
        </View>

        {/* Autonomy engine hint */}
        {autoAction && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>ASTRA Autonomy</Text>
            <View style={[styles.actionBadge, { borderColor: autoAction.color }]}>
              <Text style={[styles.actionText, { color: autoAction.color }]}>{autoAction.text}</Text>
            </View>
          </View>
        )}

        {/* Control */}
        <TouchableOpacity
          style={[styles.button, monitoring ? styles.buttonStop : styles.buttonStart]}
          onPress={() => setMonitoring(!monitoring)}
        >
          <Text style={styles.buttonText}>
            {monitoring ? 'STOP MONITORING' : 'START MONITORING'}
          </Text>
        </TouchableOpacity>

        {/* Backend status */}
        {lastBackendStatus && (
          <Text style={styles.backendStatus}>ASTRA Backend: {lastBackendStatus}</Text>
        )}

        {/* Log feed */}
        <View style={styles.logContainer}>
          <Text style={styles.logTitle}>Event Log</Text>
          {logs.map((log, i) => (
            <Text key={i} style={styles.logText}>{log}</Text>
          ))}
        </View>

      </ScrollView>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}

function MetricBox({ label, value, unit, color }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color: color || '#f8fafc' }]}>
        {value !== null && value !== undefined ? `${value}${unit ? ' ' + unit : ''}` : '—'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  scroll: { alignItems: 'center', paddingTop: 40, paddingBottom: 40, paddingHorizontal: 16 },
  header: { fontSize: 32, fontWeight: 'bold', color: '#38bdf8', letterSpacing: 3 },
  subheader: { fontSize: 14, color: '#64748b', marginBottom: 20, letterSpacing: 1 },

  hopBadge: {
    width: '100%', borderWidth: 1, borderRadius: 12, padding: 16,
    marginBottom: 16, alignItems: 'center', backgroundColor: '#1e293b',
  },
  hopLabel: { color: '#94a3b8', fontSize: 12, marginBottom: 4 },
  hopValue: { fontSize: 20, fontWeight: 'bold', marginBottom: 4 },
  tierLabel: { color: '#475569', fontSize: 11 },

  section: {
    width: '100%', backgroundColor: '#1e293b', borderRadius: 12,
    padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#334155',
  },
  sectionTitle: { color: '#94a3b8', fontSize: 12, marginBottom: 10, fontWeight: '600' },

  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  metricBox: {
    flex: 1, marginHorizontal: 3, backgroundColor: '#0f172a',
    borderRadius: 8, padding: 10, alignItems: 'center',
  },
  metricLabel: { color: '#64748b', fontSize: 10, marginBottom: 4 },
  metricValue: { fontSize: 18, fontWeight: 'bold' },

  thermalBadge: {
    borderWidth: 1, borderRadius: 8, padding: 10, alignItems: 'center',
  },
  thermalText: { fontSize: 16, fontWeight: 'bold' },

  actionBadge: {
    borderWidth: 1, borderRadius: 8, padding: 10, alignItems: 'center',
  },
  actionText: { fontSize: 14, fontWeight: '600' },

  button: {
    paddingVertical: 14, paddingHorizontal: 30, borderRadius: 8,
    width: '100%', alignItems: 'center', marginTop: 8, marginBottom: 8,
  },
  buttonStart: { backgroundColor: '#0ea5e9' },
  buttonStop: { backgroundColor: '#ef4444' },
  buttonText: { color: 'white', fontSize: 16, fontWeight: 'bold' },

  backendStatus: { color: '#475569', fontSize: 11, marginBottom: 8 },

  logContainer: { width: '100%', marginTop: 8 },
  logTitle: { color: '#94a3b8', marginBottom: 6, fontWeight: 'bold', fontSize: 12 },
  logText: { color: '#475569', fontFamily: 'monospace', fontSize: 10, marginBottom: 3 },
});
