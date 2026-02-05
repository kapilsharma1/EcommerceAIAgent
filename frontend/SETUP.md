# Frontend Setup Guide

## Quick Start

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Create environment file** (optional)
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env if needed (default is http://localhost:8000/api/v1)
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Open browser**
   - Navigate to `http://localhost:3000`
   - Make sure your backend is running on `http://localhost:8000`

## Development Commands

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── Chat/         # Chat UI components
│   │   ├── Approval/     # Approval modal components
│   │   ├── Order/        # Order display components
│   │   └── Common/       # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   │   ├── useChat.ts           # Chat state management
│   │   ├── useConversation.ts   # Conversation ID management
│   │   └── useApproval.ts       # Approval handling
│   ├── services/         # API services
│   │   ├── api.ts              # Axios client setup
│   │   ├── chatService.ts      # Chat API calls
│   │   └── approvalService.ts  # Approval API calls
│   ├── types/            # TypeScript definitions
│   │   ├── chat.ts
│   │   ├── approval.ts
│   │   └── order.ts
│   ├── utils/            # Utility functions
│   │   ├── conversationId.ts   # Conversation ID helpers
│   │   └── formatters.ts       # Date/currency formatters
│   ├── App.tsx           # Main app component
│   └── main.tsx          # Entry point
├── public/               # Static assets
├── index.html            # HTML template
└── package.json          # Dependencies
```

## Features

### Chat Interface
- Real-time message display
- Conversation history
- Typing indicators
- Auto-scroll to latest message

### Approval System
- Modal dialog for action approvals
- Clear action descriptions
- Approve/Reject buttons
- Loading states

### Conversation Management
- Automatic conversation ID generation
- localStorage persistence
- Conversation context maintained across sessions

## API Integration

The frontend expects the backend API to be running on `http://localhost:8000` by default.

### Endpoints Used:
- `POST /api/v1/chat` - Send chat messages
- `POST /api/v1/approvals/{id}` - Submit approvals

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running on port 8000
- Check CORS settings in backend
- Verify API_BASE_URL in .env file

### Build Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

### TypeScript Errors
- Run `npm run build` to check for type errors
- Ensure all dependencies are installed

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Production Build

1. **Build the application**
   ```bash
   npm run build
   ```

2. **Preview the build**
   ```bash
   npm run preview
   ```

3. **Deploy**
   - The `dist/` folder contains the production build
   - Serve it with any static file server (nginx, Apache, etc.)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## Next Steps

1. Customize the UI theme in `tailwind.config.js`
2. Add more components as needed
3. Implement additional features (conversation history, user profiles, etc.)
4. Add unit tests
5. Set up CI/CD pipeline
