Chat with the bot at https://judgement-bot-drab.vercel.app/

# Judgement Rules Chat

AI-powered rules search and chat interface for Judgement: Eternal Champions board game.

This repository contains two main components:

1. **Web Application** (`webapp/`) - A Next.js chat interface that uses Elasticsearch's Agent Builder APIs
2. **Ingestion Tools** (`ingestion/`) - Scripts to parse the rulebook PDF and ingest it into Elasticsearch

## Quick Start

### Web Application

The chat interface provides an AI-powered assistant for Judgement rules queries.

#### Prerequisites

- Node.js 18+
- Kibana instance with Agent Builder configured
- Elasticsearch cluster with ingested rulebook data

#### Setup

1. Navigate to the webapp directory:
```bash
cd webapp
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
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

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

#### Deployment to Vercel

The application is optimized for Vercel deployment:

1. Push this repository to GitHub
2. Import the project in Vercel
3. Vercel will automatically detect the Next.js configuration
4. Add the environment variables in Vercel's dashboard:
   - `KIBANA_URL`
   - `KIBANA_API_KEY`
   - `KIBANA_AGENT_ID`
   - `KIBANA_SPACE` (optional, defaults to "default")
5. Deploy

Alternatively, use the Vercel CLI:
```bash
vercel
```

### Ingestion Tools

The ingestion tools parse the Judgement rulebook PDF and load it into Elasticsearch.

See [`ingestion/README.md`](ingestion/README.md) for detailed setup and usage instructions.

Quick overview:
```bash
cd ingestion

# Install dependencies
make install

# Parse the rulebook
make run

# Configure Elasticsearch credentials
cp .env.example .env
# Edit .env with your credentials

# Ingest to Elasticsearch
make ingest
```

## Project Structure

```
judgement-bot/
├── webapp/                      # Next.js chat application
│   ├── app/                    # Next.js app directory
│   │   ├── api/               # Backend API routes
│   │   │   ├── chat/         # Chat message endpoint
│   │   │   └── conversations/ # Conversation management
│   │   ├── globals.css       # Global styles
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Main chat page
│   ├── components/            # React components
│   │   ├── ChatInput.tsx     # Message input component
│   │   ├── ChatMessage.tsx   # Message display component
│   │   └── ConversationList.tsx # Sidebar conversation list
│   ├── lib/                   # Utilities and types
│   │   ├── kibana-client.ts  # Kibana API client
│   │   └── types.ts          # TypeScript types
│   ├── public/                # Static assets
│   ├── .env.example          # Environment template
│   ├── next.config.ts        # Next.js configuration
│   ├── package.json          # Dependencies
│   ├── tailwind.config.ts    # Tailwind CSS config
│   └── tsconfig.json         # TypeScript config
│
├── ingestion/                  # Rulebook parsing and ingestion
│   ├── connector/             # Crawlee connector for web content
│   ├── parse_rulebook.py     # PDF parsing script
│   ├── ingest.py             # Elasticsearch ingestion
│   ├── mappings.json         # Index mappings
│   ├── requirements.txt      # Python dependencies
│   └── Makefile             # Build commands
│
├── vercel.json                # Vercel deployment config
└── README.md                  # This file
```

## Features

### Web Application

- **Chat Interface**: Clean, dark-themed UI matching Judgement's aesthetic
- **Conversation History**: Browse and resume previous conversations
- **Real-time Responses**: Streaming responses from Kibana Agent Builder
- **Session Management**: All conversation state managed by Elasticsearch
- **No Auth Required**: Single-user application using shared Elasticsearch credentials
- **Mobile Responsive**: Works on desktop and mobile devices

### Ingestion Tools

- **ML-based PDF parsing** using Docling
- **Smart categorization** into 12 thematic categories
- **Semantic search** ready with `semantic_text` fields
- **265 searchable chunks** from 100-page rulebook

## API Routes

The webapp provides the following API endpoints:

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
Get all conversations.

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

## Technology Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling with custom dark theme
- **Google Fonts** - Figtree & Oswald fonts matching Judgement branding

### Backend
- **Next.js API Routes** - Serverless API endpoints
- **Kibana Agent Builder API** - AI-powered chat backend
- **Elasticsearch** - Document storage and semantic search

### Deployment
- **Vercel** - Hosting and serverless functions

## Environment Variables

### Required
- `KIBANA_URL` - Your Kibana instance URL
- `KIBANA_API_KEY` - API key with Agent Builder permissions
- `KIBANA_AGENT_ID` - The ID of your configured agent

### Optional
- `KIBANA_SPACE` - Kibana space name (default: "default")

## Development

### Running Locally

```bash
# Install dependencies
cd webapp
npm install

# Start development server
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

### Building for Production

```bash
npm run build
npm start
```

## Troubleshooting

### "Failed to load conversations"
- Check that `KIBANA_URL` is correct and accessible
- Verify `KIBANA_API_KEY` has the necessary permissions
- Ensure the Agent Builder is properly configured in Kibana

### "Failed to send message"
- Verify `KIBANA_AGENT_ID` matches your configured agent
- Check that your agent has access to the ingested rulebook index
- Review Kibana logs for agent errors

### Styling issues
- Clear your browser cache
- Ensure Tailwind CSS is properly configured
- Check that Google Fonts are loading

## Credits

- **Judgement: Eternal Champions** - Created by Andrew Galea, reimagined by Creature Caster
- **Docling** - IBM Research's document understanding library
- **Elasticsearch** - Search and analytics engine
- **Kibana Agent Builder** - AI agent framework

## License

See LICENSE file.
