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
import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';

// ─── Wire Gauge Table (NEC Table 310.16, copper, 75°C, single-phase) ────────
const WIRE_GAUGE_TABLE = [
  { gauge: '14 AWG', amps: 20, maxFt60: 50 },
  { gauge: '12 AWG', amps: 25, maxFt60: 60 },
  { gauge: '10 AWG', amps: 35, maxFt60: 80 },
  { gauge: '8 AWG', amps: 50, maxFt60: 100 },
  { gauge: '6 AWG', amps: 65, maxFt60: 130 },
  { gauge: '4 AWG', amps: 85, maxFt60: 170 },
  { gauge: '3 AWG', amps: 100, maxFt60: 200 },
  { gauge: '2 AWG', amps: 115, maxFt60: 230 },
  { gauge: '1 AWG', amps: 130, maxFt60: 270 },
  { gauge: '1/0 AWG', amps: 150, maxFt60: 310 },
  { gauge: '2/0 AWG', amps: 175, maxFt60: 360 },
  { gauge: '3/0 AWG', amps: 200, maxFt60: 420 },
  { gauge: '4/0 AWG', amps: 230, maxFt60: 490 },
];

// ─── Circular mils for voltage drop calc ─────────────────────────────────────
const GAUGE_OPTIONS = ['14', '12', '10', '8', '6', '4', '3', '2', '1', '1/0', '2/0', '3/0', '4/0'];
const CIRCULAR_MILS: Record<string, number> = {
  '14': 4110, '12': 6530, '10': 10380, '8': 16510,
  '6': 26240, '4': 41740, '3': 52620, '2': 66360,
  '1': 83690, '1/0': 105600, '2/0': 133100, '3/0': 167800, '4/0': 211600,
};

// ─── P/T Chart data (common refrigerants, psi/°F) ───────────────────────────
const PT_DATA: Record<string, { temp: number; psi: number }[]> = {
  'R-410A': [
    { temp: 20, psi: 78.7 }, { temp: 25, psi: 87.8 }, { temp: 30, psi: 97.5 },
    { temp: 35, psi: 107.9 }, { temp: 40, psi: 118.9 }, { temp: 45, psi: 130.7 },
    { temp: 50, psi: 143.3 }, { temp: 55, psi: 156.6 }, { temp: 60, psi: 170.7 },
    { temp: 65, psi: 185.7 }, { temp: 70, psi: 201.5 }, { temp: 75, psi: 218.2 },
    { temp: 80, psi: 235.9 }, { temp: 85, psi: 254.6 }, { temp: 90, psi: 274.3 },
    { temp: 95, psi: 295.0 }, { temp: 100, psi: 316.9 }, { temp: 105, psi: 339.9 },
    { temp: 110, psi: 364.1 }, { temp: 115, psi: 389.6 }, { temp: 120, psi: 416.4 },
  ],
  'R-22': [
    { temp: 20, psi: 43.1 }, { temp: 25, psi: 48.8 }, { temp: 30, psi: 54.9 },
    { temp: 35, psi: 61.5 }, { temp: 40, psi: 68.6 }, { temp: 45, psi: 76.1 },
    { temp: 50, psi: 84.1 }, { temp: 55, psi: 92.6 }, { temp: 60, psi: 101.6 },
    { temp: 65, psi: 111.3 }, { temp: 70, psi: 121.5 }, { temp: 75, psi: 132.2 },
    { temp: 80, psi: 143.7 }, { temp: 85, psi: 155.7 }, { temp: 90, psi: 168.4 },
    { temp: 95, psi: 181.9 }, { temp: 100, psi: 196.0 }, { temp: 105, psi: 210.8 },
    { temp: 110, psi: 226.4 }, { temp: 115, psi: 242.8 }, { temp: 120, psi: 260.0 },
  ],
  'R-134a': [
    { temp: 20, psi: 18.4 }, { temp: 25, psi: 22.1 }, { temp: 30, psi: 26.1 },
    { temp: 35, psi: 30.4 }, { temp: 40, psi: 35.0 }, { temp: 45, psi: 40.0 },
    { temp: 50, psi: 45.4 }, { temp: 55, psi: 51.2 }, { temp: 60, psi: 57.4 },
    { temp: 65, psi: 64.0 }, { temp: 70, psi: 71.1 }, { temp: 75, psi: 78.6 },
    { temp: 80, psi: 86.7 }, { temp: 85, psi: 95.2 }, { temp: 90, psi: 104.3 },
    { temp: 95, psi: 113.9 }, { temp: 100, psi: 124.1 }, { temp: 105, psi: 134.9 },
    { temp: 110, psi: 146.3 }, { temp: 115, psi: 158.4 }, { temp: 120, psi: 171.1 },
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

type ToolId = 'wire-gauge' | 'voltage-drop' | 'ohms-law' | 'pipe-sizing' | 'pt-chart' | 'unit-convert';

interface Tool {
  id: ToolId;
  name: string;
  icon: keyof typeof Ionicons.glyphMap;
  description: string;
  category: string;
}

const TOOLS: Tool[] = [
  { id: 'wire-gauge', name: 'Wire Gauge', icon: 'git-branch-outline', description: 'NEC amperage & distance lookup', category: 'Electrical' },
  { id: 'voltage-drop', name: 'Voltage Drop', icon: 'flash-outline', description: 'Wire run calculations', category: 'Electrical' },
  { id: 'ohms-law', name: "Ohm's Law", icon: 'pulse-outline', description: 'V = IR calculator', category: 'Electrical' },
  { id: 'pipe-sizing', name: 'Pipe Sizing', icon: 'resize-outline', description: 'GPM flow requirements', category: 'Plumbing' },
  { id: 'pt-chart', name: 'P/T Chart', icon: 'thermometer-outline', description: 'Refrigerant pressure lookup', category: 'HVAC' },
  { id: 'unit-convert', name: 'Unit Converter', icon: 'swap-horizontal-outline', description: '°F↔°C, in↔mm, PSI↔kPa & more', category: 'General' },
];

// ─── Shared input field component ────────────────────────────────────────────

function InputField({
  label,
  value,
  onChangeText,
  placeholder,
  unit,
  keyboardType = 'numeric',
}: {
  label: string;
  value: string;
  onChangeText: (t: string) => void;
  placeholder: string;
  unit?: string;
  keyboardType?: 'numeric' | 'default';
}) {
  return (
    <View style={s.fieldGroup}>
      <Text style={s.fieldLabel}>{label}</Text>
      <View style={s.fieldInputWrap}>
        <TextInput
          style={[s.fieldInput, unit ? { paddingRight: 44 } : undefined]}
          keyboardType={keyboardType}
          placeholder={placeholder}
          placeholderTextColor={Colors.textFaint}
          value={value}
          onChangeText={onChangeText}
        />
        {unit && <Text style={s.fieldUnit}>{unit}</Text>}
      </View>
    </View>
  );
}

// ─── Reset button component ──────────────────────────────────────────────────

function ResetButton({ onPress }: { onPress: () => void }) {
  return (
    <TouchableOpacity style={s.resetBtn} onPress={onPress} activeOpacity={0.6}>
      <Ionicons name="refresh-outline" size={14} color={Colors.textMuted} />
      <Text style={s.resetText}>Reset</Text>
    </TouchableOpacity>
  );
}

// ─── Calculator Components ───────────────────────────────────────────────────

function WireGaugeCalc() {
  const [amps, setAmps] = useState('');
  const result = amps
    ? WIRE_GAUGE_TABLE.find((w) => w.amps >= parseFloat(amps))
    : null;

  return (
    <View style={s.calcBody}>
      <Text style={s.calcDescription}>
        Find the recommended wire gauge for your load. Based on NEC copper conductors at 75°C.
      </Text>

      <InputField
        label="Load"
        value={amps}
        onChangeText={setAmps}
        placeholder="e.g. 30"
        unit="A"
      />

      {result ? (
        <View style={s.resultCard}>
          <Text style={s.resultLabel}>Recommended Wire</Text>
          <Text style={s.resultBig}>{result.gauge}</Text>
          <View style={s.resultDivider} />
          <View style={s.resultDetails}>
            <View style={s.resultDetailItem}>
              <Text style={s.resultDetailLabel}>Max Amperage</Text>
              <Text style={s.resultDetailValue}>{result.amps} A</Text>
            </View>
            <View style={s.resultDetailItem}>
              <Text style={s.resultDetailLabel}>Max Distance</Text>
              <Text style={s.resultDetailValue}>~{result.maxFt60} ft</Text>
            </View>
          </View>
        </View>
      ) : amps ? (
        <View style={s.warningCard}>
          <Ionicons name="alert-circle-outline" size={IconSize.md} color={Colors.textDark} />
          <Text style={s.warningText}>Load exceeds standard table. Consult an engineer.</Text>
        </View>
      ) : (
        <View style={s.hintCard}>
          <Text style={s.hintText}>Enter the amperage load to get a wire gauge recommendation.</Text>
        </View>
      )}

      {amps !== '' && <ResetButton onPress={() => setAmps('')} />}

      <Text style={s.disclaimer}>NEC copper, 75°C, single-phase. Always verify with local codes.</Text>
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

  const reset = () => {
    setVoltage('120');
    setAmps('');
    setDistance('');
    setGauge('12');
  };

  return (
    <View style={s.calcBody}>
      <Text style={s.calcDescription}>
        Calculate voltage drop across a wire run. Formula: VD = (2 × 12.9 × I × D) / CM
      </Text>

      <View style={s.fieldRow}>
        <InputField label="Voltage" value={voltage} onChangeText={setVoltage} placeholder="120" unit="V" />
        <InputField label="Current" value={amps} onChangeText={setAmps} placeholder="20" unit="A" />
      </View>

      <InputField label="One-way Distance" value={distance} onChangeText={setDistance} placeholder="100" unit="ft" />

      {/* Wire Gauge Selector */}
      <View style={s.fieldGroup}>
        <Text style={s.fieldLabel}>Wire Gauge (AWG)</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.gaugeScroll} contentContainerStyle={s.gaugeScrollContent}>
          {GAUGE_OPTIONS.map((g) => (
            <TouchableOpacity
              key={g}
              style={[s.gaugePill, gauge === g && s.gaugePillActive]}
              onPress={() => setGauge(g)}
              activeOpacity={0.7}
            >
              <Text style={[s.gaugePillText, gauge === g && s.gaugePillTextActive]}>{g}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {isValid ? (
        <View style={s.resultCard}>
          <Text style={s.resultLabel}>Voltage Drop</Text>
          <Text style={s.resultBig}>{vDrop.toFixed(2)} V</Text>
          <View style={s.resultDivider} />
          <View style={s.resultDetails}>
            <View style={s.resultDetailItem}>
              <Text style={s.resultDetailLabel}>Percentage</Text>
              <Text style={s.resultDetailValue}>{pct.toFixed(1)}%</Text>
            </View>
            <View style={s.resultDetailItem}>
              <Text style={s.resultDetailLabel}>NEC Limit (3%)</Text>
              <Text style={[s.resultDetailValue, { color: pct > 3 ? Colors.errorMuted : Colors.textDark }]}>
                {pct <= 3 ? '✓ Within limit' : '⚠ Exceeds'}
              </Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={s.hintCard}>
          <Text style={s.hintText}>Fill in all fields to calculate voltage drop.</Text>
        </View>
      )}

      {(amps || distance) && <ResetButton onPress={reset} />}

      <Text style={s.disclaimer}>Copper conductor. Verify with local codes.</Text>
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

  // Bug #45: When all 3 values are entered (overdetermined), prioritize voltage + current
  // and calculate resistance from those, ignoring the manually entered resistance.
  let results: { label: string; value: string; unit: string }[] = [];
  if (v && i) {
    // V + I provided (or all 3) → calculate R and P from V and I
    results = [
      { label: 'Resistance', value: (v / i).toFixed(2), unit: 'Ω' },
      { label: 'Power', value: (v * i).toFixed(2), unit: 'W' },
    ];
  } else if (v && r) {
    results = [
      { label: 'Current', value: (v / r).toFixed(2), unit: 'A' },
      { label: 'Power', value: ((v * v) / r).toFixed(2), unit: 'W' },
    ];
  } else if (i && r) {
    results = [
      { label: 'Voltage', value: (i * r).toFixed(2), unit: 'V' },
      { label: 'Power', value: (i * i * r).toFixed(2), unit: 'W' },
    ];
  }

  const filledCount = [volts, ampsVal, ohms].filter(Boolean).length;

  return (
    <View style={s.calcBody}>
      <Text style={s.calcDescription}>
        Enter any 2 values to calculate the rest. V = I × R
      </Text>

      <InputField label="Voltage" value={volts} onChangeText={setVolts} placeholder="—" unit="V" />
      <InputField label="Current" value={ampsVal} onChangeText={setAmpsVal} placeholder="—" unit="A" />
      <InputField label="Resistance" value={ohms} onChangeText={setOhms} placeholder="—" unit="Ω" />

      {results.length > 0 ? (
        <View style={s.resultCard}>
          <Text style={s.resultLabel}>Results</Text>
          {/* Bug #45: Note when all 3 values are entered */}
          {filledCount === 3 && (
            <Text style={s.disclaimer}>All 3 values entered. Using Voltage + Current; entered Resistance is ignored.</Text>
          )}
          {results.map((r) => (
            <View key={r.label} style={s.ohmsRow}>
              <Text style={s.ohmsLabel}>{r.label}</Text>
              <View style={s.ohmsValueWrap}>
                <Text style={s.ohmsValue}>{r.value}</Text>
                <Text style={s.ohmsUnit}>{r.unit}</Text>
              </View>
            </View>
          ))}
        </View>
      ) : (
        <View style={s.hintCard}>
          <Text style={s.hintText}>
            {filledCount === 0
              ? 'Enter any 2 values above to calculate.'
              : 'Enter one more value to calculate.'}
          </Text>
        </View>
      )}

      {filledCount > 0 && (
        <ResetButton
          onPress={() => {
            setVolts('');
            setAmpsVal('');
            setOhms('');
          }}
        />
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
      <Text style={s.calcDescription}>
        Find the recommended pipe diameter for your flow rate. Based on typical copper/PEX at 4–8 fps.
      </Text>

      <InputField
        label="Flow Rate"
        value={gpm}
        onChangeText={setGpm}
        placeholder="e.g. 15"
        unit="GPM"
      />

      {result ? (
        <View style={s.resultCard}>
          <Text style={s.resultLabel}>Recommended Pipe</Text>
          <Text style={s.resultBig}>{result.size}</Text>
          <View style={s.resultDivider} />
          <View style={s.resultDetails}>
            <View style={s.resultDetailItem}>
              <Text style={s.resultDetailLabel}>Flow Range</Text>
              <Text style={s.resultDetailValue}>{result.minGPM}–{result.maxGPM} GPM</Text>
            </View>
          </View>
        </View>
      ) : flow && flow >= 300 ? (
        <View style={s.warningCard}>
          <Ionicons name="alert-circle-outline" size={IconSize.md} color={Colors.textDark} />
          <Text style={s.warningText}>Flow exceeds standard table. Consult a plumbing engineer.</Text>
        </View>
      ) : (
        <View style={s.hintCard}>
          <Text style={s.hintText}>Enter the flow rate in gallons per minute.</Text>
        </View>
      )}

      {gpm !== '' && <ResetButton onPress={() => setGpm('')} />}

      <Text style={s.disclaimer}>Typical copper/PEX sizing at 4–8 fps velocity. Verify with local codes.</Text>
    </View>
  );
}

function PTChartCalc() {
  const [selectedRef, setSelectedRef] = useState<string>('R-410A');
  const refs = Object.keys(PT_DATA);
  const data = PT_DATA[selectedRef];

  return (
    <View style={s.calcBody}>
      <Text style={s.calcDescription}>
        Saturation pressure at sea level. Select a refrigerant type below.
      </Text>

      {/* Refrigerant selector — larger pills for field use */}
      <View style={s.refSelector}>
        {refs.map((r) => (
          <TouchableOpacity
            key={r}
            style={[s.refPill, selectedRef === r && s.refPillActive]}
            onPress={() => setSelectedRef(r)}
            activeOpacity={0.7}
          >
            <Text style={[s.refPillText, selectedRef === r && s.refPillTextActive]}>{r}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Table */}
      <View style={s.ptTable}>
        <View style={s.ptHeader}>
          <Text style={s.ptHeaderCell}>Temp (°F)</Text>
          <Text style={[s.ptHeaderCell, { textAlign: 'right' }]}>Pressure (psi)</Text>
        </View>
        <ScrollView style={s.ptScroll} nestedScrollEnabled showsVerticalScrollIndicator={false}>
          {data.map((row, i) => (
            <View key={row.temp} style={[s.ptRow, i % 2 === 0 && s.ptRowAlt]}>
              <Text style={s.ptCell}>{row.temp}°</Text>
              <Text style={[s.ptCell, { textAlign: 'right', fontWeight: '600' }]}>{row.psi.toFixed(1)}</Text>
            </View>
          ))}
        </ScrollView>
      </View>

      <Text style={s.disclaimer}>Values may differ at altitude. Always cross-reference with manufacturer data.</Text>
    </View>
  );
}

// ─── Unit Converter ──────────────────────────────────────────────────────────

const CONVERSIONS = [
  { label: '°F ↔ °C',     group: 'Temp',     unitA: '°F',   unitB: '°C',   aToB: (v: number) => (v - 32) * 5 / 9,                   bToA: (v: number) => v * 9 / 5 + 32 },
  { label: 'in ↔ mm',     group: 'Length',    unitA: 'in',   unitB: 'mm',   aToB: (v: number) => v * 25.4,                            bToA: (v: number) => v / 25.4 },
  { label: 'ft ↔ m',      group: 'Length',    unitA: 'ft',   unitB: 'm',    aToB: (v: number) => v * 0.3048,                          bToA: (v: number) => v / 0.3048 },
  { label: 'PSI ↔ kPa',   group: 'Pressure',  unitA: 'PSI',  unitB: 'kPa',  aToB: (v: number) => v * 6.89476,                         bToA: (v: number) => v / 6.89476 },
  { label: 'gal ↔ L',     group: 'Volume',    unitA: 'gal',  unitB: 'L',    aToB: (v: number) => v * 3.78541,                         bToA: (v: number) => v / 3.78541 },
  { label: 'CFM ↔ L/s',   group: 'Flow',      unitA: 'CFM',  unitB: 'L/s',  aToB: (v: number) => v * 0.471947,                        bToA: (v: number) => v / 0.471947 },
  { label: 'BTU ↔ kW',    group: 'Power',     unitA: 'BTU/h', unitB: 'kW',  aToB: (v: number) => v * 0.000293071,                     bToA: (v: number) => v / 0.000293071 },
  { label: 'lb ↔ kg',     group: 'Weight',    unitA: 'lb',   unitB: 'kg',   aToB: (v: number) => v * 0.453592,                        bToA: (v: number) => v / 0.453592 },
];

function UnitConvertCalc() {
  const [selected, setSelected] = useState(0);
  const [valueA, setValueA] = useState('');
  const [valueB, setValueB] = useState('');
  const [lastEdited, setLastEdited] = useState<'A' | 'B'>('A');

  const conv = CONVERSIONS[selected];

  const handleChangeA = (text: string) => {
    setValueA(text);
    setLastEdited('A');
    const num = parseFloat(text);
    if (!isNaN(num)) {
      const result = conv.aToB(num);
      setValueB(result < 0.01 && result > 0 ? result.toPrecision(4) : result.toFixed(2));
    } else {
      setValueB('');
    }
  };

  const handleChangeB = (text: string) => {
    setValueB(text);
    setLastEdited('B');
    const num = parseFloat(text);
    if (!isNaN(num)) {
      const result = conv.bToA(num);
      setValueA(result < 0.01 && result > 0 ? result.toPrecision(4) : result.toFixed(2));
    } else {
      setValueA('');
    }
  };

  const handleSelect = (idx: number) => {
    setSelected(idx);
    const c = CONVERSIONS[idx];
    // Reconvert current value with new conversion
    if (lastEdited === 'A' && valueA) {
      const num = parseFloat(valueA);
      if (!isNaN(num)) setValueB(c.aToB(num).toFixed(2));
    } else if (lastEdited === 'B' && valueB) {
      const num = parseFloat(valueB);
      if (!isNaN(num)) setValueA(c.bToA(num).toFixed(2));
    } else {
      setValueA('');
      setValueB('');
    }
  };

  return (
    <View style={s.calcBody}>
      <Text style={s.calcDescription}>
        Tap a conversion, type in either field. Instant bidirectional conversion.
      </Text>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.gaugeScroll} contentContainerStyle={s.gaugeScrollContent}>
        {CONVERSIONS.map((c, i) => (
          <TouchableOpacity
            key={c.label}
            style={[s.gaugePill, selected === i && s.gaugePillActive]}
            onPress={() => handleSelect(i)}
            activeOpacity={0.7}
          >
            <Text style={[s.gaugePillText, selected === i && s.gaugePillTextActive]}>{c.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <View style={{ marginTop: Spacing.base }}>
        <InputField label={conv.unitA} value={valueA} onChangeText={handleChangeA} placeholder="0" unit={conv.unitA} />
      </View>

      <View style={{ alignItems: 'center', marginVertical: 4 }}>
        <Ionicons name="swap-vertical-outline" size={20} color={Colors.textMuted} />
      </View>

      <InputField label={conv.unitB} value={valueB} onChangeText={handleChangeB} placeholder="0" unit={conv.unitB} />

      {(valueA !== '' || valueB !== '') && (
        <ResetButton onPress={() => { setValueA(''); setValueB(''); }} />
      )}
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
        <TouchableOpacity style={styles.backBtn} onPress={() => router.push('/(tabs)/home')}>
          <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Quick Tools</Text>
        <View style={{ width: IconSize.lg }} />
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
                <View style={styles.toolIcon}>
                  <Ionicons name={tool.icon} size={22} color={Colors.textDark} />
                </View>
              </View>
              <Text style={styles.toolName}>{tool.name}</Text>
              <Text style={styles.toolDescription}>{tool.description}</Text>
              <View style={styles.toolCategoryBadge}>
                <Text style={styles.toolCategoryText}>{tool.category}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* AI Tip */}
        <View style={styles.tipCard}>
          <View style={styles.tipIconWrap}>
            <Ionicons name="sparkles" size={IconSize.md} color={Colors.textDark} />
          </View>
          <View style={styles.tipContent}>
            <Text style={styles.tipTitle}>Ask the AI instead</Text>
            <Text style={styles.tipText}>
              Describe any calculation to Arrival and get instant answers with step-by-step breakdowns.
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
                  <View style={s.modalIcon}>
                    <Ionicons name={activeToolData.icon} size={IconSize.md} color={Colors.textDark} />
                  </View>
                )}
                <View>
                  <Text style={s.modalTitle}>{activeToolData?.name}</Text>
                  <Text style={s.modalCategory}>{activeToolData?.category}</Text>
                </View>
              </View>
              <TouchableOpacity onPress={() => setActiveTool(null)} style={s.closeBtn} activeOpacity={0.6}>
                <Ionicons name="close" size={IconSize.md} color={Colors.textDark} />
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
              {activeTool === 'unit-convert' && <UnitConvertCalc />}
            </ScrollView>
          </SafeAreaView>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Grid/Page Styles ────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.backgroundWarm },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.full,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: { fontSize: FontSize.xl, fontWeight: '800', color: Colors.textDark, letterSpacing: -0.5 },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: Spacing.base, paddingBottom: 40 },
  subtitle: { fontSize: FontSize.base, color: Colors.textMuted, marginBottom: 20, paddingHorizontal: Spacing.xs, letterSpacing: -0.2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  toolCard: {
    width: '48%', backgroundColor: Colors.card, borderRadius: Radius.lg, padding: Spacing.base,
    ...Shadow.medium,
  },
  toolCardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
  toolIcon: { width: 44, height: 44, borderRadius: Radius.md, backgroundColor: Colors.backgroundWarm, justifyContent: 'center', alignItems: 'center' },
  toolName: { fontSize: FontSize.base, fontWeight: '700', color: Colors.textDark, marginBottom: 3, letterSpacing: -0.2 },
  toolDescription: { fontSize: FontSize.xs, color: Colors.textMuted, lineHeight: 17, marginBottom: 10 },
  toolCategoryBadge: { alignSelf: 'flex-start', paddingHorizontal: 7, paddingVertical: 2, borderRadius: Radius.sm, backgroundColor: Colors.backgroundWarm },
  toolCategoryText: { fontSize: FontSize.xs, fontWeight: '700', letterSpacing: 0.3, color: Colors.textMuted },
  tipCard: {
    flexDirection: 'row', backgroundColor: Colors.card, borderRadius: Radius.lg, padding: Spacing.base, marginTop: 20, gap: 14,
    ...Shadow.subtle,
  },
  tipIconWrap: { width: 38, height: 38, borderRadius: Radius.md, backgroundColor: Colors.backgroundWarm, justifyContent: 'center', alignItems: 'center' },
  tipContent: { flex: 1 },
  tipTitle: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.textDark, marginBottom: Spacing.xs, letterSpacing: -0.2 },
  tipText: { fontSize: FontSize.sm, color: Colors.textMuted, lineHeight: 19 },
});

// ─── Calculator / Modal Styles ───────────────────────────────────────────────

const s = StyleSheet.create({
  modalWrap: { flex: 1, backgroundColor: Colors.backgroundWarm },
  modalSafe: { flex: 1 },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 14,
    backgroundColor: Colors.card,
    ...Shadow.subtle,
  },
  modalHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  modalIcon: {
    width: 40, height: 40, borderRadius: Radius.md, backgroundColor: Colors.backgroundWarm,
    justifyContent: 'center', alignItems: 'center',
  },
  modalTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.textDark, letterSpacing: -0.3 },
  modalCategory: { fontSize: FontSize.xs, color: Colors.textMuted, marginTop: 1 },
  closeBtn: {
    width: 36, height: 36, borderRadius: Radius.full, backgroundColor: Colors.backgroundWarm,
    justifyContent: 'center', alignItems: 'center',
  },
  modalScroll: { flex: 1 },
  modalScrollContent: { padding: 20, paddingBottom: 40 },

  // Calculator common
  calcBody: {},
  calcDescription: {
    fontSize: FontSize.sm, color: Colors.textMuted, lineHeight: 20, marginBottom: 20, letterSpacing: -0.1,
  },

  // Field components
  fieldGroup: { marginBottom: Spacing.base },
  fieldLabel: {
    fontSize: FontSize.sm, fontWeight: '600', color: Colors.textDark, marginBottom: Spacing.sm, letterSpacing: -0.1,
  },
  fieldInputWrap: { position: 'relative' },
  fieldInput: {
    backgroundColor: Colors.card, borderRadius: Radius.md, height: 52, paddingHorizontal: Spacing.base,
    fontSize: FontSize.lg, color: Colors.textDark, letterSpacing: -0.2,
    borderWidth: 1, borderColor: Colors.borderWarm,
  },
  fieldUnit: {
    position: 'absolute', right: Spacing.base, top: 0, bottom: 0,
    fontSize: FontSize.sm, fontWeight: '600', color: Colors.textMuted, lineHeight: 52,
  },
  fieldRow: { flexDirection: 'row', gap: Spacing.md },

  // Wire gauge selector
  gaugeScroll: { marginTop: Spacing.xs, marginBottom: 0 },
  gaugeScrollContent: { gap: Spacing.sm, paddingRight: Spacing.base },
  gaugePill: {
    paddingHorizontal: Spacing.base, paddingVertical: 10, borderRadius: Radius.md,
    backgroundColor: Colors.card, borderWidth: 1, borderColor: Colors.borderWarm,
  },
  gaugePillActive: { backgroundColor: Colors.textDark, borderColor: Colors.textDark },
  gaugePillText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textDark },
  gaugePillTextActive: { color: Colors.card },

  // Results
  resultCard: {
    backgroundColor: Colors.card, borderRadius: Radius.lg, padding: 20, marginTop: Spacing.xs, marginBottom: Spacing.xs,
    borderLeftWidth: 3, borderLeftColor: Colors.textDark,
    ...Shadow.medium,
  },
  resultLabel: {
    fontSize: FontSize.xs, fontWeight: '700', color: Colors.textMuted, letterSpacing: 0.8,
    textTransform: 'uppercase', marginBottom: 6,
  },
  resultBig: {
    fontSize: 32, fontWeight: '800', color: Colors.textDark, letterSpacing: -0.5, marginBottom: 2,
  },
  resultDivider: {
    height: 1, backgroundColor: Colors.borderWarm, marginVertical: 14,
  },
  resultDetails: { flexDirection: 'row', gap: Spacing.lg },
  resultDetailItem: { flex: 1 },
  resultDetailLabel: { fontSize: FontSize.xs, fontWeight: '600', color: Colors.textMuted, marginBottom: 2, letterSpacing: 0.2 },
  resultDetailValue: { fontSize: FontSize.base, fontWeight: '700', color: Colors.textDark },

  // Ohm's law results
  ohmsRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: Colors.backgroundWarm,
  },
  ohmsLabel: { fontSize: FontSize.sm, color: Colors.textMuted },
  ohmsValueWrap: { flexDirection: 'row', alignItems: 'baseline', gap: Spacing.xs },
  ohmsValue: { fontSize: 22, fontWeight: '700', color: Colors.textDark },
  ohmsUnit: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textMuted },

  // Warning / Hint cards
  warningCard: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: Colors.card, borderRadius: Radius.md, padding: Spacing.base, marginTop: Spacing.xs,
    borderWidth: 1, borderColor: Colors.borderWarm,
  },
  warningText: { flex: 1, fontSize: FontSize.sm, color: Colors.textDark, lineHeight: 20 },
  hintCard: {
    backgroundColor: Colors.card, borderRadius: Radius.md, padding: Spacing.base, marginTop: Spacing.xs,
    borderWidth: 1, borderColor: Colors.borderWarm, borderStyle: 'dashed',
  },
  hintText: { fontSize: FontSize.sm, color: Colors.textMuted, textAlign: 'center', lineHeight: 20 },

  // Reset button
  resetBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    alignSelf: 'center', paddingHorizontal: Spacing.base, paddingVertical: Spacing.sm, borderRadius: Radius.full,
    marginTop: Spacing.base,
    backgroundColor: Colors.card, borderWidth: 1, borderColor: Colors.borderWarm,
  },
  resetText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textMuted },

  disclaimer: {
    fontSize: FontSize.xs, color: Colors.textFaint, marginTop: 20, lineHeight: 16, textAlign: 'center',
  },

  // P/T Chart -- refrigerant selector
  refSelector: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, marginBottom: Spacing.base },
  refPill: {
    paddingHorizontal: 18, paddingVertical: 11, borderRadius: Radius.md,
    backgroundColor: Colors.card, borderWidth: 1, borderColor: Colors.borderWarm,
  },
  refPillActive: { backgroundColor: Colors.textDark, borderColor: Colors.textDark },
  refPillText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.textDark },
  refPillTextActive: { color: Colors.card },

  // P/T Table
  ptTable: {
    backgroundColor: Colors.card, borderRadius: Radius.lg, overflow: 'hidden',
    ...Shadow.subtle,
  },
  ptHeader: {
    flexDirection: 'row', paddingVertical: Spacing.md, paddingHorizontal: 20,
    backgroundColor: Colors.textDark,
  },
  ptHeaderCell: {
    flex: 1, fontSize: FontSize.xs, fontWeight: '700', color: Colors.card,
    letterSpacing: 0.3, textTransform: 'uppercase',
  },
  ptScroll: { maxHeight: 380 },
  ptRow: {
    flexDirection: 'row', paddingVertical: Spacing.md, paddingHorizontal: 20,
    borderBottomWidth: 1, borderBottomColor: Colors.backgroundWarm,
  },
  ptRowAlt: { backgroundColor: '#FAFAF7' },
  ptCell: {
    flex: 1, fontSize: FontSize.base, color: Colors.textDark, fontVariant: ['tabular-nums'],
  },
});
