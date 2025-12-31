# Judgement Rules Chat - Web Application

AI-powered chat interface for Judgement: Eternal Champions rules, powered by Elasticsearch's Agent Builder.

## Features

- **Conversational AI**: Ask questions about Judgement rules in natural language
- **Conversation History**: Browse and resume previous conversations
- **Dark Theme**: Matches Judgement's aesthetic with gold accents
- **Real-time Responses**: Fast responses from Elasticsearch Agent Builder
- **No Authentication**: Single-user application with shared credentials
- **Mobile Responsive**: Works on all device sizes

## Prerequisites

- Node.js 18+
- Kibana instance with Agent Builder configured
- Elasticsearch cluster with ingested rulebook data (see `../ingestion/`)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your Kibana credentials:
```
KIBANA_URL=https://your-kibana-instance.kb.region.cloud.es.io
KIBANA_API_KEY=your-api-key-here
KIBANA_AGENT_ID=your-agent-id-here
KIBANA_SPACE=default
```

### Getting Your Configuration Values

**KIBANA_URL**: Your Kibana instance URL (typically ends in `.kb.region.cloud.es.io`)

**KIBANA_API_KEY**:
1. In Kibana, go to Stack Management > API Keys
2. Create a new API key with Agent Builder permissions
3. Copy the encoded key

**KIBANA_AGENT_ID**:
1. In Kibana, go to Search > Agent Builder
2. Create or select your agent
3. Configure it to use your ingested rulebook index
4. Copy the agent ID from the URL or agent settings

**KIBANA_SPACE**: The Kibana space name (use "default" if not using spaces)

## Development

Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Building for Production

```bash
npm run build
npm start
```

## Deployment to Vercel

### Via Vercel Dashboard

1. Push your repository to GitHub
2. Import the project in Vercel
3. Vercel will automatically detect Next.js
4. Configure environment variables in Vercel:
   - `KIBANA_URL`
   - `KIBANA_API_KEY`
   - `KIBANA_AGENT_ID`
   - `KIBANA_SPACE`
5. Deploy

### Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

## Project Structure

```
webapp/
├── app/                       # Next.js app directory
│   ├── api/                  # API routes
│   │   ├── chat/            # Chat endpoint
│   │   │   └── route.ts    # POST /api/chat
│   │   └── conversations/   # Conversation management
│   │       ├── route.ts    # GET /api/conversations
│   │       └── [id]/
│   │           └── route.ts # GET/DELETE /api/conversations/:id
│   ├── globals.css          # Global styles
│   ├── layout.tsx           # Root layout with fonts
│   └── page.tsx             # Main chat interface
│
├── components/               # React components
│   ├── ChatInput.tsx        # Message input field
│   ├── ChatMessage.tsx      # Message bubble
│   └── ConversationList.tsx # Sidebar with conversations
│
├── lib/                      # Utilities
│   ├── kibana-client.ts     # Kibana API client
│   └── types.ts             # TypeScript type definitions
│
├── public/                   # Static assets
├── .env.example             # Environment template
├── next.config.ts           # Next.js configuration
├── package.json             # Dependencies
├── tailwind.config.ts       # Tailwind CSS config
└── tsconfig.json            # TypeScript config
```

## API Routes

### `POST /api/chat`
Send a message to the assistant.

**Request:**
```json
{
  "message": "How does charging work?",
  "conversationId": "optional-conversation-id"
}
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "message": "Charging is a type of attack..."
}
```

### `GET /api/conversations`
List all conversations.

**Response:**
```json
[
  {
    "id": "conv_123",
    "title": "Charging Rules",
    "messages": [...],
    "last_updated": "2025-12-31T12:00:00Z"
  }
]
```

### `GET /api/conversations/[id]`
Get a specific conversation.

### `DELETE /api/conversations/[id]`
Delete a conversation.

## Styling

The application uses:

- **Tailwind CSS** for utility-first styling
- **Dark theme** with black background
- **Gold accent** (`#bc892d`) matching Judgement branding
- **Figtree** font for body text
- **Oswald** font for headings
- Responsive design for mobile and desktop

### Customizing Colors

Edit `tailwind.config.ts` to change the color scheme:

```typescript
colors: {
  gold: {
    DEFAULT: "#bc892d",
    light: "#d4a040",
    dark: "#9a6f1f",
  },
}
```

## Troubleshooting

### "Failed to load conversations"
- Verify `KIBANA_URL` is correct and accessible
- Check `KIBANA_API_KEY` has proper permissions
- Ensure Agent Builder is configured in Kibana

### "Failed to send message"
- Verify `KIBANA_AGENT_ID` matches your agent
- Check agent has access to the rulebook index
- Review Kibana logs for errors

### Build errors
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules
npm install

# Rebuild
npm run build
```

### TypeScript errors
Ensure you're using Node.js 18+ and TypeScript 5+:
```bash
node --version
npx tsc --version
```

## Environment Variables

### Required
- `KIBANA_URL` - Kibana instance URL
- `KIBANA_API_KEY` - API key with Agent Builder permissions
- `KIBANA_AGENT_ID` - ID of your configured agent

### Optional
- `KIBANA_SPACE` - Kibana space (default: "default")

## Technology Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Kibana Agent Builder API** - AI chat backend
- **Vercel** - Deployment platform

## License

See LICENSE file in repository root.
