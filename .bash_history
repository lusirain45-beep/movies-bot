cd
pip install python-telegram-bot
nano bot.py
python bot.py
pkg install python
pip install python-telegram-bot
python bot.py
pkg update -y
pkg install nodejs -y
pkg install git -y
npm install -g expo-cli
npx create-expo-app SmartPlay
cd SmartPlay
npm install expo-video expo-document-picker
npx expo start
npx expo install expo@~51.0.0
npx expo start
npm install metro@0.80.0 --legacy-peer-deps
npx expo start
cd
rm -rf SmartPlay && npx create-expo-app@sdk-51 SmartPlay
npx create-expo-app@sdk-51
rm -rf SmartPlay 
npx create-expo-app@sdk-51 SmartPlay
npx create-expo-app SmartPlay --template blank
cd SmartPlay
npm run web
npx expo start
cd SmartPlay
App.js << 'EOF'
import { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, FlatList } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

export default function App() {
  const [videos, setVideos] = useState([]);

  const pickVideo = async () => {
    const result = await DocumentPicker.getDocumentAsync({ type: 'video/*' });
    if (!result.canceled) {
      setVideos([...videos, result.assets[0]]);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>SmartPlay</Text>
      <TouchableOpacity style={styles.button} onPress={pickVideo}>
        <Text style={styles.buttonText}>+ Add Video</Text>
      </TouchableOpacity>
      <FlatList
        data={videos}
        keyExtractor={(item, index) => index.toString()}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <Text style={styles.itemText}>{item.name}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', padding: 20, paddingTop: 60 },
  title: { color: '#f5a623', fontSize: 32, fontWeight: 'bold', marginBottom: 20 },
  button: { backgroundColor: '#f5a623', padding: 15, borderRadius: 10, alignItems: 'center', marginBottom: 20 },
  buttonText: { color: '#000', fontWeight: 'bold', fontSize: 16 },
  item: { backgroundColor: '#222', padding: 15, borderRadius: 10, marginBottom: 10 },
  itemText: { color: '#fff', fontSize: 14 },
});
EOF

Command pphs in package ghostscript
nano App.js
r
npx expo start
npx expo install react-dom react-native-web
npx expo start
nano App.js
npx expo start
nano App.js
npx expo start
