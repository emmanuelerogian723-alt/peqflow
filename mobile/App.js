import React, { useState, useEffect, useCallback } from 'react';
import { 
  View, Text, TextInput, TouchableOpacity, FlatList, 
  StyleSheet, SafeAreaView, ActivityIndicator, Alert, RefreshControl
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import Constants from 'expo-constants';

const API_BASE = Constants.expoConfig?.extra?.apiBase || 'http://localhost:8000/api/v1';

// Colors
const COLORS = {
  bg: '#0a0a0f',
  surface: '#13131f',
  surface2: '#1a1a2e',
  border: '#2a2a3e',
  text: '#e4e4ef',
  muted: '#7a7a9e',
  accent: '#6c5ce7',
  accent2: '#00cec9',
  success: '#00b894',
  danger: '#e17055',
  warning: '#fdcb6e',
};

const INTEGRATION_ICONS = {
  paystack: '💳', whatsapp: '💬', gmail: '📧', google_sheets: '📊',
  slack: '🔔', notion: '📝', telegram: '✈️', shopify: '🛒', internal: '⚙️'
};

// ============ API HELPERS ============
async function apiCall(path, method = 'GET', body = null) {
  try {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(`${API_BASE}${path}`, opts);
    const data = await resp.json();
    return data;
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ============ CREATE SCREEN ============
function CreateScreen({ navigation }) {
  const [description, setDescription] = useState('');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);

  const parseWorkflow = async () => {
    if (!description.trim()) return;
    setLoading(true);
    const data = await apiCall('/workflows/parse', 'POST', { description });
    setLoading(false);
    if (data.success) {
      setPreview(data.workflow);
    } else {
      Alert.alert('Error', data.detail || 'Failed to parse');
    }
  };

  const saveWorkflow = async () => {
    if (!description.trim()) return;
    setLoading(true);
    const data = await apiCall('/workflows/create', 'POST', { description });
    setLoading(false);
    if (data.success) {
      Alert.alert('Saved!', `Workflow ID: ${data.workflow_id}`);
      setDescription('');
      setPreview(null);
      navigation.navigate('Flows');
    } else {
      Alert.alert('Error', JSON.stringify(data.validation || data.error));
    }
  };

  const examples = [
    'When someone pays on Paystack, send them a WhatsApp receipt and add to Google Sheets',
    'When I get an email from a client, add them to Notion and notify my team on Slack',
    'When a customer pays, send WhatsApp receipt, wait 3 days, send follow-up',
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        <Text style={styles.heroTitle}>Describe your automation</Text>
        <Text style={styles.heroSub}>Type what you want to automate. Peq builds it.</Text>
        
        <TextInput
          style={styles.input}
          multiline
          numberOfLines={4}
          placeholder="When someone pays on Paystack, send them a WhatsApp receipt..."
          placeholderTextColor={COLORS.muted}
          value={description}
          onChangeText={setDescription}
        />
        
        <View style={styles.buttonRow}>
          <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={parseWorkflow}>
            {loading ? <ActivityIndicator color="white" /> : <Text style={styles.btnText}>Preview</Text>}
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, styles.btnSuccess]} onPress={saveWorkflow}>
            <Text style={styles.btnText}>Save & Deploy</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.sectionTitle}>Try an example:</Text>
        {examples.map((ex, i) => (
          <TouchableOpacity key={i} style={styles.chip} onPress={() => setDescription(ex)}>
            <Text style={styles.chipText}>{ex}</Text>
          </TouchableOpacity>
        ))}

        {preview && (
          <View style={styles.previewBox}>
            <Text style={styles.previewTitle}>Preview ({preview.steps.length} steps)</Text>
            {preview.steps.map((step, i) => (
              <View key={i} style={[styles.stepCard, 
                { borderLeftColor: step.step_type === 'trigger' ? COLORS.accent2 : 
                  step.step_type === 'delay' ? COLORS.warning : COLORS.accent }]}>
                <Text style={styles.stepType}>{step.step_type} - {step.integration}</Text>
                <Text style={styles.stepName}>{step.name}</Text>
                <Text style={styles.stepDesc}>{step.description}</Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ============ FLOWS LIST SCREEN ============
function FlowsScreen() {
  const [flows, setFlows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadFlows = useCallback(async () => {
    const data = await apiCall('/workflows');
    setFlows(data.workflows || []);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { loadFlows(); }, []);

  const onRefresh = () => { setRefreshing(true); loadFlows(); };

  const activateFlow = async (id) => {
    await apiCall('/workflows/activate', 'POST', { workflow_id: id });
    loadFlows();
  };

  const pauseFlow = async (id) => {
    await apiCall('/workflows/pause', 'POST', { workflow_id: id });
    loadFlows();
  };

  const deleteFlow = (id) => {
    Alert.alert('Delete?', 'This will permanently delete the workflow.', [
      { text: 'Cancel' },
      { text: 'Delete', onPress: async () => {
        await apiCall(`/workflows/${id}`, 'DELETE');
        loadFlows();
      }}
    ]);
  };

  const statusColor = (status) => 
    status === 'active' ? COLORS.success : 
    status === 'paused' ? COLORS.warning : COLORS.muted;

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color={COLORS.accent} /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.screenTitle}>My Automations</Text>
      <FlatList
        data={flows}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
        renderItem={({ item }) => (
          <View style={styles.flowCard}>
            <View style={styles.flowInfo}>
              <Text style={styles.flowName}>{item.name}</Text>
              <Text style={styles.flowStatus} >
                Status: {item.status}
              </Text>
            </View>
            <View style={styles.flowActions}>
              {item.status === 'draft' && (
                <TouchableOpacity style={[styles.smallBtn, { backgroundColor: COLORS.success }]} onPress={() => activateFlow(item.id)}>
                  <Text style={styles.btnText}>Activate</Text>
                </TouchableOpacity>
              )}
              {item.status === 'active' && (
                <TouchableOpacity style={[styles.smallBtn, { backgroundColor: COLORS.warning }]} onPress={() => pauseFlow(item.id)}>
                  <Text style={styles.btnText}>Pause</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity style={[styles.smallBtn, { backgroundColor: COLORS.danger }]} onPress={() => deleteFlow(item.id)}>
                <Text style={styles.btnText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.centered}>
            <Text style={styles.emptyIcon}>⚡</Text>
            <Text style={styles.emptyText}>No automations yet</Text>
            <Text style={styles.emptySub}>Create one from the Create tab</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

// ============ INTEGRATIONS SCREEN ============
function IntegrationsScreen() {
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const data = await apiCall('/integrations');
      setIntegrations(data.integrations || []);
      setLoading(false);
    })();
  }, []);

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color={COLORS.accent} /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.screenTitle}>Integrations</Text>
      <FlatList
        data={integrations}
        keyExtractor={item => item.name}
        numColumns={2}
        renderItem={({ item }) => (
          <View style={[styles.integCard, { opacity: item.enabled ? 1 : 0.5 }]}>
            <Text style={styles.integIcon}>{INTEGRATION_ICONS[item.name] || '🔌'}</Text>
            <Text style={styles.integName}>{item.display_name}</Text>
            <Text style={[styles.integStatus, { color: item.enabled ? COLORS.success : COLORS.muted }]}>
              {item.enabled ? 'Connected' : 'Not configured'}
            </Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

// ============ BOTTOM TAB NAVIGATOR ============
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigationContainer } from '@react-navigation/native';
import { ScrollView } from 'react-native';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          tabBarStyle: { backgroundColor: COLORS.surface, borderTopColor: COLORS.border },
          tabBarActiveTintColor: COLORS.accent,
          tabBarInactiveTintColor: COLORS.muted,
          headerShown: false,
        }}
      >
        <Tab.Screen name="Create" component={CreateScreen} 
          options={{ tabBarIcon: () => <Text style={{fontSize: 20}}>➕</Text> }} />
        <Tab.Screen name="Flows" component={FlowsScreen}
          options={{ tabBarIcon: () => <Text style={{fontSize: 20}}>⚡</Text> }} />
        <Tab.Screen name="Integrations" component={IntegrationsScreen}
          options={{ tabBarIcon: () => <Text style={{fontSize: 20}}>🔌</Text> }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

// ============ STYLES ============
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg, padding: 16 },
  scroll: { flex: 1 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.bg },
  heroTitle: { fontSize: 24, fontWeight: '800', color: COLORS.text, marginBottom: 8, marginTop: 20 },
  heroSub: { fontSize: 14, color: COLORS.muted, marginBottom: 24 },
  input: {
    backgroundColor: COLORS.surface, borderRadius: 12, padding: 16,
    color: COLORS.text, fontSize: 15, minHeight: 100, textAlignVertical: 'top',
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 12,
  },
  buttonRow: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  btn: { padding: 12, borderRadius: 10, flex: 1, alignItems: 'center' },
  btnPrimary: { backgroundColor: COLORS.accent },
  btnSuccess: { backgroundColor: COLORS.success },
  btnText: { color: 'white', fontWeight: '600', fontSize: 14 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: COLORS.text, marginBottom: 12 },
  chip: {
    backgroundColor: COLORS.surface2, borderRadius: 20, padding: 10, marginBottom: 8,
    borderWidth: 1, borderColor: COLORS.border,
  },
  chipText: { color: COLORS.muted, fontSize: 13 },
  previewBox: { backgroundColor: COLORS.surface, borderRadius: 16, padding: 16, marginTop: 16 },
  previewTitle: { fontSize: 16, fontWeight: '700', color: COLORS.text, marginBottom: 12 },
  stepCard: {
    backgroundColor: COLORS.surface2, borderRadius: 12, padding: 12, marginBottom: 8,
    borderLeftWidth: 4,
  },
  stepType: { fontSize: 11, color: COLORS.muted, textTransform: 'uppercase' },
  stepName: { fontSize: 15, fontWeight: '600', color: COLORS.text, marginTop: 2 },
  stepDesc: { fontSize: 12, color: COLORS.muted, marginTop: 2 },
  screenTitle: { fontSize: 22, fontWeight: '800', color: COLORS.text, marginBottom: 20 },
  flowCard: {
    backgroundColor: COLORS.surface, borderRadius: 12, padding: 16, marginBottom: 12,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.border,
  },
  flowInfo: { flex: 1 },
  flowName: { fontSize: 15, fontWeight: '600', color: COLORS.text, marginBottom: 4 },
  flowStatus: { fontSize: 12, color: COLORS.muted },
  flowActions: { flexDirection: 'row', gap: 8 },
  smallBtn: { padding: 6, borderRadius: 8, paddingHorizontal: 10 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyText: { fontSize: 16, color: COLORS.muted, marginBottom: 4 },
  emptySub: { fontSize: 13, color: COLORS.muted },
  integCard: {
    backgroundColor: COLORS.surface, borderRadius: 12, padding: 16,
    margin: 6, flex: 1, alignItems: 'center', borderWidth: 1, borderColor: COLORS.border,
  },
  integIcon: { fontSize: 28, marginBottom: 8 },
  integName: { fontSize: 13, fontWeight: '600', color: COLORS.text, textAlign: 'center' },
  integStatus: { fontSize: 11, marginTop: 4 },
});
