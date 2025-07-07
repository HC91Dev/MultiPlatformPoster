import os
import time
import json
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
import moviepy.editor as mp
import tweepy
import atproto
import discord
from discord.ext import commands
import requests
import praw
import base64
from tweepy import errors as tweepy_errors

class MediaProcessor:
    PLATFORM_LIMITS = {
        'Twitter': {'image': 5*1024*1024, 'video': 512*1024*1024, 'formats': ['.jpg', '.png', '.gif', '.mp4']},
        'Bluesky': {'image': 1*1024*1024, 'video': 50*1024*1024, 'formats': ['.jpg', '.png', '.gif', '.mp4']},
        'Discord': {'image': 8*1024*1024, 'video': 8*1024*1024, 'formats': ['.jpg', '.png', '.gif', '.mp4', '.webm']},
        'Discord_Nitro': {'image': 50*1024*1024, 'video': 500*1024*1024, 'formats': ['.jpg', '.png', '.gif', '.mp4', '.webm']},
        'Instagram': {'image': 8*1024*1024, 'video': 100*1024*1024, 'formats': ['.jpg', '.jpeg', '.png', '.mp4']},
        'Reddit': {'image': 20*1024*1024, 'video': 1*1024*1024*1024, 'formats': ['.jpg', '.jpeg', '.png', '.gif', '.mp4']}
    }
    
    @staticmethod
    def compress_image(filepath, max_size):
        try:
            img = Image.open(filepath)
            filename, ext = os.path.splitext(filepath)
            # Add timestamp to avoid conflicts with multiple compressions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{filename}_compressed_{timestamp}{ext}"
            
            # Convert RGBA to RGB if saving as JPEG
            if img.mode == 'RGBA' and ext.lower() in ['.jpg', '.jpeg']:
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # First try without compression
            img.save(output_path, optimize=True)
            if os.path.getsize(output_path) <= max_size:
                return output_path
            
            # For formats that support quality
            if ext.lower() in ['.jpg', '.jpeg']:
                quality = 90
                while quality >= 60:
                    img.save(output_path, quality=quality, optimize=True)
                    if os.path.getsize(output_path) <= max_size:
                        break
                    quality -= 5
            else:
                # For PNG and other formats, resize if too large
                scale = 0.9
                while scale >= 0.5:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    resized = img.resize(new_size, Image.Resampling.LANCZOS)
                    resized.save(output_path, optimize=True)
                    if os.path.getsize(output_path) <= max_size:
                        break
                    scale -= 0.1
            
            return output_path
        except Exception as e:
            # If compression fails, return original
            return filepath
    
    @staticmethod
    def compress_video(filepath, max_size):
        try:
            video = mp.VideoFileClip(filepath)
            filename, ext = os.path.splitext(filepath)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{filename}_compressed_{timestamp}{ext}"
            
            current_size = os.path.getsize(filepath)
            if current_size <= max_size:
                video.close()
                return filepath
            
            compression_ratio = max_size / current_size
            bitrate = f"{int(video.bitrate * compression_ratio * 0.9)}k"
            
            video.write_videofile(output_path, bitrate=bitrate, codec='libx264')
            video.close()
            return output_path
        except:
            # If video compression fails, return original
            return filepath

class PostWorker(QThread):
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, content, media_files, platforms, credentials, scheduled_time=None, discord_nitro=False, discord_separate_messages=False, discord_embed_mode=False):
        super().__init__()
        self.content = content
        self.media_files = media_files
        self.platforms = platforms
        self.credentials = credentials
        self.scheduled_time = scheduled_time
        self.discord_nitro = discord_nitro
        self.discord_separate_messages = discord_separate_messages
        self.discord_embed_mode = discord_embed_mode
        self.compressed_files = []  # Track compressed files for cleanup
    
    def run(self):
        if self.scheduled_time and datetime.now() < self.scheduled_time:
            wait_seconds = (self.scheduled_time - datetime.now()).total_seconds()
            self.status_update.emit(f"Waiting until {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}...")
            self.msleep(int(wait_seconds * 1000))
        
        self.status_update.emit(f"Starting posts with {len(self.media_files)} media files...")
        
        for platform in self.platforms:
            self.status_update.emit(f"\n--- Processing {platform} ---")
            processed_media = self.process_media_for_platform(platform)
            self.status_update.emit(f"Prepared {len(processed_media)} files for {platform}")
            
            if platform == "Twitter":
                self.post_to_twitter(processed_media)
            elif platform == "Bluesky":
                self.post_to_bluesky(processed_media)
            elif platform == "Discord":
                self.post_to_discord(processed_media)
            elif platform == "Instagram":
                self.post_to_instagram(processed_media)
            elif platform == "Reddit":
                self.post_to_reddit(processed_media)
        
        # Clean up compressed files
        self.cleanup_compressed_files()
        
        self.finished.emit()
    
    def cleanup_compressed_files(self):
        """Remove temporary compressed files"""
        if self.compressed_files:
            self.status_update.emit("\nCleaning up temporary files...")
            for filepath in self.compressed_files:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        self.status_update.emit(f"✓ Removed temporary file: {os.path.basename(filepath)}")
                except Exception as e:
                    self.status_update.emit(f"⚠ Failed to remove {os.path.basename(filepath)}: {str(e)}")
    
    def process_media_for_platform(self, platform):
        processed = []
        
        # Skip compression for Discord embeds mode (imgBB will handle it)
        if platform == "Discord" and hasattr(self, 'discord_embed_mode') and self.discord_embed_mode:
            self.status_update.emit("Skipping compression for Discord embeds mode")
            return self.media_files[:10]  # Discord max 10 embeds
        
        # Handle Discord with Nitro
        if platform == "Discord" and self.discord_nitro:
            limits = MediaProcessor.PLATFORM_LIMITS.get('Discord_Nitro', {})
        else:
            limits = MediaProcessor.PLATFORM_LIMITS.get(platform, {})
        
        self.status_update.emit(f"Processing {len(self.media_files)} files for {platform}")
        
        for filepath in self.media_files:
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in limits.get('formats', []):
                self.status_update.emit(f"⚠ Skipping {os.path.basename(filepath)} - unsupported format for {platform}")
                continue
            
            file_size = os.path.getsize(filepath)
            is_video = ext in ['.mp4', '.mov', '.webm']
            max_size = limits.get('video' if is_video else 'image', 0)
            
            if max_size == 0:
                continue
            
            if file_size > max_size:
                self.status_update.emit(f"Compressing {os.path.basename(filepath)} for {platform}...")
                if is_video:
                    compressed = MediaProcessor.compress_video(filepath, max_size)
                else:
                    compressed = MediaProcessor.compress_image(filepath, max_size)
                
                # Check if compression actually reduced size enough
                compressed_size = os.path.getsize(compressed)
                if compressed_size > max_size:
                    self.status_update.emit(f"⚠ {os.path.basename(filepath)} still too large after compression ({compressed_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB) - skipping for {platform}")
                    continue
                
                processed.append(compressed)
                self.compressed_files.append(compressed)  # Track for cleanup
                self.status_update.emit(f"✓ Compressed {os.path.basename(filepath)} to {compressed_size/1024/1024:.1f}MB")
            else:
                processed.append(filepath)
                self.status_update.emit(f"✓ {os.path.basename(filepath)} ready ({file_size/1024/1024:.1f}MB)")
        
        return processed
        
    def post_to_twitter(self, media_files):
        try:
            # Validate credentials
            required_fields = ['bearer_token', 'api_key', 'api_secret', 'access_token', 'access_secret']
            for field in required_fields:
                if not self.credentials.get('twitter', {}).get(field):
                    self.status_update.emit(f"✗ Twitter: Missing {field}")
                    return
            
            client = tweepy.Client(
                bearer_token=self.credentials['twitter']['bearer_token'],
                consumer_key=self.credentials['twitter']['api_key'],
                consumer_secret=self.credentials['twitter']['api_secret'],
                access_token=self.credentials['twitter']['access_token'],
                access_token_secret=self.credentials['twitter']['access_secret']
            )
            
            if media_files:
                auth = tweepy.OAuthHandler(
                    self.credentials['twitter']['api_key'],
                    self.credentials['twitter']['api_secret']
                )
                auth.set_access_token(
                    self.credentials['twitter']['access_token'],
                    self.credentials['twitter']['access_secret']
                )
                api = tweepy.API(auth)
                
                # Test authentication
                try:
                    api.verify_credentials()
                except tweepy.errors.Unauthorized:
                    self.status_update.emit("✗ Twitter: Invalid credentials or insufficient permissions")
                    self.status_update.emit("Ensure your app has read AND write permissions")
                    # Try text-only post
                    client.create_tweet(text=self.content)
                    self.status_update.emit("✓ Posted to Twitter (text only)")
                    return
                
                self.status_update.emit(f"Uploading {len(media_files[:4])} media files to Twitter...")
                media_ids = []
                
                for i, filepath in enumerate(media_files[:4]):  # Twitter max 4 media
                    try:
                        self.status_update.emit(f"Uploading file {i+1}/{len(media_files[:4])}: {os.path.basename(filepath)}")
                        media = api.media_upload(filepath)
                        media_ids.append(media.media_id)
                    except tweepy.errors.Forbidden as e:
                        self.status_update.emit(f"⚠ Upload forbidden for {os.path.basename(filepath)}")
                        self.status_update.emit("Check Twitter app permissions: needs read AND write access")
                    except Exception as e:
                        self.status_update.emit(f"⚠ Failed to upload {os.path.basename(filepath)}: {str(e)}")
                
                if media_ids:
                    self.status_update.emit(f"Posting tweet with {len(media_ids)} media files...")
                    client.create_tweet(text=self.content, media_ids=media_ids)
                else:
                    # No media could be uploaded, post text only
                    client.create_tweet(text=self.content)
                    self.status_update.emit("✓ Posted to Twitter (text only, media upload failed)")
            else:
                client.create_tweet(text=self.content)
            
            self.status_update.emit("✓ Posted to Twitter")
        except Exception as e:
            self.status_update.emit(f"✗ Twitter failed: {str(e)}")
    
    def post_to_bluesky(self, media_files):
        try:
            client = atproto.Client()
            client.login(
                self.credentials['bluesky']['handle'],
                self.credentials['bluesky']['password']
            )

            if media_files:
                images = []
                self.status_update.emit(f"Uploading {len(media_files[:4])} images to Bluesky...")
                
                for i, filepath in enumerate(media_files[:4]):  # Bluesky max 4 images
                    try:
                        # Check file size before upload
                        file_size = os.path.getsize(filepath)
                        max_size = MediaProcessor.PLATFORM_LIMITS['Bluesky']['image']
                        
                        if file_size > max_size:
                            self.status_update.emit(f"⚠ Skipping {os.path.basename(filepath)} - too large for Bluesky")
                            continue
                        
                        # Check if it's an image file (Bluesky doesn't support videos)
                        ext = os.path.splitext(filepath)[1].lower()
                        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                            self.status_update.emit(f"⚠ Skipping {os.path.basename(filepath)} - Bluesky only supports images")
                            continue
                        
                        with open(filepath, 'rb') as f:
                            img_data = f.read()
                        
                        self.status_update.emit(f"Uploading image {i+1}/{len(media_files[:4])}...")
                        upload = client.upload_blob(img_data)
                        images.append({
                            "image": upload.blob,
                            "alt": f"Image {i+1}"
                        })
                    except Exception as e:
                        self.status_update.emit(f"⚠ Failed to upload {os.path.basename(filepath)}: {str(e)}")
                        continue

                if images:
                    self.status_update.emit(f"Posting with {len(images)} images...")
                    embed = {
                        "$type": "app.bsky.embed.images",
                        "images": images
                    }
                    client.send_post(text=self.content, embed=embed)
                else:
                    # If no images could be uploaded, post text only
                    client.send_post(text=self.content)

            else:
                client.send_post(text=self.content)

            self.status_update.emit("✓ Posted to Bluesky")
        except Exception as e:
            self.status_update.emit(f"✗ Bluesky failed: {str(e)}")

    
    def upload_images_for_discord_embeds(self, media_files):
        """Upload images to imgBB and return embed objects for Discord"""
        embeds = []
        
        for i, filepath in enumerate(media_files[:10]):  # Discord max 10 embeds
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                self.status_update.emit(f"⚠ Skipping {os.path.basename(filepath)} - Discord embeds only support images")
                continue
                
            # Check if image needs compression for imgBB (32MB limit)
            file_size = os.path.getsize(filepath)
            upload_path = filepath
            
            if file_size > 32 * 1024 * 1024:
                self.status_update.emit(f"Compressing {os.path.basename(filepath)} for imgBB (>32MB)...")
                upload_path = MediaProcessor.compress_image(filepath, 32 * 1024 * 1024)
                if upload_path != filepath:
                    self.compressed_files.append(upload_path)  # Track for cleanup
                
            self.status_update.emit(f"Uploading {os.path.basename(upload_path)} to imgBB for Discord embed...")
            imgbb_url = self.upload_to_imgbb(upload_path)
            
            if imgbb_url:
                embeds.append({
                    "image": {"url": imgbb_url}
                })
                self.status_update.emit(f"✓ Prepared embed {len(embeds)}/10")
            
            if len(embeds) >= 10:
                break
                
        return embeds
    
    def post_to_discord(self, media_files):
        try:
            webhook_url = self.credentials['discord']['webhook_url']

            if media_files:
                if hasattr(self, 'discord_embed_mode') and self.discord_embed_mode:
                    self.status_update.emit("Using Discord embeds mode (uploading to imgBB)...")

                    if not self.credentials.get('imgbb', {}).get('api_key'):
                        self.status_update.emit("✗ Discord embeds require imgBB API key to be configured")
                        self.status_update.emit("Please configure imgBB in settings to use Discord embeds")
                        self.status_update.emit("Falling back to attachment mode...")
                        media_files = media_files[:1]
                    else:
                        embeds = self.upload_images_for_discord_embeds(media_files)

                        if embeds:
                            payload = {
                                "content": self.content,
                                "embeds": embeds
                            }
                            response = requests.post(webhook_url, json=payload)

                            if response.status_code in [200, 204]:
                                self.status_update.emit(f"✓ Posted to Discord with {len(embeds)} embedded images")
                            else:
                                self.status_update.emit(f"✗ Discord failed: HTTP {response.status_code}")
                                if response.text:
                                    self.status_update.emit(f"Error: {response.text}")
                        else:
                            response = requests.post(webhook_url, json={"content": self.content})
                            if response.status_code in [200, 204]:
                                self.status_update.emit("✓ Posted to Discord (text only, no images could be embedded)")

                elif self.discord_separate_messages:
                    self.status_update.emit(f"Sending {len(media_files[:10])} files as separate Discord messages...")
                    success_count = 0

                    if self.content:
                        response = requests.post(webhook_url, json={"content": self.content})
                        if response.status_code in [200, 204]:
                            self.status_update.emit("✓ Posted text to Discord")
                        time.sleep(0.5)

                    for i, filepath in enumerate(media_files[:10]):
                        try:
                            with open(filepath, 'rb') as f:
                                files = [('file', f)]
                                filename = os.path.basename(filepath)

                                response = requests.post(
                                    webhook_url,
                                    data={"content": f"📎 {filename}"},
                                    files=files,
                                    timeout=60
                                )

                            if response.status_code in [200, 204]:
                                success_count += 1
                                self.status_update.emit(f"✓ Sent file {i+1}/{len(media_files[:10])}: {filename}")
                            else:
                                self.status_update.emit(f"✗ Failed to send {filename}: HTTP {response.status_code}")

                            if i < len(media_files[:10]) - 1:
                                time.sleep(0.5)

                        except Exception as e:
                            self.status_update.emit(f"✗ Error sending {os.path.basename(filepath)}: {str(e)}")

                    if success_count > 0:
                        self.status_update.emit(f"✓ Posted to Discord: {success_count}/{len(media_files[:10])} files sent")

                else:
                    self.status_update.emit(f"Uploading {len(media_files[:10])} files to Discord (attachments mode)...")

                    files_dict = {}
                    file_handles = []

                    for i, filepath in enumerate(media_files[:10]):
                        try:
                            f = open(filepath, 'rb')
                            file_handles.append(f)
                            files_dict[f'files[{i}]'] = (os.path.basename(filepath), f, 'application/octet-stream')
                            self.status_update.emit(f"Prepared file {i+1}: {os.path.basename(filepath)}")
                        except Exception as e:
                            self.status_update.emit(f"✗ Failed to open {os.path.basename(filepath)}: {str(e)}")

                    if files_dict:
                        try:
                            data = {'payload_json': json.dumps({'content': self.content})}

                            response = requests.post(
                                webhook_url,
                                data=data,
                                files=files_dict,
                                timeout=120
                            )

                            if response.status_code in [200, 204]:
                                self.status_update.emit(f"✓ Posted to Discord with {len(files_dict)} attachments")
                            else:
                                self.status_update.emit(f"✗ Discord failed: HTTP {response.status_code}")
                                if response.text:
                                    self.status_update.emit(f"Error: {response.text}")

                                if len(file_handles) > 1:
                                    self.status_update.emit("Retrying with single file attachment...")

                                    for f in file_handles[1:]:
                                        f.close()

                                    file_handles[0].seek(0)

                                    response = requests.post(
                                        webhook_url,
                                        data={"content": self.content},
                                        files=[('file', file_handles[0])],
                                        timeout=60
                                    )

                                    if response.status_code in [200, 204]:
                                        self.status_update.emit("✓ Posted to Discord with 1 attachment (fallback)")
                                        self.status_update.emit("Tip: Enable 'Use Discord embeds' or 'Send as separate messages' for multiple images")

                        finally:
                            for f in file_handles:
                                try:
                                    f.close()
                                except:
                                    pass
                    else:
                        response = requests.post(webhook_url, json={"content": self.content})
                        if response.status_code in [200, 204]:
                            self.status_update.emit("✓ Posted to Discord (text only)")

            else:
                response = requests.post(webhook_url, json={"content": self.content})
                if response.status_code in [200, 204]:
                    self.status_update.emit("✓ Posted to Discord")
                else:
                    self.status_update.emit(f"✗ Discord failed: {response.status_code}")

        except Exception as e:
            self.status_update.emit(f"✗ Discord failed: {str(e)}")

    def upload_to_imgbb(self, filepath):
        """Upload image to imgBB and return the URL"""
        try:
            api_key = self.credentials.get('imgbb', {}).get('api_key', '')
            if not api_key:
                self.status_update.emit("✗ imgBB API key not configured")
                return None
            
            # Check file size (imgBB has a 32MB limit for images)
            file_size = os.path.getsize(filepath)
            if file_size > 32 * 1024 * 1024:
                self.status_update.emit(f"✗ {os.path.basename(filepath)} too large for imgBB (>32MB)")
                return None
            
            with open(filepath, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            data = {
                'key': api_key,
                'image': image_data
            }
            
            response = requests.post(
                'https://api.imgbb.com/1/upload',
                data=data,
                timeout=60  # Longer timeout for uploads
            )
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get('success'):
                    return json_data['data']['url']
                else:
                    self.status_update.emit(f"✗ imgBB upload failed: {json_data.get('error', {}).get('message', 'Unknown error')}")
                    return None
            else:
                self.status_update.emit(f"✗ imgBB upload failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.status_update.emit(f"✗ imgBB upload error: {str(e)}")
            return None

    def post_to_instagram(self, media_files):
        try:
            access_token = self.credentials['instagram']['access_token']
            account_id = self.credentials['instagram']['account_id']
            
            if not media_files:
                self.status_update.emit("✗ Instagram requires at least one image or video")
                return
            
            filepath = media_files[0]  # Use first media file
            ext = os.path.splitext(filepath)[1].lower()
            
            # Upload to imgBB for images
            if ext in ['.jpg', '.jpeg', '.png']:
                self.status_update.emit("Uploading image to imgBB...")
                media_url = self.upload_to_imgbb(filepath)
                
                if not media_url:
                    self.status_update.emit("✗ Failed to upload image to imgBB")
                    return
                
                self.status_update.emit(f"✓ Image uploaded to imgBB: {media_url}")
                
                # Create media container
                container_data = {
                    'image_url': media_url,
                    'caption': self.content,
                    'access_token': access_token
                }
                endpoint = f'https://graph.facebook.com/v18.0/{account_id}/media'
                
            elif ext == '.mp4':
                # For videos, we'd need a different hosting solution
                # imgBB doesn't support video uploads
                self.status_update.emit("✗ Video posting requires a video hosting solution (imgBB doesn't support videos)")
                self.status_update.emit("Consider using AWS S3, Cloudinary, or other video hosting services")
                return
            else:
                self.status_update.emit(f"✗ Instagram doesn't support {ext} files")
                return
            
            # Create container
            self.status_update.emit("Creating Instagram media container...")
            container_response = requests.post(endpoint, data=container_data)
            
            if container_response.status_code == 200:
                container_id = container_response.json().get('id')
                
                # Publish the media
                self.status_update.emit("Publishing to Instagram...")
                publish_response = requests.post(
                    f'https://graph.facebook.com/v18.0/{account_id}/media_publish',
                    data={
                        'creation_id': container_id,
                        'access_token': access_token
                    }
                )
                
                if publish_response.status_code == 200:
                    self.status_update.emit("✓ Posted to Instagram")
                else:
                    error = publish_response.json().get('error', {})
                    self.status_update.emit(f"✗ Instagram publish failed: {error.get('message', 'Unknown error')}")
            else:
                error = container_response.json().get('error', {})
                self.status_update.emit(f"✗ Instagram container creation failed: {error.get('message', 'Unknown error')}")
                
        except Exception as e:
            self.status_update.emit(f"✗ Instagram failed: {str(e)}")

    def post_to_reddit(self, media_files):
        try:
            # Validate credentials before creating Reddit instance
            required_fields = ['client_id', 'client_secret', 'username', 'password', 'user_agent']
            for field in required_fields:
                if not self.credentials.get('reddit', {}).get(field):
                    self.status_update.emit(f"✗ Reddit: Missing {field}")
                    return
            
            reddit = praw.Reddit(
                client_id=self.credentials['reddit']['client_id'],
                client_secret=self.credentials['reddit']['client_secret'],
                username=self.credentials['reddit']['username'],
                password=self.credentials['reddit']['password'],
                user_agent=self.credentials['reddit']['user_agent']
            )
            
            # Get subreddits (comma-separated)
            subreddits_str = self.credentials['reddit'].get('subreddits', '')
            if not subreddits_str:
                self.status_update.emit("✗ Reddit: No subreddits specified")
                return
                
            subreddits = [s.strip() for s in subreddits_str.split(',') if s.strip()]
            
            if not subreddits:
                self.status_update.emit("✗ Reddit: No subreddits specified")
                return
            
            # Post to each subreddit
            success_count = 0
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Extract title from content (first line or first 100 chars)
                    lines = self.content.strip().split('\n')
                    if len(lines) > 1:
                        title = lines[0][:300]  # Reddit title limit
                        text_content = '\n'.join(lines[1:])
                    else:
                        title = self.content[:100] + '...' if len(self.content) > 100 else self.content
                        text_content = self.content
                    
                    if media_files:
                        # Reddit only supports one media file per post
                        filepath = media_files[0]
                        ext = os.path.splitext(filepath)[1].lower()
                        
                        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                            submission = subreddit.submit_image(
                                title=title,
                                image_path=filepath
                            )
                            # Add text as comment if there's body text
                            if text_content and text_content != title:
                                submission.reply(text_content)
                        elif ext == '.mp4':
                            submission = subreddit.submit_video(
                                title=title,
                                video_path=filepath
                            )
                            if text_content and text_content != title:
                                submission.reply(text_content)
                        else:
                            # Text post with link to media
                            submission = subreddit.submit(
                                title=title,
                                selftext=text_content
                            )
                    else:
                        # Text-only post
                        submission = subreddit.submit(
                            title=title,
                            selftext=text_content
                        )
                    
                    self.status_update.emit(f"✓ Posted to r/{subreddit_name}")
                    success_count += 1
                    
                    # Small delay between posts to avoid rate limiting
                    if len(subreddits) > 1:
                        time.sleep(2)
                        
                except Exception as e:
                    self.status_update.emit(f"✗ Failed to post to r/{subreddit_name}: {str(e)}")
            
            if success_count > 0:
                self.status_update.emit(f"✓ Reddit: Posted to {success_count}/{len(subreddits)} subreddits")
            else:
                self.status_update.emit("✗ Reddit: Failed to post to any subreddit")
                
        except Exception as e:
            self.status_update.emit(f"✗ Reddit failed: {str(e)}")