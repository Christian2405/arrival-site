import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Modal,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';

// ─── Wire Gauge Table (NEC copper, 75°C, single-phase) ──────────────────────
const WIRE_GAUGE_TABLE = [
  { gauge: '14 AWG', amps: 15, maxFt60: 50 },
  { gauge: '12 AWG', amps: 20, maxFt60: 60 },
  { gauge: '10 AWG', amps: 30, maxFt60: 80 },
  { gauge: '8 AWG', amps: 40, maxFt60: 100 },
  { gauge: '6 AWG', amps: 55, maxFt60: 130 },
  { gauge: '4 AWG', amps: 70, maxFt60: 170 },
  { gauge: '3 AWG', amps: 85, maxFt60: 200 },
  { gauge: '2 AWG', amps: 95, maxFt60: 230 },
  { gauge: '1 AWG', amps: 110, maxFt60: 270 },
  { gauge: '1/0 AWG', amps: 125, maxFt60: 310 },
  { gauge: '2/0 AWG', amps: 145, maxFt60: 360 },
  { gauge: '3/0 AWG', amps: 165, maxFt60: 420 },
  { gauge: '4/0 AWG', amps: 195, maxFt60: 490 },
];

// ─── Circular mils for voltage drop calc ─────────────────────────────────────
const CIRCULAR_MILS: Record<string, number> = {
  '14': 4110, '12': 6530, '10': 10380, '8': 16510,
  '6': 26240, '4': 41740, '3': 52620, '2': 66360,
  '1': 83690, '1/0': 105600, '2/0': 133100, '3/0': 167800, '4/0': 211600,
};

// ─── P/T Chart data (common refrigerants, psi/°F) ───────────────────────────
const PT_DATA: Record<string, { temp: number; psi: number }[]> = {
  'R-410A': [
    { temp: 20, psi: 80.1 }, { temp: 25, psi: 88.2 }, { temp: 30, psi: 96.8 },
    { temp: 35, psi: 106.0 }, { temp: 40, psi: 115.6 }, { temp: 45, psi: 125.9 },
    { temp: 50, psi: 136.7 }, { temp: 55, psi: 148.2 }, { temp: 60, psi: 160.3 },
    { temp: 65, psi: 173.1 }, { temp: 70, psi: 186.6 }, { temp: 75, psi: 200.9 },
    { temp: 80, psi: 215.9 }, { temp: 85, psi: 231.8 }, { temp: 90, psi: 248.5 },
    { temp: 95, psi: 266.1 }, { temp: 100, psi: 284.6 }, { temp: 105, psi: 304.0 },
    { temp: 110, psi: 324.5 }, { temp: 115, psi: 345.9 }, { temp: 120, psi: 368.4 },
  ],
  'R-22': [
    { temp: 20, psi: 43.0 }, { temp: 25, psi: 47.5 }, { temp: 30, psi: 52.4 },
    { temp: 35, psi: 57.5 }, { temp: 40, psi: 63.0 }, { temp: 45, psi: 68.8 },
    { temp: 50, psi: 75.0 }, { temp: 55, psi: 81.6 }, { temp: 60, psi: 88.5 },
    { temp: 65, psi: 95.9 }, { temp: 70, psi: 103.7 }, { temp: 75, psi: 111.9 },
    { temp: 80, psi: 120.6 }, { temp: 85, psi: 129.8 }, { temp: 90, psi: 139.5 },
    { temp: 95, psi: 149.7 }, { temp: 100, psi: 160.4 }, { temp: 105, psi: 171.7 },
    { temp: 110, psi: 183.6 }, { temp: 115, psi: 196.1 }, { temp: 120, psi: 209.2 },
  ],
  'R-134a': [
    { temp: 20, psi: 18.4 }, { temp: 25, psi: 21.0 }, { temp: 30, psi: 23.8 },
    { temp: 35, psi: 26.9 }, { temp: 40, psi: 30.2 }, { temp: 45, psi: 33.7 },
    { temp: 50, psi: 37.5 }, { temp: 55, psi: 41.6 }, { temp: 60, psi: 46.0 },
    { temp: 65, psi: 50.7 }, { temp: 70, psi: 55.7 }, { temp: 75, psi: 61.1 },
    { temp: 80, psi: 66.8 }, { temp: 85, psi: 72.9 }, { temp: 90, psi: 79.5 },
    { temp: 95, psi: 86.4 }, { temp: 100, psi: 93.8 }, { temp: 105, psi: 101.6 },
    { temp: 110, psi: 110.0 }, { temp: 115, psi: 118.8 }, { temp: 120, psi: 128.2 },
  ],
  'R-407C': [
    { temp: 20, psi: 42.8 }, { temp: 25, psi: 47.7 }, { temp: 30, psi: 52.9 },
    { temp: 35, psi: 58.5 }, { temp: 40, psi: 64.5 }, { temp: 45, psi: 70.9 },
    { temp: 50, psi: 77.7 }, { temp: 55, psi: 85.0 }, { temp: 60, psi: 92.7 },
    { temp: 65, psi: 101.0 }, { temp: 70, psi: 109.7 }, { temp: 75, psi: 119.0 },
    { temp: 80, psi: 128.9 }, { temp: 85, psi: 139.4 }, { temp: 90, psi: 150.4 },
    { temp: 95, psi: 162.2 }, { temp: 100, psi: 174.5 }, { temp: 105, psi: 187.6 },
    { temp: 110, psi: 201.3 }, { temp: 115, psi: 215.9 }, { temp: 120, psi: 231.2 },
  ],
};

// ─── Pipe sizing by flow rate (simplified GPM → nominal pipe) ─────────────
const PIPE_TABLE = [
  { size: '½"', minGPM: 0, maxGPM: 3 },
  { size: '¾"', minGPM: 3, maxGPM: 6 },
  { size: '1"', minGPM: 6, maxGPM: 12 },
  { size: '1¼"', minGPM: 12, maxGPM: 22 },
  { size: '1½"', minGPM: 22, maxGPM: 35 },
  { size: '2"', minGPM: 35, maxGPM: 60 },
  { size: '2½"', minGPM: 60, maxGPM: 90 },
  { size: '3"', minGPM: 90, maxGPM: 160 },
  { size: '4"', minGPM: 160, maxGPM: 300 },
];

type ToolId = 'wire-gauge' | 'voltage-drop' | 'ohms-law' | 'pipe-sizing' | 'pt-chart';

interface Tool {
  id: ToolId;
  name: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  description: string;
  category: string;
}

const TOOLS: Tool[] = [
  { id: 'wire-gauge', name: 'Wire Gauge', icon: 'git-branch-outline', color: '#4A90D9', description: 'Amperage & distance', category: 'Electrical' },
  { id: 'voltage-drop', name: 'Voltage Drop', icon: 'flash-outline', color: '#E8A84C', description: 'Wire run calculations', category: 'Electrical' },
  { id: 'ohms-law', name: "Ohm's Law", icon: 'pulse-outline', color: '#34C759', description: 'V = IR calculator', category: 'Electrical' },
  { id: 'pipe-sizing', name: 'Pipe Sizing', icon: 'resize-outline', color: '#5B9BD5', description: 'Flow requirements', category: 'Plumbing' },
  { id: 'pt-chart', name: 'P/T Chart', icon: 'thermometer-outline', color: '#C75450', description: 'Refrigerant lookup', category: 'HVAC' },
];

// ─── Calculator Components ───────────────────────────────────────────────────

function WireGaugeCalc() {
  const [amps, setAmps] = useState('');
  const result = amps
    ? WIRE_GAUGE_TABLE.find((w) => w.amps >= parseFloat(amps))
    : null;

  return (
    <View style={s.calcBody}>
      <Text style={s.calcLabel}>Load (Amps)</Text>
      <TextInput
        style={s.calcInput}
        keyboardType="numeric"
        placeholder="e.g. 30"
        placeholderTextColor="#C7C2BC"
        value={amps}
        onChangeText={setAmps}
      />
      {result ? (
        <View style={s.resultCard}>
          <Text style={s.resultTitle}>Recommended</Text>
          <Text style={s.resultValue}>{result.gauge}</Text>
          <Text style={s.resultDetail}>
            Rated for {result.amps}A  •  Up to ~{result.maxFt60} ft
          </Text>
        </View>
      ) : amps ? (
        <Text style={s.resultHint}>Load exceeds standard table. Consult an engineer.</Text>
      ) : null}
      <Text style={s.disclaimer}>Based on NEC copper, 75°C, single-phase. Always verify with local codes.</Text>
    </View>
  );
}

function VoltageDropCalc() {
  const [voltage, setVoltage] = useState('120');
  const [amps, setAmps] = useState('');
  const [distance, setDistance] = useState('');
  const [gauge, setGauge] = useState('12');

  const cm = CIRCULAR_MILS[gauge];
  const v = parseFloat(voltage);
  const a = parseFloat(amps);
  const d = parseFloat(distance);
  const isValid = cm && v && a && d;

  // VD = (2 × K × I × D) / CM  where K=12.9 for copper
  const vDrop = isValid ? (2 * 12.9 * a * d) / cm : 0;
  const pct = isValid ? (vDrop / v) * 100 : 0;

  return (
    <View style={s.calcBody}>
      <View style={s.calcRow}>
        <View style={s.calcHalf}>
          <Text style={s.calcLabel}>Voltage</Text>
          <TextInput style={s.calcInput} keyboardType="numeric" value={voltage} onChangeText={setVoltage} placeholder="120" placeholderTextColor="#C7C2BC" />
        </View>
        <View style={s.calcHalf}>
          <Text style={s.calcLabel}>Amps</Text>
          <TextInput style={s.calcInput} keyboardType="numeric" value={amps} onChangeText={setAmps} placeholder="20" placeholderTextColor="#C7C2BC" />
        </View>
      </View>
      <View style={s.calcRow}>
        <View style={s.calcHalf}>
          <Text style={s.calcLabel}>Distance (ft)</Text>
          <TextInput style={s.calcInput} keyboardType="numeric" value={distance} onChangeText={setDistance} placeholder="100" placeholderTextColor="#C7C2BC" />
        </View>
        <View style={s.calcHalf}>
          <Text style={s.calcLabel}>Wire Gauge</Text>
          <TextInput style={s.calcInput} keyboardType="default" value={gauge} onChangeText={setGauge} placeholder="12" placeholderTextColor="#C7C2BC" />
        </View>
      </View>
      {isValid && (
        <View style={s.resultCard}>
          <Text style={s.resultTitle}>Voltage Drop</Text>
          <Text style={s.resultValue}>{vDrop.toFixed(2)} V ({pct.toFixed(1)}%)</Text>
          <Text style={[s.resultDetail, { color: pct > 3 ? '#C75450' : '#34C759' }]}>
            {pct <= 3 ? '✓ Within NEC 3% recommendation' : '⚠ Exceeds NEC 3% recommendation'}
          </Text>
        </View>
      )}
      <Text style={s.disclaimer}>Formula: VD = (2 × 12.9 × I × D) / CM (copper). Verify with local codes.</Text>
    </View>
  );
}

function OhmsLawCalc() {
  const [volts, setVolts] = useState('');
  const [ampsVal, setAmpsVal] = useState('');
  const [ohms, setOhms] = useState('');

  const v = parseFloat(volts);
  const i = parseFloat(ampsVal);
  const r = parseFloat(ohms);

  let results: { label: string; value: string }[] = [];
  if (v && i) {
    results = [
      { label: 'Resistance (Ω)', value: (v / i).toFixed(2) },
      { label: 'Power (W)', value: (v * i).toFixed(2) },
    ];
  } else if (v && r) {
    results = [
      { label: 'Current (A)', value: (v / r).toFixed(2) },
      { label: 'Power (W)', value: ((v * v) / r).toFixed(2) },
    ];
  } else if (i && r) {
    results = [
      { label: 'Voltage (V)', value: (i * r).toFixed(2) },
      { label: 'Power (W)', value: (i * i * r).toFixed(2) },
    ];
  }

  return (
    <View style={s.calcBody}>
      <Text style={s.calcHint}>Enter any 2 values to calculate the rest</Text>
      <Text style={s.calcLabel}>Voltage (V)</Text>
      <TextInput style={s.calcInput} keyboardType="numeric" value={volts} onChangeText={setVolts} placeholder="—" placeholderTextColor="#C7C2BC" />
      <Text style={s.calcLabel}>Current (A)</Text>
      <TextInput style={s.calcInput} keyboardType="numeric" value={ampsVal} onChangeText={setAmpsVal} placeholder="—" placeholderTextColor="#C7C2BC" />
      <Text style={s.calcLabel}>Resistance (Ω)</Text>
      <TextInput style={s.calcInput} keyboardType="numeric" value={ohms} onChangeText={setOhms} placeholder="—" placeholderTextColor="#C7C2BC" />
      {results.length > 0 && (
        <View style={s.resultCard}>
          {results.map((r) => (
            <View key={r.label} style={s.resultRow}>
              <Text style={s.resultRowLabel}>{r.label}</Text>
              <Text style={s.resultRowValue}>{r.value}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function PipeSizingCalc() {
  const [gpm, setGpm] = useState('');
  const flow = parseFloat(gpm);
  const result = flow ? PIPE_TABLE.find((p) => flow >= p.minGPM && flow < p.maxGPM) : null;

  return (
    <View style={s.calcBody}>
      <Text style={s.calcLabel}>Flow Rate (GPM)</Text>
      <TextInput
        style={s.calcInput}
        keyboardType="numeric"
        placeholder="e.g. 15"
        placeholderTextColor="#C7C2BC"
        value={gpm}
        onChangeText={setGpm}
      />
      {result ? (
        <View style={s.resultCard}>
          <Text style={s.resultTitle}>Recommended Pipe Size</Text>
          <Text style={s.resultValue}>{result.size}</Text>
          <Text style={s.resultDetail}>
            For {result.minGPM}–{result.maxGPM} GPM range
          </Text>
        </View>
      ) : flow && flow >= 300 ? (
        <Text style={s.resultHint}>Flow exceeds standard table. Consult a plumbing engineer.</Text>
      ) : null}
      <Text style={s.disclaimer}>Based on typical copper/PEX sizing at 4–8 fps velocity. Verify with local codes.</Text>
    </View>
  );
}

function PTChartCalc() {
  const [selectedRef, setSelectedRef] = useState<string>('R-410A');
  const refs = Object.keys(PT_DATA);
  const data = PT_DATA[selectedRef];

  return (
    <View style={s.calcBody}>
      <Text style={s.calcLabel}>Refrigerant</Text>
      <View style={s.pillRow}>
        {refs.map((r) => (
          <TouchableOpacity
            key={r}
            style={[s.pill, selectedRef === r && s.pillActive]}
            onPress={() => setSelectedRef(r)}
          >
            <Text style={[s.pillText, selectedRef === r && s.pillTextActive]}>{r}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={s.ptTable}>
        <View style={s.ptHeaderRow}>
          <Text style={s.ptHeaderCell}>Temp (°F)</Text>
          <Text style={s.ptHeaderCell}>Pressure (psi)</Text>
        </View>
        <ScrollView style={s.ptScrollInner} nestedScrollEnabled showsVerticalScrollIndicator={false}>
          {data.map((row) => (
            <View key={row.temp} style={s.ptRow}>
              <Text style={s.ptCell}>{row.temp}°</Text>
              <Text style={s.ptCell}>{row.psi.toFixed(1)}</Text>
            </View>
          ))}
        </ScrollView>
      </View>
      <Text style={s.disclaimer}>Saturation pressure at sea level. Values may differ at altitude.</Text>
    </View>
  );
}

// ─── Main Screen ─────────────────────────────────────────────────────────────

export default function QuickToolsScreen() {
  const router = useRouter();
  const [activeTool, setActiveTool] = useState<ToolId | null>(null);

  const activeToolData = TOOLS.find((t) => t.id === activeTool);

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Quick Tools</Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Subtitle */}
        <Text style={styles.subtitle}>
          Trade calculators for the field
        </Text>

        {/* Tools Grid */}
        <View style={styles.grid}>
          {TOOLS.map((tool) => (
            <TouchableOpacity
              key={tool.id}
              style={styles.toolCard}
              onPress={() => setActiveTool(tool.id)}
              activeOpacity={0.6}
            >
              <View style={styles.toolCardTop}>
                <View style={[styles.toolIcon, { backgroundColor: tool.color + '10' }]}>
                  <Ionicons name={tool.icon} size={24} color={tool.color} />
                </View>
              </View>
              <Text style={styles.toolName}>{tool.name}</Text>
              <Text style={styles.toolDescription}>{tool.description}</Text>
              <View style={[styles.toolCategoryBadge, { backgroundColor: tool.color + '10' }]}>
                <Text style={[styles.toolCategoryText, { color: tool.color }]}>{tool.category}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* AI Tip */}
        <View style={styles.tipCard}>
          <View style={styles.tipLeft}>
            <View style={styles.tipIconWrap}>
              <Ionicons name="sparkles" size={18} color="#D4842A" />
            </View>
          </View>
          <View style={styles.tipContent}>
            <Text style={styles.tipTitle}>Ask the AI instead</Text>
            <Text style={styles.tipText}>
              You can describe any calculation to Arrival and get instant answers with step-by-step breakdowns.
            </Text>
          </View>
        </View>
      </ScrollView>

      {/* Calculator Modal */}
      <Modal
        visible={activeTool !== null}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setActiveTool(null)}
      >
        <KeyboardAvoidingView
          style={s.modalWrap}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <SafeAreaView style={s.modalSafe}>
            {/* Modal Header */}
            <View style={s.modalHeader}>
              <View style={s.modalHeaderLeft}>
                {activeToolData && (
                  <View style={[s.modalIcon, { backgroundColor: activeToolData.color + '10' }]}>
                    <Ionicons name={activeToolData.icon} size={20} color={activeToolData.color} />
                  </View>
                )}
                <Text style={s.modalTitle}>{activeToolData?.name}</Text>
              </View>
              <TouchableOpacity onPress={() => setActiveTool(null)} style={s.closeBtn}>
                <Ionicons name="close" size={22} color="#2A2622" />
              </TouchableOpacity>
            </View>

            <ScrollView
              style={s.modalScroll}
              contentContainerStyle={s.modalScrollContent}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              {activeTool === 'wire-gauge' && <WireGaugeCalc />}
              {activeTool === 'voltage-drop' && <VoltageDropCalc />}
              {activeTool === 'ohms-law' && <OhmsLawCalc />}
              {activeTool === 'pipe-sizing' && <PipeSizingCalc />}
              {activeTool === 'pt-chart' && <PTChartCalc />}
            </ScrollView>
          </SafeAreaView>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Grid/Page Styles ────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F0EB' },
  header: { paddingHorizontal: 20, paddingVertical: 12 },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#2A2622', letterSpacing: -0.5 },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 40 },
  subtitle: { fontSize: 15, color: '#A09A93', marginBottom: 20, paddingHorizontal: 4, letterSpacing: -0.2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  toolCard: {
    width: '48%', backgroundColor: '#FFFFFF', borderRadius: 16, padding: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1,
  },
  toolCardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
  toolIcon: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  toolName: { fontSize: 15, fontWeight: '700', color: '#2A2622', marginBottom: 3, letterSpacing: -0.2 },
  toolDescription: { fontSize: 12, color: '#A09A93', lineHeight: 17, marginBottom: 10 },
  toolCategoryBadge: { alignSelf: 'flex-start', paddingHorizontal: 7, paddingVertical: 2, borderRadius: 5 },
  toolCategoryText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.3 },
  tipCard: {
    flexDirection: 'row', backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, marginTop: 20, gap: 14,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1,
  },
  tipLeft: {},
  tipIconWrap: { width: 38, height: 38, borderRadius: 12, backgroundColor: '#D4842A10', justifyContent: 'center', alignItems: 'center' },
  tipContent: { flex: 1 },
  tipTitle: { fontSize: 14, fontWeight: '700', color: '#2A2622', marginBottom: 4, letterSpacing: -0.2 },
  tipText: { fontSize: 13, color: '#A09A93', lineHeight: 19 },
});

// ─── Calculator / Modal Styles ───────────────────────────────────────────────

const s = StyleSheet.create({
  modalWrap: { flex: 1, backgroundColor: '#F3F0EB' },
  modalSafe: { flex: 1 },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#EBE7E2',
  },
  modalHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  modalIcon: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#2A2622', letterSpacing: -0.3 },
  closeBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#EBE7E2', justifyContent: 'center', alignItems: 'center' },
  modalScroll: { flex: 1 },
  modalScrollContent: { padding: 16, paddingBottom: 40 },

  // Calculator common
  calcBody: {},
  calcLabel: { fontSize: 13, fontWeight: '600', color: '#2A2622', marginBottom: 6, marginTop: 12, letterSpacing: -0.1 },
  calcHint: { fontSize: 13, color: '#A09A93', lineHeight: 19, marginBottom: 4 },
  calcInput: {
    backgroundColor: '#FFFFFF', borderRadius: 12, height: 48, paddingHorizontal: 14,
    fontSize: 16, color: '#2A2622', letterSpacing: -0.2,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.03, shadowRadius: 4, elevation: 1,
  },
  calcRow: { flexDirection: 'row', gap: 10 },
  calcHalf: { flex: 1 },

  // Results
  resultCard: {
    backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, marginTop: 16,
    borderLeftWidth: 3, borderLeftColor: Colors.accent,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1,
  },
  resultTitle: { fontSize: 12, fontWeight: '600', color: '#A09A93', letterSpacing: 0.5, textTransform: 'uppercase', marginBottom: 4 },
  resultValue: { fontSize: 28, fontWeight: '800', color: '#2A2622', letterSpacing: -0.5, marginBottom: 4 },
  resultDetail: { fontSize: 14, color: '#A09A93', lineHeight: 20 },
  resultHint: { fontSize: 14, color: '#E8A84C', marginTop: 12, fontWeight: '500' },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  resultRowLabel: { fontSize: 14, color: '#A09A93' },
  resultRowValue: { fontSize: 18, fontWeight: '700', color: '#2A2622' },

  disclaimer: { fontSize: 11, color: '#C7C2BC', marginTop: 16, lineHeight: 16, fontStyle: 'italic' },

  // P/T chart
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4, marginBottom: 8 },
  pill: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#FFFFFF' },
  pillActive: { backgroundColor: '#2A2622' },
  pillText: { fontSize: 13, fontWeight: '600', color: '#2A2622' },
  pillTextActive: { color: '#FFFFFF' },

  ptTable: {
    backgroundColor: '#FFFFFF', borderRadius: 14, overflow: 'hidden', marginTop: 8,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1,
  },
  ptHeaderRow: { flexDirection: 'row', paddingVertical: 10, paddingHorizontal: 16, backgroundColor: '#F3F0EB' },
  ptHeaderCell: { flex: 1, fontSize: 12, fontWeight: '700', color: '#A09A93', letterSpacing: 0.3, textTransform: 'uppercase' },
  ptScrollInner: { maxHeight: 340 },
  ptRow: {
    flexDirection: 'row', paddingVertical: 10, paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#F3F0EB',
  },
  ptCell: { flex: 1, fontSize: 15, color: '#2A2622', fontVariant: ['tabular-nums'] },
});
