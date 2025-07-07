# Multi-Social Poster - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Setting Up Platform Credentials](#setting-up-platform-credentials)
   - [Twitter Setup](#twitter-setup)
   - [Bluesky Setup](#bluesky-setup)
   - [Discord Setup](#discord-setup)
   - [Reddit Setup](#reddit-setup)
   - [imgBB Setup](#imgbb-setup)
3. [Using the Application](#using-the-application)
4. [Platform Limitations](#platform-limitations)
5. [Troubleshooting](#troubleshooting)

## Getting Started

1. **Launch the Application**: Double-click the `multipost.exe` file
2. **First Time Setup**: Click "Configure Credentials" to set up your social media accounts
3. **Save Credentials**: Your credentials are saved locally in `social_credentials.json` (keep this file secure!)
4. **Platform Preferences**: Your platform selections are saved in `platform_preferences.json`

## Setting Up Platform Credentials

Click the "Configure Credentials" button to open the settings dialog.

### Twitter Setup

Twitter requires API access through their Developer Portal.

1. **Create a Twitter Developer Account**:
   - Go to [developer.twitter.com](https://developer.twitter.com)
   - Apply for a developer account (usually instant approval)
   - Create a new App in the Developer Portal

2. **Get Your Credentials**:
   - In your app settings, find these keys:
     - **API Key**: (also called Consumer Key)
     - **API Secret**: (also called Consumer Secret)
     - **Bearer Token**: Generated automatically
   
3. **Generate Access Tokens**:
   - In your app settings, go to "Keys and tokens"
   - Under "Authentication Tokens", click "Generate"
   - Copy the **Access Token** and **Access Token Secret**

4. **Enable OAuth 1.0a**:
   - In app settings, ensure OAuth 1.0a is enabled
   - Set app permissions to "Read and Write"

### Bluesky Setup

Bluesky uses simple username/password authentication.

1. **Get Your Handle**:
   - Your Bluesky handle (e.g., `yourname.bsky.social`)
   - Just your regular login handle

2. **Create an App Password** (Recommended):
   - Go to Settings → App Passwords
   - Create a new app password for this application
   - Use this instead of your main password for security

### Discord Setup

Discord uses webhooks to post messages.

1. **Create a Webhook**:
   - Open Discord and go to your server
   - Go to Server Settings → Integrations → Webhooks
   - Click "New Webhook"
   - Choose the channel where posts will appear
   - Copy the Webhook URL

2. **Webhook URL Format**:
   ```
   https://discord.com/api/webhooks/[webhook-id]/[webhook-token]
   ```

### Reddit Setup

Reddit requires creating an application.

1. **Create Reddit App**:
   - Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
   - Click "Create App" or "Create Another App"
   - Fill in:
     - Name: Any name for your app
     - App type: Select "script"
     - Redirect URI: `http://localhost:8080` (not used but required)

2. **Get Credentials**:
   - **Client ID**: The string under "personal use script"
   - **Client Secret**: The secret key shown
   - **Username**: Your Reddit username
   - **Password**: Your Reddit password
   - **User Agent**: Leave as default or customize
   - **Subreddits**: Comma-separated list (e.g., `python, webdev, programming`)

### imgBB Setup

imgBB is used for hosting images for Discord embeds.

1. **Create imgBB Account**:
   - Go to [imgbb.com](https://imgbb.com)
   - Sign up for a free account

2. **Get API Key**:
   - Go to [api.imgbb.com](https://api.imgbb.com)
   - Sign in with your account
   - Your API key will be displayed
   - Copy and paste into the application

**Note**: Free tier supports images up to 32MB

## Using the Application

### Post Tab

1. **Write Your Post**:
   - Enter your text in the content area
   - Character count shows below (red when over 280 for Twitter)

2. **Add Media**:
   - Click "Add Media" to select images or videos
   - Supported formats: JPG, PNG, GIF, MP4, MOV, WEBM
   - File sizes shown in the media list
   - Click "Clear Media" to remove all files

3. **Schedule Posts** (Optional):
   - Check "Schedule Post"
   - Select date and time
   - Posts will be sent at the specified time (app must remain open)

4. **Send Post**:
   - Click "Post to Selected Platforms"
   - Switch to Status tab to monitor progress

### Platforms Tab

1. **Select Platforms**:
   - Check/uncheck platforms to enable/disable
   - Your selections are saved automatically

2. **Discord Options**:
   - **Discord Nitro/Vencord**: Enable for larger file limits (50MB images, 500MB videos)
   - **Use Discord embeds**: Upload images to imgBB first, show up to 10 images
   - **Send as separate messages**: Each file as individual message

### Status Tab

- Shows real-time posting status
- Displays success/failure for each platform
- Shows compression progress for large files

## Platform Limitations

| Platform | Characters | Media | File Size | Notes |
|----------|------------|-------|-----------|-------|
| Twitter | 280 | 4 files | 5MB images, 512MB videos | JPG, PNG, GIF, MP4 |
| Bluesky | 300 | 4 images | 1MB per image | No video support |
| Discord | 2000 | 10 embeds or 1 attachment | 8MB (50MB Nitro) | All common formats |
| Reddit | 300 title | 1 file | 20MB images, 1GB videos | One media per post |

## Troubleshooting

### Common Issues

**"Failed to upload" errors**:
- Check file size limits for the platform
- Ensure media format is supported
- Verify internet connection

**Twitter: "401 Unauthorized"**:
- Regenerate your access tokens
- Ensure app has "Read and Write" permissions
- Check all 5 credential fields are filled

**Bluesky: "Invalid handle or password"**:
- Use app password instead of main password
- Include full handle (e.g., `name.bsky.social`)

**Discord: "Webhook not found"**:
- Verify webhook URL is complete and correct
- Ensure webhook hasn't been deleted
- Check channel permissions

**Reddit: "Invalid credentials"**:
- Double-check Client ID (found under app name)
- Ensure using script type app
- Verify subreddit names are spelled correctly

**imgBB: "Upload failed"**:
- Check API key is valid
- Ensure image is under 32MB
- Verify supported format (JPG, PNG, GIF)

### File Compression

- The app automatically compresses files that exceed platform limits
- Compressed files are temporary and deleted after posting
- If compression fails, original file is used
- Very large files may still fail after compression

### Best Practices

1. **Test with single platform first**
2. **Use app passwords where available** (Bluesky, Reddit)
3. **Keep credentials secure** - never share your `social_credentials.json` file
4. **Monitor rate limits** - avoid posting too frequently
5. **Check Status tab** for detailed error messages
6. **For Bluesky** - create an app password instead of using your main password
7. **For Discord embeds** - ensure imgBB API key is configured

### Need Help?

- Error messages in the Status tab provide specific details
- Platform-specific error codes usually indicate credential issues
- File-related errors often mean size or format problems
- For scheduling, keep the application running until post time

### Supported Platforms

Currently supported platforms:
- **Twitter/X**: Full support for text, images, and videos
- **Bluesky**: Text and images only (no video support)
- **Discord**: Full support with multiple posting modes
- **Reddit**: Full support for text and media posts

*Note: Instagram support is in development and not currently available in the UI.*