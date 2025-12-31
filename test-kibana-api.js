#!/usr/bin/env node

// Test script to see the actual Kibana API response structure
const fs = require('fs');
const path = require('path');

// Load environment variables from webapp/.env
const envPath = path.join(__dirname, 'webapp', '.env');
const envContent = fs.readFileSync(envPath, 'utf8');
const env = {};
envContent.split('\n').forEach(line => {
  const match = line.match(/^([^=]+)=(.*)$/);
  if (match) {
    env[match[1].trim()] = match[2].trim();
  }
});

const KIBANA_URL = env.KIBANA_URL;
const KIBANA_API_KEY = env.KIBANA_API_KEY;
const KIBANA_AGENT_ID = env.KIBANA_AGENT_ID;
const KIBANA_SPACE = env.KIBANA_SPACE || 'default';

const getBaseUrl = () => {
  if (KIBANA_SPACE === 'default') {
    return `${KIBANA_URL}/api/agent_builder`;
  }
  return `${KIBANA_URL}/s/${KIBANA_SPACE}/api/agent_builder`;
};

async function testConversationsEndpoint() {
  console.log('\n=== Testing GET /api/agent_builder/conversations ===');
  const url = `${getBaseUrl()}/conversations`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `ApiKey ${KIBANA_API_KEY}`,
        'kbn-xsrf': 'true',
      },
    });

    console.log('Status:', response.status);
    console.log('Headers:', Object.fromEntries(response.headers.entries()));

    const data = await response.json();
    console.log('\nResponse structure:');
    console.log(JSON.stringify(data, null, 2));

    if (Array.isArray(data)) {
      console.log(`\n✓ Response is an array with ${data.length} conversations`);
    } else if (data.conversations) {
      console.log(`\n✓ Response has conversations property with ${data.conversations.length} items`);
    }
  } catch (error) {
    console.error('Error:', error.message);
  }
}

async function testStreamingChat() {
  console.log('\n=== Testing POST /api/agent_builder/converse/async (streaming) ===');
  const url = `${getBaseUrl()}/converse/async`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `ApiKey ${KIBANA_API_KEY}`,
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        agent_id: KIBANA_AGENT_ID,
        input: 'What is a charge attack?',
      }),
    });

    console.log('Status:', response.status);
    console.log('Headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response:', errorText);
      return;
    }

    console.log('\nStreaming events:');
    console.log('---');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let eventCount = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        console.log('Raw line:', line);

        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            eventCount++;
            console.log(`\nEvent #${eventCount}: ${data.event}`);
            console.log('Data structure:', JSON.stringify(data, null, 2));
          } catch (e) {
            console.error('Failed to parse:', jsonStr);
            console.error('Error:', e.message);
          }
        }
      }
    }

    console.log('\n---');
    console.log(`Total events received: ${eventCount}`);
  } catch (error) {
    console.error('Error:', error.message);
    console.error(error.stack);
  }
}

async function main() {
  console.log('Kibana API Test Script');
  console.log('======================');
  console.log('KIBANA_URL:', KIBANA_URL);
  console.log('KIBANA_AGENT_ID:', KIBANA_AGENT_ID);
  console.log('Base URL:', getBaseUrl());

  await testConversationsEndpoint();
  await testStreamingChat();
}

main().catch(console.error);
