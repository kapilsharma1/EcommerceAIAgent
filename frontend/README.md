# E-Commerce AI Agent Frontend

A modern React + TypeScript frontend for the E-Commerce AI Customer Support Agent.

## Features

- 💬 Real-time chat interface
- ✅ Human-in-the-loop approval system
- 📱 Responsive design
- 🎨 Modern UI with Tailwind CSS
- 🔄 Conversation persistence
- ⚡ Fast and optimized with Vite

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Data fetching and state management
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

3. **Build for production**
   ```bash
   npm run build
   ```

4. **Preview production build**
   ```bash
   npm run preview
   ```

## Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── Chat/         # Chat-related components
│   │   ├── Approval/     # Approval modal and cards
│   │   ├── Order/        # Order display components
│   │   └── Common/       # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API service layer
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── App.tsx           # Main app component
│   └── main.tsx          # Entry point
├── public/               # Static assets
├── index.html            # HTML template
└── package.json          # Dependencies
```

## Environment Variables

Create a `.env` file in the `frontend` directory:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Usage

1. **Start a conversation**: Type a message in the chat input
2. **View responses**: Agent responses appear in real-time
3. **Handle approvals**: When an action requires approval, a modal will appear
4. **Approve/Reject**: Click the appropriate button in the approval modal

## API Integration

The frontend communicates with the backend API:

- `POST /api/v1/chat` - Send messages
- `POST /api/v1/approvals/{id}` - Submit approvals

## Development

### Code Style

- ESLint is configured for code quality
- TypeScript strict mode enabled
- Prettier recommended (optional)

### Key Features

- **Conversation Management**: Automatically manages conversation IDs via localStorage
- **Error Handling**: Graceful error handling with user-friendly messages
- **Loading States**: Visual feedback during API calls
- **Responsive Design**: Works on desktop and mobile devices

## License

MIT
