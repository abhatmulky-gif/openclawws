import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, TouchableOpacity, SafeAreaView } from 'react-native';
import React, { useState, useEffect } from 'react';
import * as Network from 'expo-network';

export default function App() {
  const [monitoring, setMonitoring] = useState(false);
  const [latency, setLatency] = useState(0);
  const [networkType, setNetworkType] = useState('UNKNOWN');
  const [logs, setLogs] = useState([]);

  // Mock checking latency by pinging our backend (or a public DNS for demo)
  const measureLatency = async () => {
    const start = Date.now();
    try {
      // Pinging a fast, reliable endpoint to simulate RTT
      await fetch('https://1.1.1.1', { method: 'HEAD', cache: 'no-cache' });
      return Date.now() - start;
    } catch (e) {
      return Date.now() - start; // will be high if it fails/times out
    }
  };

  const pollNetwork = async () => {
    const state = await Network.getNetworkStateAsync();
    const type = state.type || 'UNKNOWN';
    setNetworkType(type);
    
    const rtt = await measureLatency();
    setLatency(rtt);
    
    // Create the payload
    const payload = {
      device_id: "Avinash_Mobile",
      timestamp: new Date().toISOString(),
      network: {
        type: type,
        cell_id: "310410-12345-1", // Simulated for Expo
        rsrp: Math.floor(Math.random() * ( -70 - -110 ) + -110), // Mock RSRP
        rsrq: Math.floor(Math.random() * ( -10 - -20 ) + -20)    // Mock RSRQ
      },
      qoe: {
        ping_ms: rtt,
        packet_loss_pct: rtt > 100 ? Math.random() * 5 : 0 // Add loss if latency is high
      }
    };

    setLogs(prev => [JSON.stringify(payload.qoe) + ` [${type}]`, ...prev].slice(0, 5));

    // In a real app, POST this to our Svaya Python Backend
    // fetch('http://YOUR_BACKEND_IP:5000/analyze_capacity', { method: 'POST', body: JSON.stringify(payload) })
  };

  useEffect(() => {
    let interval;
    if (monitoring) {
      pollNetwork(); // initial
      interval = setInterval(pollNetwork, 3000); // Poll every 3s
    }
    return () => clearInterval(interval);
  }, [monitoring]);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>Svaya QoE Agent</Text>
      
      <View style={styles.card}>
        <Text style={styles.label}>Network Type:</Text>
        <Text style={styles.value}>{networkType}</Text>
        
        <Text style={styles.label}>Latency (RTT):</Text>
        <Text style={[styles.value, latency > 100 ? styles.danger : styles.safe]}>
          {latency} ms
        </Text>
      </View>

      <TouchableOpacity 
        style={[styles.button, monitoring ? styles.buttonStop : styles.buttonStart]} 
        onPress={() => setMonitoring(!monitoring)}
      >
        <Text style={styles.buttonText}>
          {monitoring ? 'STOP MONITORING' : 'START MONITORING'}
        </Text>
      </TouchableOpacity>

      <View style={styles.logContainer}>
        <Text style={styles.logTitle}>Recent Payload Logs:</Text>
        {logs.map((log, i) => (
          <Text key={i} style={styles.logText}>{log}</Text>
        ))}
      </View>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    paddingTop: 50,
  },
  header: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#38bdf8',
    marginBottom: 30,
  },
  card: {
    backgroundColor: '#1e293b',
    padding: 20,
    borderRadius: 12,
    width: '85%',
    marginBottom: 30,
    borderWidth: 1,
    borderColor: '#334155'
  },
  label: {
    color: '#94a3b8',
    fontSize: 16,
    marginBottom: 5,
  },
  value: {
    color: '#f8fafc',
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  safe: {
    color: '#4ade80',
  },
  danger: {
    color: '#f87171',
  },
  button: {
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 8,
    width: '85%',
    alignItems: 'center',
  },
  buttonStart: {
    backgroundColor: '#0ea5e9',
  },
  buttonStop: {
    backgroundColor: '#ef4444',
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  logContainer: {
    marginTop: 40,
    width: '85%',
  },
  logTitle: {
    color: '#94a3b8',
    marginBottom: 10,
    fontWeight: 'bold',
  },
  logText: {
    color: '#cbd5e1',
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 5,
  }
});