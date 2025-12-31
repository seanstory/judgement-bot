# Deployment Guide

This guide walks through deploying the Judgement Rules Chat application to Vercel.

## Prerequisites

1. Elasticsearch cluster with ingested rulebook data (see `ingestion/README.md`)
2. Kibana instance with Agent Builder configured
3. GitHub account
4. Vercel account (free tier works)

## Step 1: Configure Kibana Agent Builder

### 1.1 Create an API Key

1. In Kibana, go to **Stack Management** > **API Keys**
2. Click **Create API key**
3. Name it "Judgement Chat App"
4. Grant it these permissions:
   - Agent Builder access
   - Read access to your rulebook index
5. Copy the **encoded** API key (you won't see it again)

### 1.2 Create or Configure Agent

1. In Kibana, go to **Search** > **Agent Builder**
2. Create a new agent or select an existing one
3. Configure it to use your `judgement_core_rules` index
4. Set up the agent's instructions (e.g., "You are a helpful assistant for Judgement: Eternal Champions rules")
5. Copy the **Agent ID** from the URL or agent settings

## Step 2: Prepare Repository

### 2.1 Push to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Add Judgement Rules Chat application"

# Create GitHub repository and push
git remote add origin https://github.com/yourusername/judgement-bot.git
git branch -M main
git push -u origin main
```

### 2.2 Verify Structure

Ensure your repository has:
```
judgement-bot/
├── webapp/          # Next.js application
├── ingestion/       # Ingestion tools
├── vercel.json      # Vercel configuration
└── README.md
```

## Step 3: Deploy to Vercel

### Option A: Vercel Dashboard (Recommended)

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **Add New** > **Project**
3. Import your GitHub repository
4. Vercel will auto-detect the configuration from `vercel.json`
5. Configure environment variables:
   - Click **Environment Variables**
   - Add these variables:
     ```
     KIBANA_URL=https://your-instance.kb.region.cloud.es.io
     KIBANA_API_KEY=your-api-key-here
     KIBANA_AGENT_ID=your-agent-id-here
     KIBANA_SPACE=default
     ```
   - Set them for **Production**, **Preview**, and **Development**
6. Click **Deploy**
7. Wait 2-3 minutes for the build to complete
8. Click the deployment URL to open your app

### Option B: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy (will prompt for environment variables)
vercel

# Set environment variables
vercel env add KIBANA_URL production
vercel env add KIBANA_API_KEY production
vercel env add KIBANA_AGENT_ID production
vercel env add KIBANA_SPACE production

# Deploy to production
vercel --prod
```

## Step 4: Test Deployment

1. Open your Vercel deployment URL
2. Try asking a question: "How does charging work?"
3. Verify the response comes from your Elasticsearch data
4. Test conversation history by creating a new conversation

## Step 5: Configure Custom Domain (Optional)

1. In Vercel dashboard, go to your project
2. Click **Settings** > **Domains**
3. Add your custom domain (e.g., `rules.judgement.game`)
4. Follow Vercel's DNS configuration instructions
5. Wait for DNS propagation (up to 24 hours)

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `KIBANA_URL` | Your Kibana instance URL | `https://abc123.kb.us-east-1.cloud.es.io` |
| `KIBANA_API_KEY` | API key with Agent Builder access | `VnVhQ2l...` (long encoded string) |
| `KIBANA_AGENT_ID` | Your configured agent's ID | `agent_abc123xyz` |
| `KIBANA_SPACE` | Kibana space (optional) | `default` |

## Troubleshooting

### Build fails with "Cannot find module"
- Ensure `webapp/package.json` has all dependencies
- Try running `cd webapp && npm install` locally first
- Check that `vercel.json` points to correct directories

### "Failed to connect to Kibana"
- Verify `KIBANA_URL` is correct (include https://)
- Check API key has not expired
- Ensure Kibana instance is accessible from Vercel's servers
- Test the API key with curl:
  ```bash
  curl -H "Authorization: ApiKey YOUR_KEY" \
       -H "kbn-xsrf: true" \
       https://your-kibana-url/api/status
  ```

### "Agent not found"
- Verify `KIBANA_AGENT_ID` matches your agent
- Check agent is published/active in Kibana
- Ensure agent has access to the rulebook index

### Slow responses
- Check your Elasticsearch cluster performance
- Review agent configuration in Kibana
- Consider upgrading Elasticsearch tier for better performance

### CORS errors
- This should not happen with Next.js API routes
- If it does, check that API calls go through `/api/*` routes
- Verify you're not calling Kibana directly from the browser

## Updating Deployment

### Update Code
```bash
git add .
git commit -m "Update feature X"
git push origin main
```

Vercel will automatically redeploy on push to main.

### Update Environment Variables

1. In Vercel dashboard, go to **Settings** > **Environment Variables**
2. Edit or add variables
3. **Important:** Click **Redeploy** after changing variables

Or via CLI:
```bash
vercel env rm KIBANA_API_KEY production
vercel env add KIBANA_API_KEY production
vercel --prod
```

## Monitoring

### View Logs

**Vercel Dashboard:**
1. Go to your project
2. Click **Deployments**
3. Select a deployment
4. Click **Functions** to see API route logs

**Vercel CLI:**
```bash
vercel logs
```

### Check Performance

1. In Vercel dashboard, go to **Analytics**
2. Review page load times, function execution times
3. Check error rates

### Monitor Costs

1. Go to **Settings** > **Usage**
2. Check function invocations, bandwidth
3. Free tier includes:
   - 100 GB bandwidth
   - 100 GB-hours serverless function execution

## Security Best Practices

1. **Never commit `.env` files**
   - Add `.env` to `.gitignore`
   - Use Vercel's environment variables feature

2. **Rotate API keys regularly**
   - Create new API key in Kibana
   - Update Vercel environment variable
   - Revoke old key

3. **Use minimal permissions**
   - API key should only have Agent Builder access
   - No unnecessary cluster admin permissions

4. **Enable Vercel authentication** (optional)
   - Go to **Settings** > **General** > **Password Protection**
   - Enable for preview deployments

## Scaling

The application scales automatically with Vercel:

- **Serverless functions**: Auto-scale with traffic
- **Global CDN**: Static assets served from edge
- **No server management**: Fully managed infrastructure

For high traffic:
- Consider Vercel Pro plan for better performance
- Upgrade Elasticsearch tier for better search performance
- Monitor function execution times and optimize slow queries

## Rollback

If a deployment has issues:

1. In Vercel dashboard, go to **Deployments**
2. Find the previous working deployment
3. Click **⋯** > **Promote to Production**

Or via CLI:
```bash
vercel rollback
```

## Support

- **Vercel Issues**: [vercel.com/support](https://vercel.com/support)
- **Elasticsearch/Kibana**: [discuss.elastic.co](https://discuss.elastic.co)
- **Project Issues**: Create an issue in your GitHub repository
