# RAG Mobile App - React Native

A native mobile application for the RAG (Retrieval-Augmented Generation) system built with React Native and Expo.

## Features

- 📤 **Document Upload**: Pick and upload PDF/TXT files from your device
- 💬 **AI Chat**: Native chat interface with message bubbles
- 📄 **Document Management**: View and delete uploaded documents
- 📱 **Native Experience**: True iOS and Android app
- 🎨 **Modern UI**: Clean, intuitive mobile design

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Expo Go app on your phone (for testing)
- RAG backend running and accessible

### Installation

```bash
cd rag-mobile
npm install
```

### Configuration

**IMPORTANT**: Update the API URL in `services/api.ts`:

```typescript
// For testing on physical device, use your computer's IP address
const API_BASE_URL = 'http://192.168.1.100:8001';  // Replace with your IP

// For emulator/simulator
const API_BASE_URL = 'http://localhost:8001';
```

To find your IP address:
- **Windows**: Run `ipconfig` in terminal
- **Mac/Linux**: Run `ifconfig` in terminal

### Run the App

```bash
npx expo start
```

Then:
- **iOS**: Scan QR code with Camera app
- **Android**: Scan QR code with Expo Go app
- **Emulator**: Press `i` for iOS or `a` for Android

## Usage

1. **Upload Documents**:
   - Tap "Upload" on home screen
   - Choose a PDF or TXT file
   - Wait for upload confirmation

2. **Chat**:
   - Tap "Chat" on home screen
   - Type your question
   - View AI response with sources

3. **Manage Documents**:
   - Tap "Documents" on home screen
   - View all uploaded files
   - Swipe to delete

## Tech Stack

- **Framework**: React Native with Expo
- **Language**: TypeScript
- **Navigation**: Expo Router
- **HTTP Client**: Axios
- **File Picker**: expo-document-picker

## Project Structure

```
rag-mobile/
├── app/
│   ├── index.tsx         # Home screen
│   ├── _layout.tsx       # Navigation layout
│   ├── upload.tsx        # Upload screen
│   ├── chat.tsx          # Chat screen
│   └── documents.tsx     # Documents screen
├── services/
│   └── api.ts            # API client
└── package.json
```

## Testing

### On Physical Device

1. Install Expo Go from App Store/Play Store
2. Make sure your phone and computer are on the same WiFi
3. Update API_BASE_URL to your computer's IP address
4. Scan the QR code from `npx expo start`

### On Emulator

1. Start iOS Simulator or Android Emulator
2. Run `npx expo start`
3. Press `i` for iOS or `a` for Android

## Building for Production

### iOS

```bash
npx expo build:ios
```

### Android

```bash
npx expo build:android
```

Or use EAS Build:

```bash
npm install -g eas-cli
eas build --platform ios
eas build --platform android
```

## Troubleshooting

**Network Errors**:
- Verify backend is running
- Check API_BASE_URL is correct
- Ensure phone and computer are on same WiFi
- Try using IP address instead of localhost

**Upload Failures**:
- Check file size (max 50MB)
- Verify file type (PDF or TXT only)
- Check backend logs for errors

**Can't Connect to Backend**:
- Make sure backend allows CORS from mobile
- Try disabling firewall temporarily
- Use your computer's IP address, not localhost

## Deployment

### App Store (iOS)

1. Build with EAS
2. Submit to App Store Connect
3. Complete app review process

### Play Store (Android)

1. Build with EAS
2. Create app in Play Console
3. Upload APK/AAB
4. Complete review process

---

Built with ❤️ using React Native and Expo
